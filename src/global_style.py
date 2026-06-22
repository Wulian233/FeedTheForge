from rich.console import Console

console = Console()


def focused(text):
    return f"[cyan]{text}[/cyan]"


def success(text):
    console.print(f"[green]{text}[/green]")


def error(text):
    console.print(f"[red]{text}[/red]")


def warn(text):
    console.print(f"[yellow]{text}[/yellow]")
