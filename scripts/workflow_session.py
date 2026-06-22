#!/usr/bin/env python3
"""Start a tmux session for OpenHRI workflow runs."""

import argparse
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from trial_runner import (
    CONTAINER_REPO_ROOT,
    DEFAULT_DETECTOR_PARAMS,
    DEFAULT_IMAGE,
    TrialError,
    assert_inside_repo,
    load_simple_yaml,
    normalize_trial,
    resolve_recipe_path,
)


def main(argv=None):
    args = parse_args(argv)
    repo_root = Path(__file__).resolve().parents[1]

    if not shutil.which("tmux"):
        print(
            "workflow_session: tmux is not installed on the host. "
            "Install tmux, then rerun make workflow-session.",
            file=sys.stderr,
        )
        return 2

    try:
        trial = resolve_trial(repo_root, args.trial, args.recipe)
        run_dir = (repo_root / args.runs_dir / trial["trial_id"]).resolve()
        assert_inside_repo(repo_root, run_dir, "run directory")
        container_run_dir = CONTAINER_REPO_ROOT / run_dir.relative_to(repo_root).as_posix()

        prepare_trial_plan(repo_root, args)
        commands = session_commands(repo_root, args, trial, run_dir, container_run_dir)

        if args.dry_run:
            print_dry_run(args.session, commands)
            return 0

        start_session(
            args.session,
            commands,
            repo_root,
            args.container,
            attach=not args.no_attach,
        )
        return 0
    except TrialError as exc:
        print(f"workflow_session: {exc}", file=sys.stderr)
        return 2
    except subprocess.CalledProcessError as exc:
        return exc.returncode


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="Open a fresh tmux session for simulation, detector, and run logs."
    )
    parser.add_argument("--trial", default="", help="Trial name in recipes/trials")
    parser.add_argument("--recipe", default="", help="Explicit recipe YAML path")
    parser.add_argument("--runs-dir", default="runs")
    parser.add_argument("--session", default="openhri")
    parser.add_argument("--container", default="openhri-office")
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    parser.add_argument("--platform", default="linux/arm64")
    parser.add_argument("--detector-params", default=DEFAULT_DETECTOR_PARAMS)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and print window commands without creating a tmux session.",
    )
    parser.add_argument(
        "--no-attach",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    return parser.parse_args(argv)


def resolve_trial(repo_root, trial_name, recipe):
    recipe_path = resolve_recipe_path(repo_root, trial_name, recipe)
    recipe_data = load_simple_yaml(recipe_path)
    return normalize_trial(recipe_data, trial_name, recipe_path)


def prepare_trial_plan(repo_root, args):
    command = [
        sys.executable,
        "scripts/trial_runner.py",
        "--no-start",
        "--trial",
        args.trial,
        "--recipe",
        args.recipe,
        "--runs-dir",
        args.runs_dir,
        "--container",
        args.container,
        "--image",
        args.image,
        "--platform",
        args.platform,
        "--detector-params",
        args.detector_params,
    ]
    subprocess.run(command, cwd=repo_root, check=True)


def session_commands(repo_root, args, trial, run_dir, container_run_dir):
    trial_id = trial["trial_id"]
    detector_log = container_run_dir / "detector.log"
    event_log = run_dir / "events.jsonl"
    manifest = run_dir / "manifest.yaml"
    summary = run_dir / "summary.txt"

    make_trial_parts = [
        "make",
        "trial",
        f"TRIAL={trial_id}",
        f"RECIPE={args.recipe}",
        f"RUNS_DIR={args.runs_dir}",
        f"CONTAINER={args.container}",
        f"IMAGE={args.image}",
        f"OPENHRI_PLATFORM={args.platform}",
        f"DETECTOR_PARAMS={args.detector_params}",
    ]
    make_trial = shell_join(make_trial_parts)
    detector_logs = shell_join(
        [
            "make",
            "detector-logs",
            f"CONTAINER={args.container}",
            f"DETECTOR_LOG={str(detector_log)}",
        ]
    )

    return {
        "controls": controls_command(repo_root, args, trial),
        "sim": window_command(
            repo_root,
            "simulation",
            "make sim",
            [
                "make",
                "sim",
                f"CONTAINER={args.container}",
            ],
        ),
        "trial": command_block(
            repo_root,
            "trial + detector log",
            "make trial TRIAL=<trial-id>; make detector-logs",
            " && ".join(
                [
                    f"printf '%s\\n' {shlex.quote('Starting recipe-backed trial: ' + trial_id)}",
                    make_trial,
                    "printf '%s\\n' 'Detector started. Streaming detector log now.'",
                    detector_logs,
                ]
            ),
        ),
        "container": window_command(
            repo_root,
            "container logs",
            "make logs",
            [
                "make",
                "logs",
                f"CONTAINER={args.container}",
            ],
        ),
        "outputs": outputs_command(repo_root, run_dir, event_log, manifest, summary),
        "shell": window_command(
            repo_root,
            "ROS shell",
            "make shell",
            [
                "make",
                "shell",
                f"CONTAINER={args.container}",
            ],
        ),
    }


def controls_command(repo_root, args, trial):
    lines = [
        f"printf '%s\\n' {shlex.quote('OpenHRI workflow session')}",
        f"printf '%s\\n' {shlex.quote('Trial: ' + trial['trial_id'])}",
        "printf '\\n%s\\n' 'Default run window:'",
        "printf '%s\\n' '  top-left      simulation: Gazebo/RViz/Nav2 launch logs'",
        "printf '%s\\n' '  bottom-left   detector: trial startup and detector log stream'",
        "printf '%s\\n' '  top-right     container: supervisor/container logs'",
        "printf '%s\\n' '  bottom-right  outputs: live run folder/events/manifest preview'",
        "printf '\\n%s\\n' 'Extra windows:'",
        "printf '%s\\n' '  shell         Interactive ROS-ready container shell'",
        "printf '%s\\n' '  help          This help and a normal shell prompt'",
        "printf '\\n%s\\n' 'Navigation:'",
        "printf '%s\\n' '  Mouse: click window names in the bottom bar'",
        "printf '%s\\n' '  Keyboard: Ctrl-b then window number, n for next, p for previous'",
        "printf '%s\\n' '  Resize panes: drag pane borders with the mouse'",
        "printf '\\n%s\\n' 'Scrolling:'",
        "printf '%s\\n' '  Mouse wheel scrolls the current window'",
        "printf '%s\\n' "
        "'  Keyboard: Ctrl-b then [, use arrows/PageUp/PageDown, q to exit'",
        "printf '%s\\n' '  scroll mode'",
        "printf '\\n%s\\n' 'Rerunning commands:'",
        "printf '%s\\n' '  When a pane command exits, the pane stays open at a shell prompt'",
        "printf '%s\\n' '  Type rerun to execute that pane command again'",
        "printf '%s\\n' '  Or press Up then Enter to edit/rerun the last command'",
        "printf '\\n%s\\n' 'Stopping:'",
        "printf '%s\\n' '  From inside tmux: Ctrl-b then X, or press F12'",
        "printf '%s\\n' '  From outside tmux: make workflow-stop'",
        "printf '\\n%s\\n' 'Detach without stopping:'",
        "printf '%s\\n' '  Ctrl-b then d'",
        "printf '\\n%s\\n' "
        "'This controls window is a normal shell. Run make workflow-stop here.'",
        "exec bash -i",
    ]
    return shell_block(repo_root, "controls", lines, pause_on_exit=False)


def window_command(repo_root, label, display, command_parts):
    command = shell_join(command_parts)
    return command_block(repo_root, label, display, command)


def command_block(repo_root, label, display, command):
    return shell_block(
        repo_root,
        label,
        display_command=display,
        rerun_command=command,
    )


def outputs_command(repo_root, run_dir, event_log, manifest, summary):
    lines = [
        f"RUN_DIR={shlex.quote(str(run_dir))}",
        f"EVENT_LOG={shlex.quote(str(event_log))}",
        f"MANIFEST={shlex.quote(str(manifest))}",
        f"SUMMARY={shlex.quote(str(summary))}",
        "while true; do",
        "  clear",
        "  date",
        "  printf '\\nRun directory: %s\\n\\n' \"$RUN_DIR\"",
        "  ls -lah \"$RUN_DIR\" 2>/dev/null || true",
        "  printf '\\nsummary.txt\\n'",
        "  sed -n '1,120p' \"$SUMMARY\" 2>/dev/null || printf '%s\\n' 'waiting for summary.txt'",
        "  printf '\\nevents.jsonl tail\\n'",
        "  tail -n 25 \"$EVENT_LOG\" 2>/dev/null || printf '%s\\n' 'waiting for events.jsonl'",
        "  printf '\\nmanifest.yaml head\\n'",
        "  sed -n '1,80p' \"$MANIFEST\" 2>/dev/null || printf '%s\\n' 'waiting for manifest.yaml'",
        "  sleep 3",
        "done",
    ]
    return command_block(
        repo_root,
        "run outputs",
        "watch run outputs",
        "\n".join(lines),
    )


def shell_block(
    repo_root,
    label,
    lines=None,
    pause_on_exit=True,
    display_command=None,
    rerun_command=None,
):
    lines = lines or []
    script = [
        "set -euo pipefail",
        f"cd {shlex.quote(str(repo_root))}",
        f"printf '%s\\n' {shlex.quote('OpenHRI window: ' + label)}",
    ]
    if rerun_command:
        shown_command = display_command or rerun_command
        script.extend(
            [
                f"OPENHRI_LAST_COMMAND={shlex.quote(rerun_command)}",
                "export OPENHRI_LAST_COMMAND",
                f"printf '%s\\n' {shlex.quote('$ ' + shown_command)}",
                'printf "%s\\n" "$OPENHRI_LAST_COMMAND" >> ~/.bash_history',
                'set +e',
                'eval "$OPENHRI_LAST_COMMAND"',
                'status=$?',
                'set -e',
                'printf "\\nCommand exited with status %s. " "$status"',
                'printf "This pane stays open.\\n"',
                'printf "%s\\n" "Run rerun to execute it again."',
                'printf "%s\\n" "Or press Up then Enter to edit/rerun."',
                'rerun() { eval "$OPENHRI_LAST_COMMAND"; }',
                'export -f rerun',
                'exec bash -i',
            ]
        )
    else:
        script.extend(lines)
        if pause_on_exit:
            script.extend(
                [
                    'status=$?',
                    'printf "\\nCommand exited with status %s. " "$status"',
                    'printf "This pane stays open.\\n"',
                    'exec bash -i',
                ]
            )
    return "bash -lc " + shlex.quote("\n".join(script))


def shell_join(parts):
    return " ".join(shlex.quote(str(part)) for part in parts)


def print_dry_run(session, commands):
    print(f"tmux session: {session}")
    for name, command in commands.items():
        print(f"\n[{name}]")
        print(command)


def start_session(session, commands, repo_root, container, attach=True):
    if tmux_session_exists(session):
        replace_existing_session(session, repo_root, container)

    subprocess.run(
        [
            "tmux",
            "new-session",
            "-d",
            "-s",
            session,
            "-n",
            "run",
            initial_shell_command(repo_root),
        ],
        check=True,
    )
    configure_tmux_session(session, repo_root)

    run_target = f"{session}:run"
    sim_pane = current_pane_id(run_target)
    send_window_command(sim_pane, commands["sim"])
    container_pane = split_window(sim_pane, "-h", commands["container"])
    trial_pane = split_window(sim_pane, "-v", commands["trial"])
    outputs_pane = split_window(container_pane, "-v", commands["outputs"])
    for pane, title in (
        (sim_pane, "simulation"),
        (trial_pane, "detector"),
        (container_pane, "container"),
        (outputs_pane, "outputs"),
    ):
        subprocess.run(["tmux", "select-pane", "-t", pane, "-T", title], check=True)
    subprocess.run(
        ["tmux", "new-window", "-t", session, "-n", "shell", commands["shell"]],
        check=True,
    )
    subprocess.run(
        ["tmux", "new-window", "-t", session, "-n", "help", commands["controls"]],
        check=True,
    )
    subprocess.run(["tmux", "select-window", "-t", run_target], check=True)
    if attach:
        subprocess.run(["tmux", "attach-session", "-t", session], check=True)


def initial_shell_command(repo_root):
    return "bash -lc " + shlex.quote(
        "\n".join(
            [
                "set -euo pipefail",
                f"cd {shlex.quote(str(repo_root))}",
                "exec bash -i",
            ]
        )
    )


def current_pane_id(target):
    completed = subprocess.run(
        ["tmux", "display-message", "-p", "-t", target, "#{pane_id}"],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def send_window_command(target, command):
    subprocess.run(["tmux", "send-keys", "-t", target, command, "C-m"], check=True)


def split_window(pane_target, direction, command):
    completed = subprocess.run(
        [
            "tmux",
            "split-window",
            direction,
            "-t",
            pane_target,
            "-P",
            "-F",
            "#{pane_id}",
            command,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def replace_existing_session(session, repo_root, container):
    print(f"Replacing existing tmux session: {session}")
    subprocess.run(["tmux", "kill-session", "-t", session], check=False)
    subprocess.run(
        ["make", "sim-stop", f"CONTAINER={container}"],
        cwd=repo_root,
        check=False,
    )
    subprocess.run(
        ["make", "detector-stop", f"CONTAINER={container}"],
        cwd=repo_root,
        check=False,
    )


def configure_tmux_session(session, repo_root):
    status_right = "Mouse scroll on | Prefix X/F12 stop | Prefix d detach"
    commands = [
        ["tmux", "set-option", "-t", session, "mouse", "on"],
        ["tmux", "set-option", "-t", session, "history-limit", "100000"],
        ["tmux", "set-option", "-t", session, "status-interval", "5"],
        ["tmux", "set-option", "-t", session, "status-left", " OpenHRI #[session_name] "],
        ["tmux", "set-option", "-t", session, "status-right", status_right],
        ["tmux", "set-window-option", "-t", session, "pane-border-status", "top"],
        [
            "tmux",
            "set-window-option",
            "-t",
            session,
            "pane-border-format",
            " #{pane_index}: #{pane_title} ",
        ],
        ["tmux", "set-window-option", "-t", session, "mode-keys", "vi"],
        [
            "tmux",
            "bind-key",
            "X",
            "confirm-before",
            "-p",
            "Stop OpenHRI simulation, detector, and tmux session? (y/n)",
            workflow_stop_tmux_command(repo_root),
        ],
        [
            "tmux",
            "bind-key",
            "-n",
            "F12",
            "confirm-before",
            "-p",
            "Stop OpenHRI simulation, detector, and tmux session? (y/n)",
            workflow_stop_tmux_command(repo_root),
        ],
    ]
    for command in commands:
        subprocess.run(command, check=True)


def workflow_stop_tmux_command(repo_root):
    return "run-shell " + shlex.quote(
        shell_join(["make", "-C", str(repo_root), "workflow-stop"])
    )


def tmux_session_exists(session):
    completed = subprocess.run(
        ["tmux", "has-session", "-t", session],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return completed.returncode == 0


if __name__ == "__main__":
    raise SystemExit(main())
