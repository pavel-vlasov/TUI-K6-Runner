def format_error_categories_table(categories: dict[str, int]) -> str:
    rows = sorted(categories.items(), key=lambda pair: (-pair[1], pair[0]))
    if not rows:
        rows = [("-", 0)]

    max_name = max(len("Category"), *(len(name) for name, _ in rows))
    max_count = max(len("Count"), *(len(str(count)) for _, count in rows))

    border = f"┌{'─' * (max_name + 2)}┬{'─' * (max_count + 2)}┐"
    header = f"│ {'Category'.ljust(max_name)} │ {'Count'.rjust(max_count)} │"
    separator = f"├{'─' * (max_name + 2)}┼{'─' * (max_count + 2)}┤"
    body = [f"│ {name.ljust(max_name)} │ {str(count).rjust(max_count)} │" for name, count in rows]
    footer = f"└{'─' * (max_name + 2)}┴{'─' * (max_count + 2)}┘"

    return "\n".join([border, header, separator, *body, footer])


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
