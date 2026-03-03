import subprocess
import asyncio
import re
import platform
import time
import signal
import os
import json

class K6Logic:
    def __init__(self):
        self.success_count = 0
        self.fail_count = 0
        self.last_counter = "✅ 0  │  ❌ 0"
        self.status_running = "Waiting for the run..."
        self.status_default = "Prepairing..."
        self.last_update_time = 0
        self.process = None 
        self.is_running = False
        self.current_vus_internal = 1

    @staticmethod
    def clean_cursor_sequences(line: str) -> str:
        line = re.sub(r'\x1b\[[0-9;]*[ABCDGKsu]', '', line)
        line = re.sub(r'\\x1b\[[0-9;]*[ABCDGKsu]', '', line)
        line = line.replace('\\"', '"')
        line = line.replace('\\n', '\n')
        if '\x1b' in line:
            ansi_escape = re.compile(r'(?:\x1B[@-_]|[\x80-\x9F])[0-?]*[ -/]*[@-~]')
            line = ansi_escape.sub('', line)
        return line

    async def stop_k6_process(self):
        if self.process and self.process.returncode is None:
            try:
                if platform.system() == "Windows":
                    os.kill(self.process.pid, signal.CTRL_BREAK_EVENT)
                else:
                    self.process.send_signal(signal.SIGINT)
                return True
            except Exception:
                if self.process: self.process.terminate()
        return False

    async def run_k6_process(self, on_log, on_status, output_to_ui: bool = True):
        if self.is_running:
            # already running — block parallel start
            try:
                on_status("[bold red]⛔ k6 уже выполняется. Дождитесь завершения текущего запуска.[/bold red]")
                on_log("[bold red]⛔ Повторный запуск заблокирован: тест уже идёт.[/bold red]\n")
            except Exception:
                pass
            return

        self.is_running = True
        self.success_count = 0
        self.fail_count = 0
        self.last_counter = "requests: ✅ 0  │  ❌ 0"
        self.last_update_time = 0
        
        try:
            if output_to_ui:
                on_status("[bold yellow]🚀 Preparing test execution...[/bold yellow]")
                on_log("[bold cyan]Starting k6 test in UI...[/bold cyan]\n")
                
                extra_args = {}
                if platform.system() == "Windows":
                    extra_args["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP

                self.process = await asyncio.create_subprocess_exec(
                    "k6", "run", "test.js", "--no-color",
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    **extra_args
                )

                async def read_stream(stream, color):
                    while True:
                        line = await stream.readline()
                        if not line: break
                        
                        text = line.decode('utf-8', errors='replace').rstrip()
                        clean_text = self.clean_cursor_sequences(text)
                        if not clean_text.strip(): continue


                        is_running_line = "running (" in clean_text and "VUs" in clean_text
                        is_default_line = "default" in clean_text and "%" in clean_text
                        is_scenario_progress_line = bool(
                            re.search(r"^\s*[A-Za-z0-9_-]+\s+\[\s*\d+%\s*\]\s+\d+/\d+\s+VUs\s+\S+/\S+", clean_text)
                        )
                        if is_running_line or is_default_line or is_scenario_progress_line:
                            if is_running_line:
                                self.status_running = clean_text
                            if is_default_line or is_scenario_progress_line:
                                self.status_default = clean_text
                            if time.time() - self.last_update_time > 0.1:
                                self._update_ui(on_status)
                                self.last_update_time = time.time()
                            continue


                        is_success_msg = 'msg="Processed request: 200 ✅"' in clean_text
                        is_fail_msg = 'msg="❌' in clean_text or "Non-200" in clean_text

                        if is_success_msg:
                            self.success_count += 1
                            self.last_counter = f"requests: ✅ {self.success_count}  [bold white]│[/bold white]  ❌ {self.fail_count}"
                            self._update_ui(on_status)
                            continue 
                        
                        if is_fail_msg:
                            self.fail_count += 1
                            self.last_counter = f"requests: ✅ {self.success_count}  [bold white]│[/bold white]  ❌ {self.fail_count}"
                            self._update_ui(on_status)
                            continue

  
                        on_log(f"[{color}]{clean_text}[/{color}]")

                await asyncio.gather(
                    read_stream(self.process.stdout, "white"),
                    read_stream(self.process.stderr, "pale_turquoise4")
                )
                
                await self.process.wait()
                on_log("\n[bold green]✅ Test finished.[/bold green]")
                on_status(f"[bold green]✅ Done. [/bold green]\n[bold]{self.last_counter}[/bold]")
            
            else:
                on_log("📤 k6 starting in external terminal.\n")
                
                if platform.system() == "Windows":
                    subprocess.Popen('start powershell.exe -NoExit -Command "chcp 65001; k6 run test.js"', shell=True)
                else:
                    subprocess.Popen(["x-terminal-emulator", "-e", "bash", "-c", "k6 run test.js; exec bash"])
                
                on_status("[bold green]📤 External terminal is started.[/bold green]")


                
        except Exception as e:
            on_log(f"[bold red]💥 Error: {str(e)}[/bold red]")
        finally:
            self.is_running = False
            self.process = None

    def _update_ui(self, on_status):
        on_status(
            f"[bold]📊 {self.last_counter}[/bold]\n"
            f"[bold]🔄 {self.status_running}[/bold]\n"
            f"[bold]📈 {self.status_default}[/bold]"
        )

    async def get_current_vus(self):
        try:
            process = await asyncio.create_subprocess_exec(
                "k6", "status",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, _ = await process.communicate()
            
            if process.returncode == 0:
                data = json.loads(stdout.decode())
                vus = data.get('vus') or data.get('metrics', {}).get('vus', {}).get('value')
                if vus is not None:
                    self.current_vus_internal = int(vus)
                    return self.current_vus_internal
        except Exception:
            pass
        return self.current_vus_internal

    async def set_vus(self, target_vus: int, on_log):
        if not self.is_running:
            on_log("[bold red]❌ No active execution[/bold red]\n")
            return

        if target_vus < 1:
            target_vus = 1

        try:
            scale_proc = await asyncio.create_subprocess_exec(
                "k6", "scale", "--vus", str(target_vus),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = await scale_proc.communicate()
            
            if scale_proc.returncode == 0:
                self.current_vus_internal = target_vus
                on_log(f"[bold cyan]🔼 VUs number is changed to: {target_vus} VUs[/bold cyan]\n")
                return True
            else:
                err_text = stderr.decode()
                on_log(f"[bold red]❌ Scaling error: {err_text}[/bold red]\n")
                return False
        except Exception as e:
            on_log(f"[bold red]💥 Error of connection to k6: {str(e)}[/bold red]\n")
            return False
