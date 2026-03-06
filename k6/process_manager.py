import asyncio
import os
import platform
import signal
import subprocess
from collections.abc import AsyncIterator
from typing import Optional


class K6ProcessManager:
    API_ADDRESS = "127.0.0.1:6565"

    def __init__(self) -> None:
        self.process: Optional[asyncio.subprocess.Process] = None

    async def start_run(self) -> asyncio.subprocess.Process:
        extra_args = {}
        if platform.system() == "Windows":
            extra_args["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP

        self.process = await asyncio.create_subprocess_exec(
            "k6",
            "run",
            "test.js",
            "--no-color",
            "--address",
            self.API_ADDRESS,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            **extra_args,
        )
        return self.process

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
            "--address",
            self.API_ADDRESS,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        return process.returncode, stdout, stderr

    async def status(self) -> tuple[int, bytes, bytes]:
        process = await asyncio.create_subprocess_exec(
            "k6", "status", "--address", self.API_ADDRESS, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        return process.returncode, stdout, stderr

    async def stream_metrics_events(self) -> AsyncIterator[str]:
        reader, writer = await asyncio.open_connection("127.0.0.1", 6565)

        request = (
            "GET /v1/metrics HTTP/1.1\r\n"
            "Host: 127.0.0.1:6565\r\n"
            "Accept: text/event-stream\r\n"
            "Cache-Control: no-cache\r\n"
            "Connection: keep-alive\r\n\r\n"
        )
        writer.write(request.encode("utf-8"))
        await writer.drain()

        try:
            status_line = (await reader.readline()).decode("utf-8", errors="replace").strip()
            if "200" not in status_line:
                raise RuntimeError(f"SSE connection failed: {status_line or 'empty response'}")

            while True:
                line = await reader.readline()
                if not line or line == b"\r\n":
                    break

            current_data: list[str] = []
            while True:
                raw_line = await reader.readline()
                if not raw_line:
                    break

                line = raw_line.decode("utf-8", errors="replace").rstrip("\r\n")
                if line.startswith("data:"):
                    current_data.append(line[5:].lstrip())
                    continue

                if not line:
                    if current_data:
                        yield "\n".join(current_data)
                        current_data.clear()
        finally:
            writer.close()
            await writer.wait_closed()

    def clear_process(self) -> None:
        self.process = None
