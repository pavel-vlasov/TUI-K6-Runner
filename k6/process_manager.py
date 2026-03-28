import asyncio
import logging
import os
import platform
import signal
import subprocess
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


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
            command.extend(["--out", "web-dashboard=period=5s&open=false"])
            env["K6_WEB_DASHBOARD_OPEN"] = "false"
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
            logger.info("Web dashboard URL is not set, using k6 default binding.")
            return

        parsed = urlparse(web_dashboard_url)
        host = parsed.hostname
        if host:
            env["K6_WEB_DASHBOARD_HOST"] = host
        else:
            logger.warning(
                "Could not determine web dashboard host from URL '%s'; using k6 default host.",
                web_dashboard_url,
            )
        if parsed.port:
            env["K6_WEB_DASHBOARD_PORT"] = str(parsed.port)
        else:
            logger.info(
                "Web dashboard URL '%s' does not include a port; using k6 default port.",
                web_dashboard_url,
            )

    async def stop(self, timeout: float = 5.0) -> bool:
        if not self.process:
            return False

        if self.process.returncode is not None:
            return True

        try:
            if platform.system() == "Windows":
                os.kill(self.process.pid, signal.CTRL_BREAK_EVENT)
            else:
                self.process.send_signal(signal.SIGINT)
        except Exception:
            logger.exception("Failed to send graceful stop signal, escalating to terminate().")
            self.process.terminate()

        try:
            await asyncio.wait_for(self.process.wait(), timeout=timeout)
            return self.process.returncode is not None
        except asyncio.TimeoutError:
            logger.warning("Graceful stop timed out after %.2fs, escalating to terminate().", timeout)

        self.process.terminate()
        try:
            await asyncio.wait_for(self.process.wait(), timeout=timeout)
            return self.process.returncode is not None
        except asyncio.TimeoutError:
            logger.warning("Terminate timed out after %.2fs, escalating to kill().", timeout)

        self.process.kill()
        try:
            await asyncio.wait_for(self.process.wait(), timeout=timeout)
            return self.process.returncode is not None
        except asyncio.TimeoutError:
            logger.error("Kill timed out after %.2fs.", timeout)
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
