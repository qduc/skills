import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location("start_term2", Path(__file__).with_name("start_term2.py"))
launcher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(launcher)


class FakeHerdr:
    def __init__(self, prompt_error=None, pending=False, state="idle"):
        self.calls = []
        self.prompt_error = prompt_error
        self.pending = pending
        self.state = state
        self.waits = 0
        self.prompt = ""

    def __call__(self, argv, **kwargs):
        self.calls.append(argv)
        op = argv[1:3]
        data = {"result": {}}
        code = 0
        if op == ["tab", "create"]:
            data = {"result": {"root_pane": {"pane_id": "wX:pY"}, "tab": {"tab_id": "wX:tZ"}}}
        elif op == ["agent", "get"]:
            data = {"result": {"agent": {"agent": "term2", "agent_status": self.state}}}
        elif op == ["pane", "read"]:
            return subprocess.CompletedProcess(argv, 0, "term2 codex/gpt-5.6-luna\n❯ " + (self.prompt if self.pending and self.waits else "") + "\n Standard", "")
        elif op == ["agent", "prompt"]:
            self.prompt = argv[4]
            if self.prompt_error:
                code = 1
                data = {"error": {"code": self.prompt_error, "message": "rejected"}}
            else:
                data = {"result": {"agent": {"agent_status": "working"}}}
        elif op == ["agent", "wait"]:
            self.waits += 1
            if self.pending and self.waits == 1:
                code = 1
                data = {"error": {"code": "timeout", "message": "timeout"}}
            else:
                data = {"result": {"agent": {"agent_status": "working"}}}
        return subprocess.CompletedProcess(argv, code, "" if code else json.dumps(data), json.dumps(data) if code else "")


class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.brief = Path(self.tmp.name) / "brief with spaces.md"
        self.brief.write_text("bounded task")
        self.args = argparse.Namespace(workspace="wX", cwd=self.tmp.name, brief=str(self.brief),
            provider="codex", model="gpt-5.6-luna", effort="high", label="worker",
            auto_approve=False, timeout_ms=10000, herdr="herdr", term2="term2", pane=None)

    def test_integrated_prompt_and_explicit_launch(self):
        fake = FakeHerdr()
        result = launcher.launch(self.args, run=fake)
        self.assertEqual(result["status"], "admitted")
        self.assertEqual(result["pane_id"], "wX:pY")
        self.assertIn("--no-focus", fake.calls[0])
        command = next(c[4] for c in fake.calls if c[1:3] == ["pane", "run"])
        self.assertEqual(command, "term2 -p codex -m gpt-5.6-luna -r high")
        self.assertFalse(any(c[1:3] == ["pane", "send-keys"] for c in fake.calls))

    def test_unintegrated_idle_fallback(self):
        fake = FakeHerdr("agent_not_ready")
        result = launcher.launch(self.args, run=fake)
        self.assertEqual(result["transport"], "verified-idle-pane")
        self.assertEqual(sum(c[1:3] == ["pane", "send-keys"] for c in fake.calls), 1)

    def test_pending_draft_retries_enter_not_text(self):
        fake = FakeHerdr("agent_not_ready", pending=True)
        result = launcher.launch(self.args, run=fake)
        self.assertEqual(result["status"], "admitted")
        self.assertEqual(sum(c[1:3] == ["pane", "send-keys"] for c in fake.calls), 2)
        self.assertEqual(sum(c[1:3] == ["pane", "run"] for c in fake.calls), 2)

    def test_blocked_prompt_never_falls_back(self):
        fake = FakeHerdr("agent_blocked")
        result = launcher.launch(self.args, run=fake)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["pane_id"], "wX:pY")
        self.assertFalse(any(c[1:3] == ["pane", "send-keys"] for c in fake.calls))

    def test_non_idle_agent_never_receives_input(self):
        fake = FakeHerdr(state="working")
        result = launcher.launch(self.args, run=fake)
        self.assertEqual(result["status"], "failed")
        self.assertFalse(any(c[1:3] == ["agent", "prompt"] for c in fake.calls))

    def test_route_shell_metacharacters_are_quoted(self):
        import shlex
        self.args.model = "model; printf harmless"
        fake = FakeHerdr()
        launcher.launch(self.args, run=fake)
        command = next(c[4] for c in fake.calls if c[1:3] == ["pane", "run"])
        self.assertEqual(shlex.split(command)[4], self.args.model)

    def test_missing_workspace_has_no_effect(self):
        self.args.workspace = None
        fake = FakeHerdr()
        self.assertEqual(launcher.launch(self.args, run=fake)["status"], "failed")
        self.assertEqual(fake.calls, [])

    def test_auto_approve_is_explicit(self):
        self.args.auto_approve = True
        fake = FakeHerdr()
        launcher.launch(self.args, run=fake)
        command = next(c[4] for c in fake.calls if c[1:3] == ["pane", "run"])
        self.assertTrue(command.endswith(" --auto-approve"))

    def test_recovery_uses_returned_pane_without_relaunch(self):
        self.args.pane = "wX:pY"
        fake = FakeHerdr("agent_not_ready")
        result = launcher.launch(self.args, run=fake)
        self.assertEqual(result["status"], "admitted")
        self.assertFalse(any(c[1:3] == ["tab", "create"] for c in fake.calls))
        self.assertEqual(sum(c[1:3] == ["pane", "run"] for c in fake.calls), 1)

    def test_missing_brief_has_no_effect(self):
        self.args.brief += ".missing"
        fake = FakeHerdr()
        result = launcher.launch(self.args, run=fake)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(fake.calls, [])

    def test_timeout_preserves_created_pane(self):
        fake = FakeHerdr()
        def timed(argv, **kwargs):
            if argv[1:3] == ["pane", "wait-output"]:
                raise subprocess.TimeoutExpired(argv, 10)
            return fake(argv, **kwargs)
        result = launcher.launch(self.args, run=timed)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["pane_id"], "wX:pY")
        self.assertFalse(any("close" in c for c in fake.calls))


class FakeSteerHerdr:
    """Models a Term2 TUI: send-text fills the draft, Enter submits it into the transcript."""

    def __init__(self, status="working", agent="term2", ack=True, ack_before_echo=False,
                 land_text=True, empty_prompt=True, transcript=""):
        self.calls = []
        self.status = status
        self.agent = agent
        self.ack = ack
        self.ack_before_echo = ack_before_echo
        self.land_text = land_text
        self.empty_prompt = empty_prompt
        self.draft = ""
        self.transcript = transcript
        self.submitted = ""

    def screen(self):
        return "term2 codex/gpt-6-astra\n  \u276f " + self.draft + "\n Standard"

    def __call__(self, argv, **kwargs):
        self.calls.append(argv)
        op = argv[1:3]
        if op == ["agent", "get"]:
            return subprocess.CompletedProcess(argv, 0, json.dumps(
                {"result": {"agent": {"agent": self.agent, "agent_status": self.status}}}), "")
        if op == ["pane", "read"]:
            if not self.empty_prompt and not self.draft:
                return subprocess.CompletedProcess(argv, 0, "$ shell prompt, no TUI", "")
            return subprocess.CompletedProcess(argv, 0, self.screen(), "")
        if op == ["pane", "send-text"]:
            if self.land_text:
                self.draft = argv[4]
            return subprocess.CompletedProcess(argv, 0, "", "")
        if op == ["pane", "send-keys"]:
            self.submitted, self.draft = self.draft, ""
            return subprocess.CompletedProcess(argv, 0, "", "")
        if op == ["agent", "read"]:
            body = self.transcript + "\n  \u276f " + self.submitted + "\n"
            marker = self.submitted.rsplit("marker ", 1)[-1].rstrip(".") if self.submitted else ""
            if self.ack_before_echo:
                body = marker + " stale earlier mention\n" + body
            elif self.ack and marker:
                body += "\n  " + marker + " -- understood, continuing.\n"
            return subprocess.CompletedProcess(argv, 0, body, "")
        raise AssertionError("unexpected call: " + " ".join(argv))


class SteerTests(unittest.TestCase):
    def setUp(self):
        self.args = argparse.Namespace(pane="w18:pE", message="Use the builtin rollover tool.",
            message_file=None, ack_marker=None, no_ack=False, ack_timeout_ms=5000,
            ack_lines=160, timeout_ms=10000, herdr="herdr")

    def test_acknowledged_round_trip(self):
        fake = FakeSteerHerdr()
        result = launcher.steer(self.args, run=fake)
        self.assertEqual(result["status"], "acknowledged")
        self.assertEqual(result["acknowledgement"], "verified")
        self.assertTrue(result["ack_marker"].startswith("STEER_ACK_"))
        self.assertEqual(sum(c[1:3] == ["pane", "send-text"] for c in fake.calls), 1)
        self.assertEqual(sum(c[1:3] == ["pane", "send-keys"] for c in fake.calls), 1)
        self.assertFalse(any(c[1:3] == ["agent", "prompt"] for c in fake.calls))

    def test_echoed_marker_alone_is_not_acknowledgement(self):
        # The regression that motivated this: the marker appears only BEFORE the echoed
        # message, so matching it anywhere would report a false success.
        fake = FakeSteerHerdr(ack=False, ack_before_echo=True)
        self.args.ack_timeout_ms = 0
        result = launcher.steer(self.args, run=fake)
        self.assertEqual(result["status"], "delivered")
        self.assertEqual(result["acknowledgement"], "timed_out")
        self.assertTrue(result["echo_anchor_found"])

    def test_no_ack_timeout_reports_unverified_not_success(self):
        fake = FakeSteerHerdr(ack=False)
        self.args.ack_timeout_ms = 0
        result = launcher.steer(self.args, run=fake)
        self.assertEqual(result["status"], "delivered")
        self.assertEqual(result["acknowledgement"], "timed_out")
        self.assertNotEqual(result["status"], "acknowledged")

    def test_marker_inside_message_is_refused_before_any_call(self):
        self.args.ack_marker = "ROLLOVER_ACK"
        self.args.message = "Reply ROLLOVER_ACK when done."
        fake = FakeSteerHerdr()
        result = launcher.steer(self.args, run=fake)
        self.assertEqual(result["status"], "failed")
        self.assertIn("indistinguishable", result["error"])
        self.assertEqual(fake.calls, [])

    def test_blocked_worker_never_receives_input(self):
        fake = FakeSteerHerdr(status="blocked")
        result = launcher.steer(self.args, run=fake)
        self.assertEqual(result["status"], "failed")
        self.assertFalse(any(c[1:3] == ["pane", "send-text"] for c in fake.calls))

    def test_non_term2_pane_is_refused(self):
        fake = FakeSteerHerdr(agent="claude")
        result = launcher.steer(self.args, run=fake)
        self.assertEqual(result["status"], "failed")
        self.assertIn("Term2-specific", result["error"])
        self.assertFalse(any(c[1:3] == ["pane", "send-text"] for c in fake.calls))

    def test_pending_draft_or_shell_foreground_is_refused(self):
        fake = FakeSteerHerdr(empty_prompt=False)
        result = launcher.steer(self.args, run=fake)
        self.assertEqual(result["status"], "failed")
        self.assertFalse(any(c[1:3] == ["pane", "send-text"] for c in fake.calls))

    def test_text_that_does_not_land_never_gets_enter(self):
        fake = FakeSteerHerdr(land_text=False)
        self.args.timeout_ms = 1000
        result = launcher.steer(self.args, run=fake)
        self.assertEqual(result["status"], "failed")
        self.assertFalse(any(c[1:3] == ["pane", "send-keys"] for c in fake.calls))

    def test_working_worker_is_steerable(self):
        # Term2 accepts input while generating; steering must not require an idle worker.
        result = launcher.steer(self.args, run=FakeSteerHerdr(status="working"))
        self.assertEqual(result["status"], "acknowledged")

    def test_no_ack_mode_reports_delivery_as_unproven(self):
        self.args.no_ack = True
        result = launcher.steer(self.args, run=FakeSteerHerdr(ack=False))
        self.assertEqual(result["status"], "delivered")
        self.assertEqual(result["acknowledgement"], "not_requested")
        self.assertIsNone(result["ack_marker"])

    def test_empty_message_makes_no_calls(self):
        self.args.message = "   "
        fake = FakeSteerHerdr()
        self.assertEqual(launcher.steer(self.args, run=fake)["status"], "failed")
        self.assertEqual(fake.calls, [])

    def test_message_and_message_file_are_mutually_exclusive(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "note.md"
            path.write_text("from file")
            self.args.message_file = str(path)
            fake = FakeSteerHerdr()
            self.assertEqual(launcher.steer(self.args, run=fake)["status"], "failed")
            self.assertEqual(fake.calls, [])

    def test_message_file_is_used_when_message_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "note.md"
            path.write_text("Switch back to the builtin rollover tool.")
            self.args.message, self.args.message_file = None, str(path)
            fake = FakeSteerHerdr()
            self.assertEqual(launcher.steer(self.args, run=fake)["status"], "acknowledged")
            self.assertIn("builtin rollover", fake.submitted)

    def test_late_render_of_the_draft_is_not_a_delivery_failure(self):
        # Observed live: pane read can race the TUI redraw and show an empty draft
        # immediately after send-text. One read is not evidence the text was lost.
        class LateRender(FakeSteerHerdr):
            reads = 0

            def __call__(self, argv, **kwargs):
                if argv[1:3] == ["pane", "read"] and self.draft:
                    LateRender.reads += 1
                    if LateRender.reads == 1:
                        held, self.draft = self.draft, ""
                        result = super().__call__(argv, **kwargs)
                        self.draft = held
                        return result
                return super().__call__(argv, **kwargs)

        result = launcher.steer(self.args, run=LateRender())
        self.assertEqual(result["status"], "acknowledged")

    def test_transient_read_failure_does_not_abort_the_ack_poll(self):
        # Observed live: agent read returned agent_not_found while the worker was mid-turn.
        # Enter was already delivered, so a failed read proves nothing; keep polling.
        class FlakyRead(FakeSteerHerdr):
            reads = 0

            def __call__(self, argv, **kwargs):
                if argv[1:3] == ["agent", "read"]:
                    FlakyRead.reads += 1
                    if FlakyRead.reads == 1:
                        return subprocess.CompletedProcess(argv, 1, "", json.dumps(
                            {"error": {"code": "agent_not_found", "message": "not found"}}))
                return super().__call__(argv, **kwargs)

        result = launcher.steer(self.args, run=FlakyRead())
        self.assertEqual(result["status"], "acknowledged")

    def test_wrapped_echo_still_anchors_the_acknowledgement(self):
        # The TUI wraps and re-indents the echoed prompt; matching must be whitespace-insensitive.
        class Wrapping(FakeSteerHerdr):
            def __call__(self, argv, **kwargs):
                result = super().__call__(argv, **kwargs)
                if argv[1:3] == ["agent", "read"]:
                    wrapped = result.stdout.replace(" ", "\n     ", 12)
                    return subprocess.CompletedProcess(argv, 0, wrapped, "")
                return result
        self.assertEqual(launcher.steer(self.args, run=Wrapping())["status"], "acknowledged")


class MainDispatchTests(unittest.TestCase):
    def test_bare_flags_still_route_to_launch(self):
        self.assertIn("--brief", launcher.build_launch_parser().format_usage())

    def test_steer_exit_code_is_nonzero_without_verified_ack(self):
        parser = launcher.build_steer_parser()
        args = parser.parse_args(["w18:pE", "--message", "hi", "--ack-timeout-ms", "0"])
        self.assertEqual(args.pane, "w18:pE")
        self.assertFalse(args.no_ack)


if __name__ == "__main__":
    unittest.main()
