def format_running_status(last_counter: str, status_running: str, status_default: str) -> str:
    return (
        f"[bold]📊 {last_counter}[/bold]\n"
        f"[bold]🔄 {status_running}[/bold]\n"
        f"[bold]📈 {status_default}[/bold]"
    )


def format_done_status(last_counter: str) -> str:
    return f"[bold green]✅ Done. [/bold green]\n[bold]{last_counter}[/bold]"


def format_start_status() -> str:
    return "[bold yellow]🚀 Preparing test execution...[/bold yellow]"


def format_start_log() -> str:
    return "[bold cyan]Starting k6 test in UI...[/bold cyan]\n"
