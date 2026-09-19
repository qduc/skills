#!/usr/bin/env python3
"""Start one interactive Term2 tab and submit a brief, or steer a running Term2 worker.

Term2 has no Herdr agent integration, so `herdr agent prompt` always fails with
`agent_not_ready`. Both subcommands here reach Term2 through verified pane input
instead. Emits a JSON receipt on stdout.
"""

import argparse
import json
import os
from pathlib import Path
import re
import secrets
import shlex
import subprocess
import sys
import time

PROMPT_LINE = r"(?m)^ *\u276f *$"


def collapse(text):
    """Whitespace-insensitive form, so TUI wrapping and indentation do not defeat matching."""
    return "".join(str(text).split())


class LaunchError(Exception):
    pass


def launch(args, run=subprocess.run):
    receipt = {"status": "failed", "workspace_id": args.workspace,
               "provider": args.provider, "model": args.model,
               "effort": args.effort, "acknowledgement": "not_verified"}

    def call(*parts):
        return run([args.herdr, *parts], capture_output=True, text=True,
                   timeout=args.timeout_ms / 1000 + 2)

    def decode(result):
        try:
            return json.loads(result.stdout.strip() or result.stderr.strip())
        except (ValueError, TypeError) as error:
            raise LaunchError("Invalid Herdr JSON: " + (result.stderr or result.stdout)) from error

    def checked(*parts):
        result = call(*parts)
        if result.returncode:
            raise LaunchError(result.stderr or result.stdout or "Herdr command failed")
        return result

    def idle(pane):
        data = decode(checked("agent", "get", pane))["result"]["agent"]
        if data.get("agent") != "term2" or data.get("agent_status") not in ("idle", "done"):
            raise LaunchError("Expected an idle interactive Term2; refusing terminal input")

    def visible(pane):
        return checked("pane", "read", pane, "--source", "visible", "--lines", "80").stdout

    def wait_working(pane):
        result = call("agent", "wait", pane, "--until", "working",
                      "--timeout", str(args.timeout_ms))
        data = decode(result)
        if not result.returncode and data.get("result", {}).get("agent", {}).get("agent_status") == "working":
            return True
        if data.get("error", {}).get("code") != "timeout":
            raise LaunchError(result.stderr or result.stdout)
        return False

    try:
        for value in (args.workspace, args.provider, args.model, args.label, args.herdr, args.term2):
            if not value or any(ord(char) < 32 for char in value):
                raise LaunchError("Workspace, route, label and executable names must be explicit single-line values")
        if not 1000 <= args.timeout_ms <= 120000:
            raise LaunchError("timeout-ms must be 1000..120000 (launch/admission only)")
        cwd = Path(args.cwd).resolve(strict=True)
        brief = Path(args.brief).resolve(strict=True)
        if not cwd.is_dir() or not brief.is_file():
            raise LaunchError("cwd must be a directory and brief must be a file")
        if any(ord(char) < 32 for char in str(brief)):
            raise LaunchError("Brief path must be single-line")
        with brief.open("rb") as source:
            source.read(1)
        prompt = "Read " + str(brief) + " and execute only that assignment. First acknowledge the task ID and your provider/model route."
        receipt.update(cwd=str(cwd), brief=str(brief))
        if args.pane:
            pane = args.pane
            receipt["pane_id"] = pane
            idle(pane)
            screen = visible(pane)
            route = (args.provider + "/" + args.model).lower()
            if route not in screen.lower():
                raise LaunchError("Recovery pane does not visibly match the requested route")
        else:
            created = decode(checked("tab", "create", "--workspace", args.workspace,
                "--label", args.label, "--cwd", str(cwd), "--no-focus"))["result"]
            pane = created["root_pane"]["pane_id"]
            receipt.update(pane_id=pane, tab_id=created["tab"]["tab_id"])
            command = [args.term2, "-p", args.provider, "-m", args.model]
            if args.effort:
                command += ["-r", args.effort]
            if args.auto_approve:
                command.append("--auto-approve")
            checked("pane", "run", pane, shlex.join(command))
        checked("pane", "wait-output", pane, "--source", "visible",
                "--regex", PROMPT_LINE, "--timeout", str(args.timeout_ms))
        idle(pane)
        result = call("agent", "prompt", pane, prompt, "--wait", "--until", "working",
                      "--timeout", str(args.timeout_ms))
        data = decode(result)
        if result.returncode == 0:
            if data.get("result", {}).get("agent", {}).get("agent_status") != "working":
                raise LaunchError("Prompt accepted without attributable working admission")
            receipt["transport"] = "agent-prompt"
        elif data.get("error", {}).get("code") == "agent_not_ready":
            idle(pane)
            if not re.search(PROMPT_LINE, visible(pane)):
                raise LaunchError("No empty interactive prompt; refusing fallback input")
            receipt["transport"] = "verified-idle-pane"
            checked("pane", "run", pane, prompt)
            checked("pane", "send-keys", pane, "enter")
            if not wait_working(pane):
                screen = visible(pane)
                idle(pane)
                draft = screen.rsplit("\u276f", 1)[-1] if "\u276f" in screen else ""
                if not collapse(draft).startswith(collapse(prompt)):
                    raise LaunchError("Admission unknown; no matching idle draft. Input not repeated")
                checked("pane", "send-keys", pane, "enter")
                if not wait_working(pane):
                    raise LaunchError("Admission unknown after one Enter-only recovery")
        else:
            raise LaunchError(result.stderr or result.stdout)
        receipt["status"] = "admitted"
        receipt["next_action"] = "Verify worker acknowledgement; attach a bounded lifecycle wait. Admission is not task completion."
    except (LaunchError, OSError, KeyError, TypeError, subprocess.TimeoutExpired) as error:
        receipt["error"] = str(error)
        receipt["next_action"] = "Inspect the returned pane before retrying. It is preserved; no cleanup or relaunch was attempted."
    return receipt


def steer(args, run=subprocess.run):
    """Deliver a mid-flight correction to an already-running interactive Term2 worker.

    Term2 accepts input while generating (Enter steers at the next request boundary),
    so this does not require an idle worker -- only a real Term2 TUI showing an empty
    input line. Acknowledgement is checked against output that appears *after* the
    echoed message, because terminal echo of the message is not evidence of delivery.
    """
    receipt = {"status": "failed", "pane_id": args.pane,
               "transport": "verified-pane-input", "acknowledgement": "not_verified"}

    def call(*parts):
        return run([args.herdr, *parts], capture_output=True, text=True,
                   timeout=args.timeout_ms / 1000 + 2)

    def decode(result):
        try:
            return json.loads(result.stdout.strip() or result.stderr.strip())
        except (ValueError, TypeError) as error:
            raise LaunchError("Invalid Herdr JSON: " + (result.stderr or result.stdout)) from error

    def checked(*parts):
        result = call(*parts)
        if result.returncode:
            raise LaunchError(result.stderr or result.stdout or "Herdr command failed")
        return result

    def visible():
        return checked("pane", "read", args.pane, "--source", "visible", "--lines", "80").stdout

    try:
        for value in (args.pane, args.herdr):
            if not value or any(ord(char) < 32 for char in value):
                raise LaunchError("Pane and executable names must be explicit single-line values")
        if not 1000 <= args.timeout_ms <= 120000:
            raise LaunchError("timeout-ms must be 1000..120000 (per-step deadline)")
        if not 0 <= args.ack_timeout_ms <= 600000:
            raise LaunchError("ack-timeout-ms must be 0..600000")
        if not 20 <= args.ack_lines <= 400:
            raise LaunchError("ack-lines must be 20..400")
        message = args.message
        if args.message_file:
            if message:
                raise LaunchError("Pass either --message or --message-file, not both")
            message = Path(args.message_file).resolve(strict=True).read_text()
        message = (message or "").strip()
        if not message:
            raise LaunchError("Message must be a non-empty single value")

        marker = None
        payload = message
        if not args.no_ack:
            marker = args.ack_marker or ("STEER_ACK_" + secrets.token_hex(4).upper())
            if any(ord(char) < 32 for char in marker) or not marker.strip():
                raise LaunchError("Ack marker must be an explicit single-line value")
            if collapse(marker) in collapse(message):
                raise LaunchError(
                    "Message already contains the ack marker; its echo would be "
                    "indistinguishable from an acknowledgement")
            payload = message + " Acknowledge this correction by replying with the exact marker " + marker + "."
        receipt["ack_marker"] = marker

        agent = decode(checked("agent", "get", args.pane))["result"]["agent"]
        receipt["agent_status"] = agent.get("agent_status")
        if agent.get("agent") != "term2":
            raise LaunchError("Pane is not a Term2 agent; this transport is Term2-specific")
        if agent.get("agent_status") not in ("working", "idle", "done"):
            raise LaunchError(
                "Refusing input to a " + str(agent.get("agent_status")) +
                " Term2; resolve that state before steering")
        if not re.search(PROMPT_LINE, visible()):
            raise LaunchError(
                "No empty Term2 input line; refusing to append to a pending draft "
                "or to a non-Term2 foreground process")

        checked("pane", "send-text", args.pane, payload)
        # The TUI redraws asynchronously, so a single read can race the render and
        # wrongly conclude the text never landed. Poll until it appears or the step
        # deadline passes; Enter is withheld until the draft is confirmed.
        landed = False
        render_deadline = time.monotonic() + args.timeout_ms / 1000
        while True:
            screen = visible()
            draft = screen.rsplit("\u276f", 1)[-1] if "\u276f" in screen else ""
            landed = collapse(draft).startswith(collapse(payload))
            remaining = render_deadline - time.monotonic()
            if landed or remaining <= 0:
                break
            time.sleep(min(0.5, remaining))
        if not landed:
            raise LaunchError("Message did not land in the input box; Enter was not sent")
        checked("pane", "send-keys", args.pane, "enter")
        receipt["status"] = "delivered"

        if args.no_ack:
            receipt["acknowledgement"] = "not_requested"
            receipt["next_action"] = ("Delivery to the input box was verified and Enter was sent. "
                                      "Terminal echo is not proof the worker ingested it; confirm in its own output.")
            return receipt

        flat_payload = collapse(payload)
        flat_marker = collapse(marker)
        deadline = time.monotonic() + args.ack_timeout_ms / 1000
        anchored = False
        while True:
            # A read can fail transiently (observed: agent_not_found while the worker was
            # mid-turn). Enter is already delivered, so a failed read is not evidence of
            # anything -- keep polling to the deadline instead of aborting the whole steer.
            read_result = call("agent", "read", args.pane, "--source", "recent-unwrapped",
                               "--lines", str(args.ack_lines))
            output = read_result.stdout if read_result.returncode == 0 else ""
            flat = collapse(output)
            anchor = flat.rfind(flat_payload)
            anchored = anchored or anchor >= 0
            if anchor >= 0 and flat_marker in flat[anchor + len(flat_payload):]:
                receipt["status"] = "acknowledged"
                receipt["acknowledgement"] = "verified"
                receipt["next_action"] = "Correction reached the worker. Resume normal monitoring."
                return receipt
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            time.sleep(min(2.0, remaining))

        receipt["acknowledgement"] = "timed_out"
        receipt["echo_anchor_found"] = anchored
        receipt["next_action"] = (
            "Marker not seen after the echoed message within the deadline. "
            + ("The worker may still be mid-turn; re-check its output before resending -- "
               "do not resend blindly, Enter was already delivered."
               if anchored else
               "The echoed message was not found in the read window either; raise --ack-lines "
               "and re-check before concluding anything about delivery."))
    except (LaunchError, OSError, KeyError, TypeError, ValueError, subprocess.TimeoutExpired) as error:
        receipt["error"] = str(error)
        receipt.setdefault("next_action",
                           "Inspect the pane before retrying. No cleanup or resend was attempted.")
    return receipt


def build_launch_parser():
    parser = argparse.ArgumentParser(prog="start_term2.py",
                                     description="Start one interactive Term2 tab and submit a brief.")
    parser.add_argument("--workspace", default=os.environ.get("HERDR_WORKSPACE_ID"),
                        help="Explicit workspace, defaults only to HERDR_WORKSPACE_ID")
    parser.add_argument("--pane", help="Recover a previously created, idle empty TUI after inspecting its failure receipt; skip creation and launch")
    parser.add_argument("--cwd", required=True)
    parser.add_argument("--brief", required=True)
    parser.add_argument("--provider", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--effort", choices=("none", "minimal", "low", "medium", "high", "xhigh", "default"))
    parser.add_argument("--label", required=True)
    parser.add_argument("--auto-approve", action="store_true", help="Explicitly enable Term2 auto-approval")
    parser.add_argument("--timeout-ms", type=int, default=10000, help="Per-step launch/admission deadline; not worker runtime")
    parser.add_argument("--herdr", default="herdr", help="Herdr executable (not a shell command)")
    parser.add_argument("--term2", default="term2", help="Term2 executable (not a shell command)")
    return parser


def build_steer_parser():
    parser = argparse.ArgumentParser(prog="start_term2.py steer",
                                     description="Steer a running interactive Term2 worker through verified pane input.")
    parser.add_argument("pane", help="Explicit Term2 pane id; never the visually focused pane")
    parser.add_argument("--message", help="Correction text; mutually exclusive with --message-file")
    parser.add_argument("--message-file", help="Read the correction text from this file")
    parser.add_argument("--ack-marker", help="Marker the worker must echo back; defaults to a fresh random STEER_ACK_<hex>")
    parser.add_argument("--no-ack", action="store_true",
                        help="Do not append an acknowledgement request and do not verify one. Delivery is then unproven.")
    parser.add_argument("--ack-timeout-ms", type=int, default=180000,
                        help="How long to wait for the worker to write the marker after the echoed message")
    parser.add_argument("--ack-lines", type=int, default=160, help="Lines of agent output to scan for the acknowledgement")
    parser.add_argument("--timeout-ms", type=int, default=10000, help="Per-step Herdr command deadline")
    parser.add_argument("--herdr", default="herdr", help="Herdr executable (not a shell command)")
    return parser


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "steer":
        result = steer(build_steer_parser().parse_args(argv[1:]))
        # Unverified delivery is not success: only an explicit --no-ack run exits 0 on "delivered".
        ok = (result["status"] == "acknowledged"
              or (result["status"] == "delivered" and result["acknowledgement"] == "not_requested"))
    else:
        result = launch(build_launch_parser().parse_args(argv))
        ok = result["status"] == "admitted"
    print(json.dumps(result, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
