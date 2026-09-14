"""
Deploy tool for Personal AI Assistant -> Raspberry Pi (over SSH)

Syncs the project to a Raspberry Pi, (re)creates its virtual environment,
installs dependencies, and optionally installs/enables a systemd service
so the bot runs continuously and restarts on boot/crash.

Usage:
    python deploy/deploy.py --host pi.local --user pi

Configuration can also be supplied via deploy/deploy.env (see deploy.env.example),
so you don't have to pass flags every time. CLI flags always win over the file.

Requires on the local machine: ssh, scp, tar (all present on Windows 10+/macOS/Linux).
Requires on the Pi: python3, python3-venv, ssh access, and sudo (only if --service is used).
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEPLOY_DIR = Path(__file__).resolve().parent
SERVICE_TEMPLATE = DEPLOY_DIR / "personal-ai-assistant.service.template"

# Files/dirs never synced to the Pi
EXCLUDES = [
    ".git",
    "venv",
    "__pycache__",
    "*.pyc",
    "memory.db",
    "deploy",
    ".pytest_cache",
    ".coverage",
    "htmlcov",
]


def load_env_file(path: Path) -> dict:
    values = {}
    if not path.exists():
        return values
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip()
    return values


def run(cmd, **kwargs):
    print(f"[RUN] {' '.join(cmd)}")
    return subprocess.run(cmd, check=True, **kwargs)


def build_ssh_target(user: str, host: str) -> str:
    return f"{user}@{host}" if user else host


def ssh_base_args(port: str, key: str) -> list:
    args = []
    if port:
        args += ["-p", str(port)]
    if key:
        args += ["-i", key]
    return args


def sync_project(target: str, remote_path: str, ssh_args: list) -> None:
    """Stream a tar of the project (minus excludes) straight into the Pi over ssh."""
    print(f"[STEP] Syncing project files to {target}:{remote_path}")

    tar_cmd = ["tar", "czf", "-"]
    for pattern in EXCLUDES:
        tar_cmd += ["--exclude", pattern]
    tar_cmd += ["-C", str(PROJECT_ROOT), "."]

    remote_cmd = f"mkdir -p {remote_path} && tar xzf - -C {remote_path}"
    ssh_cmd = ["ssh"] + ssh_args + [target, remote_cmd]

    print(f"[RUN] {' '.join(tar_cmd)} | {' '.join(ssh_cmd)}")
    tar_proc = subprocess.Popen(tar_cmd, stdout=subprocess.PIPE)
    ssh_proc = subprocess.Popen(ssh_cmd, stdin=tar_proc.stdout)
    tar_proc.stdout.close()
    ssh_proc.communicate()
    if ssh_proc.returncode != 0:
        raise subprocess.CalledProcessError(ssh_proc.returncode, ssh_cmd)


def copy_env_file(target: str, remote_path: str, scp_args: list) -> None:
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        print("[WARN] No local .env file found — skipping secret sync. "
              "Create one on the Pi manually before starting the bot.")
        return
    print("[STEP] Copying .env with credentials to the Pi")
    run(["scp"] + scp_args + [str(env_path), f"{target}:{remote_path}/.env"])


def remote_setup(target: str, remote_path: str, ssh_args: list) -> None:
    print("[STEP] Creating/updating virtual environment and installing dependencies on the Pi")
    remote_cmd = (
        f"cd {remote_path} && "
        "python3 -m venv venv && "
        "venv/bin/pip install --upgrade pip && "
        "venv/bin/pip install -r requirements.txt"
    )
    run(["ssh"] + ssh_args + [target, remote_cmd])


def install_service(target: str, remote_path: str, ssh_args: list, scp_args: list,
                     service_name: str, user: str) -> None:
    if remote_path.startswith("~"):
        raise ValueError(
            "--path must be an absolute path when using --service "
            "(systemd does not expand '~'). Try e.g. /home/pi/personal-ai-assistant"
        )

    print(f"[STEP] Installing systemd service '{service_name}'")

    template = SERVICE_TEMPLATE.read_text()
    rendered = template.format(
        remote_path=remote_path,
        user=user or "pi",
    )

    tmp_service_path = DEPLOY_DIR / f"{service_name}.service"
    tmp_service_path.write_text(rendered)

    try:
        run(["scp"] + scp_args + [str(tmp_service_path), f"{target}:/tmp/{service_name}.service"])
        remote_cmd = (
            f"sudo mv /tmp/{service_name}.service /etc/systemd/system/{service_name}.service && "
            "sudo systemctl daemon-reload && "
            f"sudo systemctl enable {service_name} && "
            f"sudo systemctl restart {service_name}"
        )
        run(["ssh"] + ssh_args + [target, remote_cmd])
    finally:
        tmp_service_path.unlink(missing_ok=True)

    print(f"[INFO] Service installed. Check status with: ssh {target} sudo systemctl status {service_name}")


def restart_service(target: str, ssh_args: list, service_name: str) -> None:
    print(f"[STEP] Restarting service '{service_name}'")
    run(["ssh"] + ssh_args + [target, f"sudo systemctl restart {service_name}"])


def main():
    env_config = load_env_file(DEPLOY_DIR / "deploy.env")

    parser = argparse.ArgumentParser(description="Deploy Personal AI Assistant to a Raspberry Pi over SSH")
    parser.add_argument("--host", default=env_config.get("PI_HOST"), help="Pi hostname or IP")
    parser.add_argument("--user", default=env_config.get("PI_USER", "pi"), help="SSH user on the Pi")
    parser.add_argument("--port", default=env_config.get("PI_PORT"), help="SSH port")
    parser.add_argument("--key", default=env_config.get("PI_SSH_KEY"), help="Path to SSH private key")
    parser.add_argument("--path", default=env_config.get("PI_REMOTE_PATH", "~/personal-ai-assistant"),
                         help="Remote directory to deploy into")
    parser.add_argument("--service-name", default=env_config.get("SERVICE_NAME", "personal-ai-assistant"),
                         help="systemd service name")
    parser.add_argument("--service", action="store_true",
                         help="Install/refresh the systemd service so the bot runs on boot")
    parser.add_argument("--skip-env", action="store_true",
                         help="Do not copy the local .env file to the Pi")
    parser.add_argument("--no-sync", action="store_true",
                         help="Skip file sync (only re-run setup/service steps)")
    parser.add_argument("--restart-only", action="store_true",
                         help="Skip sync/setup/service install; just restart the running service")
    args = parser.parse_args()

    if not args.host:
        parser.error("--host is required (or set PI_HOST in deploy/deploy.env)")

    target = build_ssh_target(args.user, args.host)
    ssh_args = ssh_base_args(args.port, args.key)
    scp_args = ssh_base_args(args.port, args.key)
    # scp uses -P for port, not -p
    if args.port:
        scp_args = ["-P", str(args.port)] + ([ "-i", args.key ] if args.key else [])

    try:
        if args.restart_only:
            restart_service(target, ssh_args, args.service_name)
            print("[DONE] Service restarted.")
            return

        if not args.no_sync:
            sync_project(target, args.path, ssh_args)
            if not args.skip_env:
                copy_env_file(target, args.path, scp_args)

        remote_setup(target, args.path, ssh_args)

        if args.service:
            install_service(target, args.path, ssh_args, scp_args, args.service_name, args.user)
        else:
            print("[INFO] Skipping systemd service install (pass --service to enable it).")
            print(f"[INFO] To run manually: ssh {target} \"cd {args.path} && venv/bin/python agent.py\"")

        print("[DONE] Deployment complete.")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Command failed with exit code {e.returncode}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
