import asyncio
import os
import platform
import signal
import subprocess
from typing import Optional


class K6ProcessManager:
    def __init__(self) -> None:
        self.process: Optional[asyncio.subprocess.Process] = None
        self.metrics_process: Optional[asyncio.subprocess.Process] = None

    async def start_run(self) -> asyncio.subprocess.Process:
        extra_args = {}
        if platform.system() == "Windows":
            extra_args["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP

        self.process = await asyncio.create_subprocess_exec(
            "k6",
            "run",
            "test.js",
            "--no-color",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            **extra_args,
        )
        return self.process

    async def start_metrics(self) -> asyncio.subprocess.Process:
        self.metrics_process = await asyncio.create_subprocess_exec(
            "k6",
            "top",
            "--no-thresholds",
            "--no-tags",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return self.metrics_process

    async def stop(self) -> bool:
        stopped = self._stop_process(self.process)
        metrics_stopped = self._stop_process(self.metrics_process)
        return stopped or metrics_stopped

    def _stop_process(self, process: Optional[asyncio.subprocess.Process]) -> bool:
        if process and process.returncode is None:
            try:
                if platform.system() == "Windows":
                    os.kill(process.pid, signal.CTRL_BREAK_EVENT)
                else:
                    process.send_signal(signal.SIGINT)
                return True
            except Exception:
                process.terminate()
                return True
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
        self.metrics_process = None
