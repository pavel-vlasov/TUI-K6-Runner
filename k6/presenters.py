def format_error_categories_table(categories: dict[str, int]) -> str:
    if not categories:
        return "errors: -"

    preferred_order = ["4xx", "500", "5xx (not 500)", "EOF"]
    ordered_keys = [key for key in preferred_order if key in categories]
    ordered_keys.extend(sorted(key for key in categories if key not in preferred_order))

    parts = [f"{key}: {categories[key]}" for key in ordered_keys]
    return "errors: " + "  |  ".join(parts)


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
