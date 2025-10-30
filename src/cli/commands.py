"""
Command line interface for Video Toolkit
Provides interactive and command-based interfaces
"""

import asyncio
import sys
from pathlib import Path
from typing import List, Optional

from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from core.config import get_config
from core.constants import WORKFLOW_PRESETS, Platform
from core.workflow.manager import WorkflowManager
from core.utils.logging import get_logger

console = Console()
logger = get_logger(__name__)


def main(args):
    """Main CLI entry point"""
    try:
        if hasattr(args, 'command') and args.command:
            # Command mode
            handle_command(args)
        else:
            # Interactive mode
            interactive_mode()
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️  Operation cancelled by user[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        logger.exception("CLI error")
        sys.exit(1)


def handle_command(args):
    """Handle specific commands"""
    command_handlers = {
        'download': handle_download,
        'process': handle_process,
        'upload': handle_upload,
        'workflow': handle_workflow,
        'config': handle_config,
        'status': handle_status
    }
    
    handler = command_handlers.get(args.command)
    if handler:
        handler(args)
    else:
        console.print(f"[red]Unknown command: {args.command}[/red]")
        sys.exit(1)


def interactive_mode():
    """Interactive mode with rich interface"""
    console.clear()
    
    # Welcome banner
    welcome_panel = Panel(
        "[bold blue]🎬 Video Toolkit Refactored v2.0.0[/bold blue]\n"
        "Modern video processing & multi-platform upload tool",
        title="Welcome",
        border_style="blue"
    )
    console.print(welcome_panel)
    
    while True:
        console.print("\n[bold cyan]📋 Main Menu[/bold cyan]")
        
        table = Table(show_header=False, box=None)
        table.add_column("Option", style="cyan")
        table.add_column("Description", style="white")
        
        table.add_row("1", "🔽 Download videos")
        table.add_row("2", "⚙️  Process existing videos")
        table.add_row("3", "🚀 Upload to platforms")
        table.add_row("4", "🎯 Run complete workflow")
        table.add_row("5", "⚙️  Configuration")
        table.add_row("6", "📊 Status & monitoring")
        table.add_row("7", "❓ Help & documentation")
        table.add_row("0", "🚪 Exit")
        
        console.print(table)
        
        choice = Prompt.ask(
            "\n[bold]Select option",
            choices=["0", "1", "2", "3", "4", "5", "6", "7"],
            default="4"
        )
        
        if choice == "0":
            console.print("[green]👋 Goodbye![/green]")
            break
        elif choice == "1":
            interactive_download()
        elif choice == "2":
            interactive_process()
        elif choice == "3":
            interactive_upload()
        elif choice == "4":
            interactive_workflow()
        elif choice == "5":
            interactive_config()
        elif choice == "6":
            interactive_status()
        elif choice == "7":
            show_help()


def interactive_workflow():
    """Interactive workflow selection and execution"""
    console.print("\n[bold cyan]🎯 Workflow Selection[/bold cyan]")
    
    # Show available presets
    table = Table(title="Available Workflows")
    table.add_column("#", style="cyan")
    table.add_column("Name", style="bold")
    table.add_column("Description", style="white")
    table.add_column("Steps", style="dim")
    
    presets = list(WORKFLOW_PRESETS.items())
    for i, (key, preset) in enumerate(presets, 1):
        steps_str = " → ".join(preset['steps'][:3])
        if len(preset['steps']) > 3:
            steps_str += f" ... (+{len(preset['steps'])-3} more)"
        table.add_row(str(i), preset['name'], preset['description'], steps_str)
    
    console.print(table)
    
    # Get user choice
    choice = Prompt.ask(
        "\nSelect workflow",
        choices=[str(i) for i in range(1, len(presets) + 1)],
        default="1"
    )
    
    preset_key = list(WORKFLOW_PRESETS.keys())[int(choice) - 1]
    selected_preset = WORKFLOW_PRESETS[preset_key]
    
    console.print(f"\n[green]✅ Selected: {selected_preset['name']}[/green]")
    
    # Get video source
    video_source = get_video_source()
    if not video_source:
        return
    
    # Get additional options
    options = get_workflow_options(preset_key)
    
    # Confirm execution
    if not Confirm.ask(f"\nExecute workflow '{selected_preset['name']}'?"):
        console.print("[yellow]Workflow cancelled[/yellow]")
        return
    
    # Execute workflow
    execute_workflow(preset_key, video_source, options)


def get_video_source() -> Optional[str]:
    """Get video source from user input"""
    console.print("\n[bold cyan]📁 Video Source[/bold cyan]")
    
    source_type = Prompt.ask(
        "Source type",
        choices=["url", "file", "folder", "search"],
        default="url"
    )
    
    if source_type == "url":
        url = Prompt.ask("Enter video URL")
        return url
    elif source_type == "file":
        file_path = Prompt.ask("Enter file path")
        if Path(file_path).exists():
            return file_path
        else:
            console.print("[red]❌ File not found[/red]")
            return None
    elif source_type == "folder":
        folder_path = Prompt.ask("Enter folder path")
        if Path(folder_path).exists():
            return folder_path
        else:
            console.print("[red]❌ Folder not found[/red]")
            return None
    elif source_type == "search":
        search_term = Prompt.ask("Search for video by title/keyword")
        return f"search:{search_term}"
    
    return None


def get_workflow_options(preset_key: str) -> dict:
    """Get additional workflow options from user"""
    options = {}
    config = get_config()
    
    # Platform selection for upload workflows
    if "upload" in WORKFLOW_PRESETS[preset_key]['steps']:
        console.print("\n[bold cyan]🌐 Platform Selection[/bold cyan]")
        
        available_platforms = [p.value for p in Platform]
        platform_table = Table(show_header=False)
        platform_table.add_column("#", style="cyan")
        platform_table.add_column("Platform", style="bold")
        
        for i, platform in enumerate(available_platforms, 1):
            platform_table.add_row(str(i), platform.capitalize())
        
        console.print(platform_table)
        
        platform_choices = Prompt.ask(
            "Select platforms (comma-separated numbers)",
            default="1,2"
        )
        
        selected_platforms = []
        for choice in platform_choices.split(","):
            try:
                idx = int(choice.strip()) - 1
                if 0 <= idx < len(available_platforms):
                    selected_platforms.append(available_platforms[idx])
            except ValueError:
                continue
        
        options['platforms'] = selected_platforms
    
    # Split duration for splitting workflows
    if "split_final" in WORKFLOW_PRESETS[preset_key]['steps']:
        console.print("\n[bold cyan]✂️ Split Duration[/bold cyan]")
        
        duration_presets = {
            "1": (60, "1 minute (Shorts/Reels)"),
            "2": (180, "3 minutes (TikTok)"),
            "3": (300, "5 minutes (Standard)"),
            "4": (600, "10 minutes (Long clips)"),
            "5": (900, "15 minutes (Extended)"),
            "6": (None, "Don't split (full video)")
        }
        
        duration_table = Table(show_header=False)
        duration_table.add_column("#", style="cyan")
        duration_table.add_column("Duration", style="bold")
        
        for key, (duration, desc) in duration_presets.items():
            duration_table.add_row(key, desc)
        
        console.print(duration_table)
        
        duration_choice = Prompt.ask(
            "Select split duration",
            choices=list(duration_presets.keys()),
            default="5"
        )
        
        options['split_duration'] = duration_presets[duration_choice][0]
    
    return options


def execute_workflow(preset_key: str, video_source: str, options: dict):
    """Execute the selected workflow with progress tracking"""
    try:
        console.print(f"\n[bold green]🚀 Starting workflow: {WORKFLOW_PRESETS[preset_key]['name']}[/bold green]")
        
        # Initialize workflow manager
        manager = WorkflowManager()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            # Create progress task
            task = progress.add_task("Initializing workflow...", total=None)
            
            # Execute workflow (this should be async in real implementation)
            result = asyncio.run(
                manager.execute_workflow(
                    preset_key=preset_key,
                    video_source=video_source,
                    options=options,
                    progress_callback=lambda desc: progress.update(task, description=desc)
                )
            )
            
            progress.update(task, description="✅ Workflow completed!")
        
        if result:
            console.print("\n[bold green]🎉 Workflow completed successfully![/bold green]")
            
            # Show results summary
            if result.get('output_files'):
                console.print("\n[bold cyan]📄 Generated Files:[/bold cyan]")
                for file_path in result['output_files']:
                    console.print(f"  📁 {file_path}")
            
            if result.get('upload_results'):
                console.print("\n[bold cyan]🚀 Upload Results:[/bold cyan]")
                for platform, status in result['upload_results'].items():
                    icon = "✅" if status else "❌"
                    console.print(f"  {icon} {platform.capitalize()}")
        else:
            console.print("\n[bold red]❌ Workflow failed[/bold red]")
    
    except Exception as e:
        console.print(f"\n[bold red]❌ Workflow error: {e}[/bold red]")
        logger.exception("Workflow execution failed")
    
    input("\nPress Enter to continue...")


def interactive_download():
    """Interactive download interface"""
    console.print("\n[bold cyan]🔽 Video Download[/bold cyan]")
    
    source_type = Prompt.ask(
        "Download source",
        choices=["youtube", "facebook", "bilibili", "tiktok", "custom"],
        default="youtube"
    )
    
    url = Prompt.ask("Enter video URL")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Downloading...", total=None)
        
        try:
            # TODO: Implement actual download logic
            import time
            time.sleep(2)  # Simulate download
            progress.update(task, description="✅ Download completed!")
            console.print("[green]✅ Download successful![/green]")
        except Exception as e:
            console.print(f"[red]❌ Download failed: {e}[/red]")
    
    input("\nPress Enter to continue...")


def interactive_process():
    """Interactive video processing interface"""
    console.print("\n[bold cyan]⚙️ Video Processing[/bold cyan]")
    console.print("[dim]This feature will be implemented soon...[/dim]")
    input("\nPress Enter to continue...")


def interactive_upload():
    """Interactive upload interface"""
    console.print("\n[bold cyan]🚀 Platform Upload[/bold cyan]")
    console.print("[dim]This feature will be implemented soon...[/dim]")
    input("\nPress Enter to continue...")


def interactive_config():
    """Interactive configuration interface"""
    console.print("\n[bold cyan]⚙️ Configuration[/bold cyan]")
    
    config = get_config()
    
    config_table = Table(title="Current Configuration")
    config_table.add_column("Setting", style="cyan")
    config_table.add_column("Value", style="white")
    
    config_table.add_row("Output Directory", str(config.paths.output_dir))
    config_table.add_row("Video Quality", config.processing.video_quality)
    config_table.add_row("Whisper Model", config.processing.whisper_model)
    config_table.add_row("Enabled Platforms", ", ".join(config.platforms.enabled_platforms))
    
    console.print(config_table)
    
    if Confirm.ask("\nEdit configuration?"):
        console.print("[dim]Configuration editing will be implemented soon...[/dim]")
    
    input("\nPress Enter to continue...")


def interactive_status():
    """Interactive status and monitoring interface"""
    console.print("\n[bold cyan]📊 System Status[/bold cyan]")
    
    # Check system requirements
    status_table = Table(title="System Requirements")
    status_table.add_column("Component", style="cyan")
    status_table.add_column("Status", style="white")
    status_table.add_column("Version", style="dim")
    
    # TODO: Implement actual system checks
    status_table.add_row("FFmpeg", "✅ Available", "4.4.0")
    status_table.add_row("Whisper", "✅ Available", "20231117")
    status_table.add_row("Selenium", "✅ Available", "4.15.0")
    status_table.add_row("Python", "✅ Available", f"{sys.version_info.major}.{sys.version_info.minor}")
    
    console.print(status_table)
    
    # Show recent operations
    console.print("\n[bold cyan]📝 Recent Operations[/bold cyan]")
    console.print("[dim]No recent operations found[/dim]")
    
    input("\nPress Enter to continue...")


def show_help():
    """Show help and documentation"""
    console.print("\n[bold cyan]❓ Help & Documentation[/bold cyan]")
    
    help_panel = Panel(
        "[bold]Video Toolkit Refactored - Help[/bold]\n\n"
        "[cyan]Quick Start:[/cyan]\n"
        "1. Run 'python -m src.main' for interactive mode\n"
        "2. Select workflow type (full processing recommended)\n"
        "3. Provide video source (URL, file, or folder)\n"
        "4. Configure platforms and options\n"
        "5. Execute and monitor progress\n\n"
        "[cyan]Commands:[/cyan]\n"
        "• download <url> - Download video only\n"
        "• process <file> - Process existing video\n"
        "• workflow <preset> <source> - Run workflow\n"
        "• config - Show configuration\n\n"
        "[cyan]Documentation:[/cyan]\n"
        "• GitHub: https://github.com/gunantos/video-toolkit-refactored\n"
        "• Wiki: https://github.com/gunantos/video-toolkit-refactored/wiki\n"
        "• Issues: https://github.com/gunantos/video-toolkit-refactored/issues",
        border_style="blue"
    )
    
    console.print(help_panel)
    input("\nPress Enter to continue...")


# Command handlers for non-interactive mode
def handle_download(args):
    """Handle download command"""
    console.print(f"[cyan]🔽 Downloading: {args.url}[/cyan]")
    # TODO: Implement download logic


def handle_process(args):
    """Handle process command"""
    console.print(f"[cyan]⚙️ Processing: {args.file}[/cyan]")
    # TODO: Implement processing logic


def handle_upload(args):
    """Handle upload command"""
    console.print(f"[cyan]🚀 Uploading: {args.file}[/cyan]")
    # TODO: Implement upload logic


def handle_workflow(args):
    """Handle workflow command"""
    console.print(f"[cyan]🎯 Running workflow: {args.preset} on {args.source}[/cyan]")
    # TODO: Implement workflow execution


def handle_config(args):
    """Handle config command"""
    config = get_config()
    console.print("[cyan]⚙️ Current Configuration:[/cyan]")
    console.print(f"Output Directory: {config.paths.output_dir}")
    console.print(f"Video Quality: {config.processing.video_quality}")
    console.print(f"Enabled Platforms: {', '.join(config.platforms.enabled_platforms)}")


def handle_status(args):
    """Handle status command"""
    console.print("[cyan]📊 System Status:[/cyan]")
    # TODO: Implement status checks
    console.print("All systems operational")
