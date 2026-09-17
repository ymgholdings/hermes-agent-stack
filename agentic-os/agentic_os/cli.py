"""CLI interface for Agentic OS."""

import sys
import time
from datetime import datetime

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from .config import config
from .db import SessionLocal, Task, init_db
from .executor import executor
from .orchestrator import orchestrator

console = Console()


@click.group()
def cli():
    """Agentic OS - Multi-agent coding orchestration system."""
    pass


@cli.command()
@click.argument("spec", required=True)
def submit(spec: str):
    """Submit a coding task for execution.

    Example:
        agentic-os submit "write a fibonacci function with unit tests"
    """
    # Verify Docker is available
    if not executor.verify_docker_available():
        console.print("[red]Error: Docker is not available or not running.[/red]")
        console.print("Please ensure Docker is installed and running.")
        sys.exit(1)

    # Initialize database if needed
    try:
        init_db()
    except Exception as e:
        console.print(f"[red]Database initialization failed: {e}[/red]")
        sys.exit(1)

    # Create task in database
    db = SessionLocal()
    task = Task(spec=spec, status="pending")
    db.add(task)
    db.commit()
    task_id = task.id
    db.close()

    # Display header
    console.print(Panel.fit(
        f"🤖 Agentic OS v1 — Task #{task_id}",
        border_style="blue"
    ))
    console.print(f"\n📝 Spec: [cyan]{spec}[/cyan]\n")

    # Phase 1: Decomposing
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task_progress = progress.add_task("[yellow]Decomposing task...", total=None)

        start = time.time()

        try:
            result = orchestrator.run_task(spec, task_id)
            elapsed = time.time() - start

        except Exception as e:
            progress.stop()
            console.print(f"\n[red]✗ Task failed: {e}[/red]")
            sys.exit(1)

        progress.stop()

    # Display results
    if result.success:
        console.print(f"[green]✓[/green] Task completed in {elapsed:.1f}s ({result.iterations} iteration(s))\n")

        console.print("[bold]Final Code:[/bold]")
        console.print(Panel(
            result.code,
            title="solution.py",
            border_style="green",
        ))

        console.print("\n[bold]Test Output:[/bold]")
        console.print(result.test_output)

        console.print(f"\n[green]✅ All tests passed![/green]")
        console.print(f"View full details: [cyan]agentic-os show {task_id}[/cyan]")

    else:
        console.print(f"[red]✗[/red] Task failed after {result.iterations} iteration(s)\n")

        if result.error_trace:
            console.print("[bold]Error Trace:[/bold]")
            console.print(Panel(
                result.error_trace,
                border_style="red",
            ))

        if result.code:
            console.print("\n[bold]Last Generated Code:[/bold]")
            console.print(Panel(
                result.code,
                title="solution.py (incomplete)",
                border_style="yellow",
            ))

        console.print(f"\n[yellow]View full details: agentic-os show {task_id}[/yellow]")
        sys.exit(1)


@cli.command()
@click.option("--limit", default=10, help="Number of recent tasks to show")
def list(limit: int):
    """List recent tasks.

    Example:
        agentic-os list
        agentic-os list --limit 20
    """
    db = SessionLocal()
    tasks = db.query(Task).order_by(Task.created_at.desc()).limit(limit).all()
    db.close()

    if not tasks:
        console.print("[yellow]No tasks found.[/yellow]")
        return

    table = Table(title=f"Recent Tasks (limit: {limit})")
    table.add_column("ID", style="cyan", width=6)
    table.add_column("Status", width=12)
    table.add_column("Iterations", width=10)
    table.add_column("Spec", style="white")
    table.add_column("Created", style="dim")

    for task in tasks:
        status_color = {
            "completed": "green",
            "failed": "red",
            "pending": "yellow",
            "implemented": "blue",
            "reviewed": "blue",
        }.get(task.status, "white")

        table.add_row(
            str(task.id),
            f"[{status_color}]{task.status}[/{status_color}]",
            str(task.iteration_count),
            task.spec[:60] + "..." if len(task.spec) > 60 else task.spec,
            task.created_at.strftime("%Y-%m-%d %H:%M"),
        )

    console.print(table)


@cli.command()
@click.argument("task_id", type=int)
def show(task_id: int):
    """Show detailed information about a task.

    Example:
        agentic-os show 1
    """
    db = SessionLocal()
    task = db.query(Task).filter(Task.id == task_id).first()
    db.close()

    if not task:
        console.print(f"[red]Task #{task_id} not found.[/red]")
        sys.exit(1)

    console.print(Panel.fit(f"Task #{task.id} Details", border_style="blue"))

    console.print(f"\n[bold]Spec:[/bold] {task.spec}")
    console.print(f"[bold]Status:[/bold] {task.status}")
    console.print(f"[bold]Iterations:[/bold] {task.iteration_count}")
    console.print(f"[bold]Created:[/bold] {task.created_at}")

    if task.code:
        console.print("\n[bold]Code:[/bold]")
        console.print(Panel(task.code, border_style="green"))

    if task.test_output:
        console.print("\n[bold]Test Output:[/bold]")
        console.print(task.test_output)

    if task.error_trace:
        console.print("\n[bold]Error Trace:[/bold]")
        console.print(Panel(task.error_trace, border_style="red"))


@cli.command()
def test_connections():
    """Test connections to OpenRouter, Postgres, and Redis.

    Example:
        agentic-os test-connections
    """
    console.print("[bold]Testing infrastructure connections...[/bold]\n")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("[yellow]Testing...", total=None)
        success = config.test_connections()
        progress.stop()

    if success:
        console.print("[green]✓ All connections successful![/green]")
    else:
        console.print("[red]✗ Some connections failed. Check error messages above.[/red]")
        sys.exit(1)


if __name__ == "__main__":
    cli()
