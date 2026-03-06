import asyncio
import ipaddress
import os
import platform
import signal
import subprocess
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse


class K6ProcessManager:
    def __init__(self) -> None:
        self.process: Optional[asyncio.subprocess.Process] = None

    async def start_run(
        self,
        enable_web_dashboard: bool = False,
        web_dashboard_url: str | None = None,
        summary_json_path: str | None = None,
        enable_html_summary: bool = False,
    ) -> asyncio.subprocess.Process:
        extra_args = {}
        if platform.system() == "Windows":
            extra_args["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP

        env = os.environ.copy()

        command = ["k6", "run", "test.js", "--no-color"]
        if enable_web_dashboard:
            # Keep both CLI output and env flags for compatibility across k6 versions/builds.
            command.extend(["--out", "web-dashboard=period=1s&open=false"])
            env["K6_WEB_DASHBOARD"] = "true"
            env["K6_WEB_DASHBOARD_EXPORT"] = "artifacts/dashboard.html"
            env["K6_WEB_DASHBOARD_OPEN"] = "false"
            env.pop("K6_WEB_DASHBOARD_HOST", None)
            env.pop("K6_WEB_DASHBOARD_PORT", None)
            self._apply_web_dashboard_binding(env, web_dashboard_url)
        if enable_html_summary and summary_json_path:
            summary_dir = Path(summary_json_path).parent
            if str(summary_dir) not in {"", "."}:
                summary_dir.mkdir(parents=True, exist_ok=True)
            command.extend(["--summary-export", summary_json_path])

        self.process = await asyncio.create_subprocess_exec(
            *command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            **extra_args,
        )
        return self.process

    def _apply_web_dashboard_binding(self, env: dict[str, str], web_dashboard_url: str | None) -> None:
        if not web_dashboard_url:
            return

        candidate = web_dashboard_url if "://" in web_dashboard_url else f"//{web_dashboard_url}"
        parsed = urlparse(candidate)
        host = parsed.hostname
        if host:
            env["K6_WEB_DASHBOARD_HOST"] = "0.0.0.0" if self._is_loopback_host(host) else host
        if parsed.port:
            env["K6_WEB_DASHBOARD_PORT"] = str(parsed.port)

    @staticmethod
    def _is_loopback_host(host: str) -> bool:
        if host.lower() == "localhost":
            return True

        try:
            return ipaddress.ip_address(host).is_loopback
        except ValueError:
            return False

    async def stop(self) -> bool:
        if self.process and self.process.returncode is None:
            try:
                if platform.system() == "Windows":
                    os.kill(self.process.pid, signal.CTRL_BREAK_EVENT)
                else:
                    self.process.send_signal(signal.SIGINT)
                return True
            except Exception:
                if self.process:
                    self.process.terminate()
        return False

    async def scale(self, target_vus: int) -> tuple[int, bytes, bytes]:
        process = await asyncio.create_subprocess_exec(
            "k6",
            "scale",
            "--vus",
            str(target_vus),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        return process.returncode, stdout, stderr

    async def status(self) -> tuple[int, bytes, bytes]:
        process = await asyncio.create_subprocess_exec(
            "k6", "status", stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        return process.returncode, stdout, stderr

    def clear_process(self) -> None:
        self.process = None
