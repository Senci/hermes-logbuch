"""States (D47): the pure decision, the end-of-chain facts, redaction, and the wiring into the sessions items.

Synthetic chains only; every db and home lives in a TemporaryDirectory.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import support
from support import add_message, add_session, raw_calls

sys.path.insert(0, str(support.DASHBOARD))
import lb_scan  # noqa: E402
import classify  # noqa: E402
import lb_service  # noqa: E402
import states  # noqa: E402

PROVIDER = "provider problem"
WAIT = ("waiting_go", "needs your go")
MERGE = ("not_merged", "not merged")
TODO = ("todo", "still open")
FAILED = "Your request was not processed. Send it again if you still want me to carry it out."


def facts(provider=None, *opens):
    return states.StateFacts(provider=provider, opens=tuple(opens))


class TestDecide(unittest.TestCase):
    def decide(self, f, value=None, commits=0, mrs=0, done=False):
        return states.decide(f, value, commits, mrs, done)

    def test_every_state_is_reachable(self):
        got = {
            "critical": self.decide(facts(PROVIDER), 3)[0],
            "waiting_go": self.decide(facts(None, WAIT), 1)[0],
            "interrupted": self.decide(facts(PROVIDER), 2)[0],
            "not_merged": self.decide(facts(None, MERGE), 1)[0],
            "todo": self.decide(facts(None, TODO), 1)[0],
            "shipped": self.decide(facts(), 1, commits=1)[0],
            "none": self.decide(facts(), 1)[0],
        }
        self.assertEqual(got, {name: name for name in states.STATES})

    def test_shipped_counts_commit_or_mr_calls(self):
        self.assertEqual(self.decide(facts(), 0, commits=1)[0], "shipped")
        self.assertEqual(self.decide(facts(), 0, mrs=2)[0], "shipped")
        self.assertEqual(self.decide(facts(), 0)[0], "none")

    def test_critical_beats_waiting_go(self):
        f = facts(PROVIDER, WAIT, MERGE, TODO)
        self.assertEqual(self.decide(f, 3), ("critical", PROVIDER))

    def test_precedence_down_the_list(self):
        self.assertEqual(self.decide(facts(PROVIDER, WAIT, MERGE, TODO), 2), ("waiting_go", WAIT[1]))
        self.assertEqual(self.decide(facts(PROVIDER, MERGE, TODO), 2), ("interrupted", PROVIDER))
        self.assertEqual(self.decide(facts(None, MERGE, TODO), 2), ("not_merged", MERGE[1]))
        self.assertEqual(self.decide(facts(None, TODO), 2, commits=3), ("todo", TODO[1]))
        self.assertEqual(self.decide(facts(), 2, commits=3), ("shipped", None))

    def test_p1_without_a_label_is_interrupted_not_critical(self):
        self.assertEqual(self.decide(facts(PROVIDER), None), ("interrupted", PROVIDER))

    def test_non_p1_values_are_interrupted(self):
        for value in (0, 1, 2):
            self.assertEqual(self.decide(facts(PROVIDER), value)[0], "interrupted")

    def test_loose_end_done_clears_every_open_state(self):
        open_cases = [facts(PROVIDER), facts(None, WAIT), facts(None, MERGE), facts(None, TODO)]
        for f in open_cases:
            self.assertEqual(self.decide(f, 3, done=True), ("none", None))
            self.assertEqual(self.decide(f, 3, commits=1, done=True), ("shipped", None))
            self.assertEqual(self.decide(f, 3, mrs=1, done=True), ("shipped", None))

    def test_state_for_reads_the_item(self):
        item = {"label": {"value": 3}, "commit_calls": 0, "mr_calls": 0, "loose_end_done": False}
        self.assertEqual(states.state_for(facts(PROVIDER), item)[0], "critical")
        self.assertEqual(states.state_for(facts(PROVIDER), dict(item, label=None))[0], "interrupted")
        self.assertEqual(states.state_for(facts(PROVIDER), dict(item, loose_end_done=True))[0], "none")


class TestProviderEnd(unittest.TestCase):
    def meta(self, code=None, layer="provider", error=None):
        surface = {k: v for k, v in (("layer", layer), ("code", code)) if v}
        body = {"error_surface": surface}
        if error:
            body["error"] = error
        return json.dumps(body)

    def test_unstructured_failed_turn_is_a_provider_problem(self):
        self.assertEqual(states.provider_end(FAILED, "failed_turn", None), FAILED[:120].rstrip())
        self.assertIsNotNone(states.provider_end(FAILED, "failed_turn", ""))

    def test_structured_failed_turn_names_the_code(self):
        meta = self.meta("rate_limit", error="HTTP 429: quota exceeded")
        self.assertEqual(states.provider_end(FAILED, "failed_turn", meta), "rate_limit: HTTP 429: quota exceeded")

    def test_content_policy_failed_turn_is_not_a_provider_problem(self):
        by_code = self.meta("content_policy_blocked", error="content_policy_blocked: model declined")
        by_text_only = json.dumps({"error": "content_policy_blocked: model declined"})
        self.assertIsNone(states.provider_end(FAILED, "failed_turn", by_code))
        self.assertIsNone(states.provider_end(FAILED, "failed_turn", self.meta("content_policy_blocked")))
        self.assertIsNone(states.provider_end(FAILED, "failed_turn", by_text_only))

    def test_malformed_metadata_still_counts_as_a_failed_turn(self):
        self.assertIsNotNone(states.provider_end(FAILED, "failed_turn", "{not json"))
        self.assertIsNotNone(states.provider_end(FAILED, "failed_turn", "[1, 2]"))

    def test_the_three_interrupt_lines(self):
        for line in (
            "Operation interrupted: waiting for model response (4.8s elapsed).",
            "Operation interrupted: handling API error (RateLimitError: 429).",
            "Operation interrupted: retrying API call after error (retry 1/3).",
        ):
            self.assertEqual(states.provider_end(line, None, None), line)

    def test_the_three_more_0_22_2_interrupt_lines(self):
        for line in (
            "Operation interrupted: waiting for the provider to recover (cycle 2/5).",
            "Operation interrupted: retrying empty response from model (retry 1/3).",
            "Operation interrupted during retry (rate_limit, attempt 2/4).",
        ):
            self.assertEqual(states.provider_end(line, None, None), line)

    def test_untyped_failed_turn_notices_are_provider_ends(self):
        partial = "This turn did not complete. Some actions may already have run; verify their effects before resending."
        self.assertEqual(states.provider_end(FAILED, None, None), FAILED[:120].rstrip())
        self.assertEqual(states.provider_end(partial, None, None), partial[:120].rstrip())
        self.assertEqual(states.provider_end(FAILED, "", "{}"), FAILED[:120].rstrip())

    def test_notice_text_under_another_kind_is_not_a_provider_end(self):
        self.assertIsNone(states.provider_end(FAILED, "steer", None))
        self.assertIsNone(states.provider_end("The run said: " + FAILED, None, None))

    def test_typed_content_policy_notice_stays_excluded(self):
        meta = json.dumps({"error_surface": {"code": "content_policy_blocked"}})
        self.assertIsNone(states.provider_end(FAILED, "failed_turn", meta))

    def test_a_bare_interrupt_has_no_cause(self):
        self.assertIsNone(states.provider_end("Operation interrupted.", None, None))

    def test_interrupt_text_only_counts_at_the_start(self):
        text = "The run stopped. Operation interrupted: waiting for model response (1s)."
        self.assertIsNone(states.provider_end(text, None, None))

    def test_tool_output_noise_is_not_a_provider_problem(self):
        text = "The log shows quota exceeded, HTTP 429 and a request that timed out; all three are old."
        self.assertIsNone(states.provider_end(text, None, None))
        self.assertIsNone(states.provider_end(text, "steer", None))


class TestOpenEnds(unittest.TestCase):
    def ends(self, text):
        return dict(states.open_ends(text, lb_scan.LOOSE_WINDOW, support.DATA.open_patterns))

    def test_each_alternative_group_maps_to_its_state(self):
        self.assertIn("waiting_go", self.ends("Done, but this needs your go before it lands."))
        self.assertIn("waiting_go", self.ends("Four decisions are still waiting on the picker."))
        self.assertIn("waiting_go", self.ends("The picker timed out twice."))
        self.assertIn("waiting_go", self.ends("Nothing moves, waiting on you."))
        self.assertIn("not_merged", self.ends("The MR is open, none is merged yet."))
        self.assertIn("not_merged", self.ends("!347 is a Draft until the hold ends."))
        self.assertIn("todo", self.ends("One item is still open for you."))
        self.assertIn("todo", self.ends("Still to do: publish the page."))

    def test_prototype_alternatives_without_a_state_give_nothing(self):
        for text in ("Your request was not processed.", "The call timed out once and then passed.",
                     "Operation interrupted: waiting for model response."):
            self.assertEqual(self.ends(text), {})

    def test_the_window_is_the_loose_end_window(self):
        far = "x" * lb_scan.LOOSE_WINDOW + " needs your go"
        self.assertEqual(self.ends(far), {})
        self.assertEqual(self.ends("needs your go " + "x" * 500).keys(), {"waiting_go"})

    def test_evidence_is_the_match_with_context(self):
        text = "All checks pass and the branch is pushed, but the MR is a Draft because you chose to hold it."
        evidence = self.ends(text)["not_merged"]
        self.assertIn("is a Draft", evidence)
        self.assertLessEqual(len(evidence), states.EVIDENCE_MAX)

    def test_several_groups_can_match_at_once(self):
        got = self.ends("It needs your go. Also none is merged and a step is still open.")
        self.assertEqual(set(got), {"waiting_go", "not_merged", "todo"})


class TestRedactionAndCut(unittest.TestCase):
    def test_secret_shapes_are_redacted(self):
        pem = "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkq\n-----END PRIVATE KEY-----"
        cases = {
            "key sk-abcdef1234567890XYZ in env": "sk-abcdef1234567890XYZ",
            "pat glpat-AbCdEf123456_-xyz used": "glpat-AbCdEf123456_-xyz",
            "header Bearer eyJhbGciOi.payload.sig sent": "eyJhbGciOi.payload.sig",
            "api_token=Zk93mQ77plainvalue here": "Zk93mQ77plainvalue",
            'GITLAB_TOKEN: "s3cr3tValue99" set': "s3cr3tValue99",
            f"a {pem} b": "MIIEvQIBADANBgkq",
        }
        for text, secret in cases.items():
            self.assertNotIn(secret, classify.redact(text), text)

    def test_evidence_is_cut_to_120(self):
        out = states.provider_end("Operation interrupted: waiting for model response " + "z" * 400, None, None)
        self.assertEqual(len(out), 120)

    def test_redaction_runs_before_the_cut(self):
        pem = "-----BEGIN RSA PRIVATE KEY-----\n" + "A" * 300 + "\n-----END RSA PRIVATE KEY-----"
        text = "Operation interrupted: handling API error " + pem
        out = states.provider_end(text, None, None)
        self.assertNotIn("AAAA", out)
        self.assertNotIn("BEGIN", out.replace("[redacted key]", ""))
        # a secret that starts just before character 120: cutting first would leave a short, unmatched prefix
        head = "Operation interrupted: waiting for model response " + "x" * 65 + " "
        self.assertEqual(len(head), 116)
        out = states.provider_end(head + "sk-" + "Q" * 30, None, None)
        self.assertNotIn("sk-", out)
        self.assertTrue(out.endswith("[red"))

    def test_open_evidence_is_redacted_too(self):
        text = "It needs your go; token=abcd1234efgh5678 stays out of the log."
        evidence = dict(states.open_ends(text, lb_scan.LOOSE_WINDOW, support.DATA.open_patterns))["waiting_go"]
        self.assertNotIn("abcd1234efgh5678", evidence)

    def test_unterminated_pem_is_cut_to_the_end(self):
        out = classify.redact("x -----BEGIN PRIVATE KEY----- MIIE" + "B" * 50)
        self.assertNotIn("MIIE", out)

    def test_states_has_no_redaction_of_its_own(self):
        self.assertFalse(hasattr(states, "redact"))
        self.assertFalse(hasattr(states, "_SECRETS"))

    def test_open_evidence_uses_the_shared_line_break_redaction(self):
        # D50: a key broken by a line break must not leave its tail in the evidence (the pre-D50 copy did)
        tail = "PLANTTAILWWW0123456789abcd"
        text = "It needs your go. glpat-\n" + tail + " was pasted by mistake."
        evidence = dict(states.open_ends(text, lb_scan.LOOSE_WINDOW, support.DATA.open_patterns))["waiting_go"]
        self.assertNotIn("PLANTTAIL", evidence)
        text = "It needs your go. key sk-abcd\n1234efghijklmnop5678 here"
        evidence = dict(states.open_ends(text, lb_scan.LOOSE_WINDOW, support.DATA.open_patterns))["waiting_go"]
        self.assertNotIn("1234efghijklmnop5678", evidence)

    def test_interrupt_evidence_goes_through_the_shared_redaction(self):
        line = "Operation interrupted: handling API error (AuthError: token=abcd1234efgh5678 rejected)"
        out = states.provider_end(line, None, None)
        self.assertNotIn("abcd1234efgh5678", out)
        self.assertEqual(out, states._cut(" ".join(classify.redact(line).split())))


class WorldCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.home = Path(self._tmp.name)
        self.conn = support.make_state_db(self.home / "state.db")
        self.addCleanup(self.conn.close)
        self.n = 0

    def chain(self, sid, reply=None, kind=None, meta=None, commit=False, trailing=()):
        """A qualifying desktop chain whose final assistant message is `reply`; trailing rows follow it."""
        self.n += 1
        add_session(self.conn, sid, "desktop", started=1000 + self.n, last=2000 + self.n, tool_calls=25, title=sid)
        add_message(self.conn, sid, "user", "please do the thing")
        add_message(self.conn, sid, "assistant", "", raw_calls("patch"))
        if commit:
            add_message(self.conn, sid, "assistant", "", raw_calls("terminal", "git commit -m x"))
        if reply is not None:
            if len(reply) <= 40:  # the digest reply floor is 40 chars
                reply = "All the checks were run and written up. " + reply
            add_message(self.conn, sid, "assistant", reply, None, kind, meta)
        for content, k in trailing:
            add_message(self.conn, sid, "assistant", content, raw_calls("terminal", "ls") if not content else None, k)
        self.conn.commit()

    def label(self, sid, value):
        lb_service.put_label(self.home, sid, {"topic": "OPS", "value": value, "summary": "s"})

    def items(self):
        return {i["id"]: i for i in lb_service.sessions_payload(self.home, "t")["items"]}

    def state(self, sid):
        item = self.items()[sid]
        return item["state"], item["state_evidence"]


class TestWiring(WorldCase):
    def test_a_chain_of_every_state(self):
        self.chain("crit", FAILED, "failed_turn")
        self.label("crit", 3)
        self.chain("wait", "Done. This needs your go before it lands.")
        self.chain("intr", "Operation interrupted: waiting for model response (2.1s elapsed).")
        self.label("intr", 2)
        self.chain("merge", "The MR is open, none is merged yet.")
        self.chain("todo", "One item is still open for you.")
        self.chain("ship", "All done and pushed.", commit=True)
        self.chain("none", "All done, nothing to ship.")
        got = {sid: self.state(sid)[0] for sid in ("crit", "wait", "intr", "merge", "todo", "ship", "none")}
        self.assertEqual(got, {"crit": "critical", "wait": "waiting_go", "intr": "interrupted",
                               "merge": "not_merged", "todo": "todo", "ship": "shipped", "none": "none"})

    def test_critical_beats_waiting_go_on_one_chain(self):
        # one final message that is both a failed turn and carries a waiting-on-go phrase in its first 320 chars
        text = "This turn did not complete and the task needs your go before a retry is sent. " + FAILED
        self.chain("both", text, "failed_turn")
        self.label("both", 3)
        self.assertEqual(self.state("both")[0], "critical")
        self.chain("both2", text, "failed_turn")
        self.label("both2", 2)
        self.assertEqual(self.state("both2")[0], "waiting_go")

    def test_content_policy_failed_turn_is_not_a_provider_problem(self):
        meta = json.dumps({"error": "content_policy_blocked: declined",
                           "error_surface": {"layer": "provider", "code": "content_policy_blocked"}})
        self.chain("policy", FAILED, "failed_turn", meta)
        self.label("policy", 3)
        self.assertEqual(self.state("policy"), ("none", None))

    def test_p1_without_a_label_gives_interrupted(self):
        self.chain("nolabel", FAILED, "failed_turn")
        item = self.items()["nolabel"]
        self.assertIsNone(item["label"])
        self.assertEqual(item["state"], "interrupted")

    def test_untyped_failed_turn_row_ends_the_chain_as_a_provider_problem(self):
        self.chain("untyped", FAILED, None)
        self.label("untyped", 3)
        self.chain("untyped2", FAILED, None)
        self.assertEqual(self.state("untyped"), ("critical", FAILED))
        self.assertEqual(self.state("untyped2"), ("interrupted", FAILED))

    def test_p1_with_a_label_gives_critical(self):
        self.chain("p1", FAILED, "failed_turn")
        self.label("p1", 3)
        self.assertEqual(self.state("p1")[0], "critical")

    def test_loose_end_done_clears(self):
        self.chain("open", "This needs your go.", commit=True)
        self.chain("cut", FAILED, "failed_turn")
        self.label("cut", 3)
        self.assertEqual(self.state("open")[0], "waiting_go")
        self.assertEqual(self.state("cut")[0], "critical")
        lb_service.put_label(self.home, "open", {"loose_end_done": True})
        lb_service.put_label(self.home, "cut", {"loose_end_done": True})
        self.assertEqual(self.state("open"), ("shipped", None))
        self.assertEqual(self.state("cut"), ("none", None))
        lb_service.put_label(self.home, "cut", {"loose_end_done": False})
        self.assertEqual(self.state("cut")[0], "critical")

    def test_only_the_last_assistant_message_counts(self):
        self.chain("recovered", None)
        add_message(self.conn, "recovered", "assistant", FAILED, None, "failed_turn")
        add_message(self.conn, "recovered", "user", "retry")
        add_message(self.conn, "recovered", "assistant", "Fixed and verified.")
        self.conn.commit()
        self.label("recovered", 3)
        self.assertEqual(self.state("recovered")[0], "none")

    def test_noise_rows_after_the_reply_are_skipped(self):
        self.chain("noise", FAILED, "failed_turn", trailing=(("", None), ("hidden text", "hidden")))
        self.label("noise", 3)
        self.assertEqual(self.state("noise")[0], "critical")

    def test_tool_output_mentioning_a_provider_problem_is_ignored(self):
        self.chain("tool", "Done. The log held quota and 429 lines, and one call timed out.")
        add_message(self.conn, "tool", "tool", "Operation interrupted: waiting for model response")
        add_message(self.conn, "tool", "user", "Your request was not processed")
        self.conn.commit()
        self.label("tool", 3)
        self.assertEqual(self.state("tool"), ("none", None))

    def test_last_message_comes_from_the_newest_session_of_the_chain(self):
        self.chain("root", "Old reply, all fine.")
        add_session(self.conn, "root2", "kanban", parent="root", started=1500, last=9000, tool_calls=1)
        add_message(self.conn, "root2", "assistant", FAILED, None, "failed_turn")
        self.conn.commit()
        self.assertEqual(self.state("root")[0], "interrupted")

    def test_evidence_is_redacted_and_cut_in_the_payload(self):
        line = "Operation interrupted: handling API error (AuthError: Bearer abcdef0123456789xyz " + "q" * 200 + ")"
        self.chain("ev", line)
        state, evidence = self.state("ev")
        self.assertEqual(state, "interrupted")
        self.assertNotIn("abcdef0123456789xyz", evidence)
        self.assertLessEqual(len(evidence), 120)

    def test_open_evidence_in_the_payload(self):
        self.chain("w", "Everything is pushed. The MR is a Draft because you chose to hold it.")
        state, evidence = self.state("w")
        self.assertEqual(state, "not_merged")
        self.assertIn("is a Draft", evidence)

    def test_shipped_and_none_carry_no_evidence(self):
        self.chain("s", "All done.", commit=True)
        self.chain("n", "All done.")
        self.assertEqual(self.state("s"), ("shipped", None))
        self.assertEqual(self.state("n"), ("none", None))

    def test_loose_end_flag_is_unchanged(self):
        self.chain("l", "One item is still open for you.")
        self.assertTrue(self.items()["l"]["loose_end"])

    def test_facts_are_cached_with_the_chain(self):
        self.chain("c", FAILED, "failed_turn")
        scanner = lb_scan.scanner_for(self.home / "state.db")
        scanner.refresh(support.DATA)
        first = scanner.chains_scanned_total
        again = scanner.refresh(support.DATA)
        self.assertEqual(scanner.chains_scanned_total, first)
        self.assertIsNotNone(again.entries[0].facts.provider)

    def test_schema_without_display_columns_still_reads_interrupt_lines(self):
        conn = support.make_state_db(self.home / "other.db", drop_message=("display_kind", "display_metadata"))
        add_session(conn, "x", "desktop", started=1, last=2, tool_calls=25, title="x")
        add_message(conn, "x", "user", "go")
        add_message(conn, "x", "assistant", "", raw_calls("patch"))
        add_message(conn, "x", "assistant", "Operation interrupted: waiting for model response (3s elapsed).")
        add_session(conn, "y", "desktop", started=3, last=4, tool_calls=25, title="y")
        add_message(conn, "y", "user", "go")
        add_message(conn, "y", "assistant", "", raw_calls("patch"))
        add_message(conn, "y", "assistant", FAILED)
        conn.commit()
        conn.close()
        other = Path(self._tmp.name) / "h2"
        other.mkdir()
        (other / "state.db").write_bytes((self.home / "other.db").read_bytes())
        got = {i["id"]: i for i in lb_service.sessions_payload(other, "t")["items"]}
        self.assertEqual(got["x"]["state"], "interrupted")
        self.assertNotEqual(got["y"]["state"], "critical")
        self.assertTrue(lb_service.sessions_payload(other, "t")["schema_ok"])


if __name__ == "__main__":
    unittest.main()
