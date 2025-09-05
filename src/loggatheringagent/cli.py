#!/usr/bin/env python3
"""
Command-line interface for the Windows Log Gathering Agent.
"""

import asyncio
import json
from pathlib import Path
from typing import List, Optional
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm, Prompt
from rich import print as rprint

from .config.settings import Settings
from .core.log_collector import WindowsLogCollector
from .core.llm_analyzer import WindowsLogAnalyzer

# Initialize CLI
app = typer.Typer(
    name="loggatheringagent",
    help="Windows Log Gathering Agent - Centralized log analysis for deployment troubleshooting",
    add_completion=False
)
console = Console()

# Global settings
settings = Settings()


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", "--host", help="API server host"),
    port: int = typer.Option(8000, "--port", help="API server port"),
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload for development")
):
    """Start the FastAPI server."""
    import uvicorn
    from .api.main import app as fastapi_app
    
    console.print(f"🚀 Starting Windows Log Gathering Agent server on {host}:{port}")
    console.print(f"📊 Web interface: http://{host}:{port}")
    console.print(f"📖 API docs: http://{host}:{port}/docs")
    
    uvicorn.run(
        "loggatheringagent.api.main:app",
        host=host,
        port=port,
        reload=reload
    )


@app.command()
def list_clients():
    """List all configured client machines."""
    try:
        machines_config = settings.load_machines_config()
        
        table = Table(title="Configured Clients")
        table.add_column("Name", style="cyan")
        table.add_column("Hostname", style="green")
        table.add_column("IP", style="blue")
        table.add_column("Credentials", style="yellow")
        table.add_column("Log Sources", style="magenta")
        
        for client in machines_config.clients:
            log_count = sum(len(paths) for paths in client.log_paths.values())
            log_count += len(client.powershell_commands)
            
            table.add_row(
                client.name,
                client.hostname,
                client.ip,
                client.credentials,
                str(log_count)
            )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"❌ Error loading client configuration: {e}", style="red")
        raise typer.Exit(1)


@app.command()
def analyze(
    clients: Optional[List[str]] = typer.Argument(None, help="Client names to analyze (default: all)"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file (JSON)"),
    summary: bool = typer.Option(True, "--summary/--no-summary", help="Include summary"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output")
):
    """Analyze logs from specified clients."""
    
    async def run_analysis():
        try:
            # Load configuration
            machines_config = settings.load_machines_config()
            
            # Determine which clients to analyze
            if clients:
                # Validate client names
                available_clients = {client.name for client in machines_config.clients}
                invalid_clients = set(clients) - available_clients
                if invalid_clients:
                    console.print(f"❌ Unknown clients: {', '.join(invalid_clients)}", style="red")
                    console.print(f"Available clients: {', '.join(available_clients)}")
                    raise typer.Exit(1)
                target_clients = clients
            else:
                target_clients = [client.name for client in machines_config.clients]
            
            if not target_clients:
                console.print("❌ No clients to analyze", style="red")
                raise typer.Exit(1)
            
            console.print(f"🔍 Starting analysis for {len(target_clients)} clients...")
            
            # Initialize components
            log_collector = WindowsLogCollector(settings)
            log_analyzer = WindowsLogAnalyzer(settings)
            
            # Collect logs with progress indicator
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                collect_task = progress.add_task("Collecting logs...", total=None)
                log_collections = await log_collector.collect_multiple_clients(target_clients)
                progress.update(collect_task, description="✅ Log collection completed")
            
            # Show collection results
            if verbose:
                for collection in log_collections:
                    status = "✅" if collection.success else "❌"
                    console.print(f"{status} {collection.client_name}: {len(collection.log_results)} log sources")
            
            # Analyze logs with progress indicator
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                analyze_task = progress.add_task("Analyzing logs with LLM...", total=None)
                analysis_results = await log_analyzer.analyze_multiple_clients(log_collections)
                progress.update(analyze_task, description="✅ Analysis completed")
            
            # Display results
            console.print("\n📋 Analysis Results:")
            
            for result in analysis_results:
                # Status indicator
                if result.overall_status == "healthy":
                    status_icon = "🟢"
                    status_color = "green"
                elif result.overall_status == "issues":
                    status_icon = "🟡"
                    status_color = "yellow"
                else:  # critical
                    status_icon = "🔴"
                    status_color = "red"
                
                # Create panel for each client
                panel_content = f"""
**Status**: {status_icon} {result.overall_status.upper()}
**Summary**: {result.summary}
**Action Items**: {len(result.action_items)} recommendations
**Logs Analyzed**: {len(result.log_analyses)} sources
                """.strip()
                
                if verbose:
                    panel_content += f"\n**Top Actions**:\n"
                    for i, action in enumerate(result.action_items[:3], 1):
                        panel_content += f"  {i}. {action}\n"
                
                console.print(Panel(
                    panel_content,
                    title=f"{result.client_name} ({result.hostname})",
                    border_style=status_color
                ))
            
            # Generate summary
            if summary:
                total_clients = len(analysis_results)
                healthy = len([r for r in analysis_results if r.overall_status == "healthy"])
                issues = len([r for r in analysis_results if r.overall_status == "issues"])
                critical = len([r for r in analysis_results if r.overall_status == "critical"])
                
                summary_panel = f"""
**Total Clients Analyzed**: {total_clients}
🟢 **Healthy**: {healthy}
🟡 **Issues**: {issues}  
🔴 **Critical**: {critical}
                """.strip()
                
                console.print(Panel(
                    summary_panel,
                    title="📊 Analysis Summary",
                    border_style="blue"
                ))
            
            # Save to file if requested
            if output:
                output_data = {
                    "timestamp": analysis_results[0].timestamp.isoformat(),
                    "clients_analyzed": target_clients,
                    "results": [
                        {
                            "client_name": r.client_name,
                            "hostname": r.hostname,
                            "overall_status": r.overall_status,
                            "summary": r.summary,
                            "action_items": r.action_items,
                            "log_analyses": [
                                {
                                    "source": la.source,
                                    "analysis": la.analysis,
                                    "issues_found": la.issues_found,
                                    "recommendations": la.recommendations,
                                    "severity": la.severity,
                                    "confidence": la.confidence
                                }
                                for la in r.log_analyses
                            ]
                        }
                        for r in analysis_results
                    ]
                }
                
                with open(output, 'w', encoding='utf-8') as f:
                    json.dump(output_data, f, indent=2, ensure_ascii=False, default=str)
                
                console.print(f"💾 Results saved to: {output}")
            
        except KeyboardInterrupt:
            console.print("\n⚠️ Analysis interrupted by user", style="yellow")
            raise typer.Exit(130)
        except Exception as e:
            console.print(f"❌ Analysis failed: {e}", style="red")
            if verbose:
                console.print_exception()
            raise typer.Exit(1)
    
    # Run async analysis
    asyncio.run(run_analysis())


@app.command()
def test_connection(
    client: str = typer.Argument(..., help="Client name to test"),
    test_smb: bool = typer.Option(True, "--smb/--no-smb", help="Test SMB connectivity"),
    test_powershell: bool = typer.Option(True, "--ps/--no-ps", help="Test PowerShell connectivity")
):
    """Test connectivity to a specific client."""
    
    async def run_test():
        try:
            machines_config = settings.load_machines_config()
            
            # Find client
            client_config = None
            for c in machines_config.clients:
                if c.name == client:
                    client_config = c
                    break
            
            if not client_config:
                console.print(f"❌ Client '{client}' not found in configuration", style="red")
                raise typer.Exit(1)
            
            cred_config = machines_config.credentials.get(client_config.credentials)
            if not cred_config:
                console.print(f"❌ Credentials '{client_config.credentials}' not found", style="red")
                raise typer.Exit(1)
            
            console.print(f"🔍 Testing connectivity to {client_config.name} ({client_config.hostname})")
            
            # Test SMB
            if test_smb:
                from .mcp_clients.smb_client import SMBMCPClient
                
                with console.status("Testing SMB connectivity..."):
                    try:
                        async with SMBMCPClient() as smb_client:
                            result = await smb_client.list_directory(
                                hostname=client_config.hostname,
                                username=cred_config.username,
                                password=cred_config.password,
                                dir_path="C$/Windows",
                                domain=cred_config.domain
                            )
                            
                            if result["success"]:
                                console.print("✅ SMB connection successful", style="green")
                            else:
                                console.print(f"❌ SMB connection failed: {result['error']}", style="red")
                                
                    except Exception as e:
                        console.print(f"❌ SMB test failed: {e}", style="red")
            
            # Test PowerShell
            if test_powershell:
                from .mcp_clients.powershell_client import PowerShellMCPClient
                
                with console.status("Testing PowerShell connectivity..."):
                    try:
                        async with PowerShellMCPClient() as ps_client:
                            result = await ps_client.execute_powershell(
                                hostname=client_config.hostname,
                                username=cred_config.username,
                                password=cred_config.password,
                                command="Write-Output 'Connection test successful'"
                            )
                            
                            if result["success"]:
                                console.print("✅ PowerShell connection successful", style="green")
                                if result["stdout"]:
                                    console.print(f"Response: {result['stdout'].strip()}")
                            else:
                                console.print(f"❌ PowerShell connection failed: {result['stderr']}", style="red")
                                
                    except Exception as e:
                        console.print(f"❌ PowerShell test failed: {e}", style="red")
            
        except Exception as e:
            console.print(f"❌ Test failed: {e}", style="red")
            raise typer.Exit(1)
    
    asyncio.run(run_test())


@app.command()
def config(
    show: bool = typer.Option(False, "--show", help="Show current configuration"),
    edit: bool = typer.Option(False, "--edit", help="Edit configuration file"),
    validate: bool = typer.Option(False, "--validate", help="Validate configuration")
):
    """Manage configuration."""
    
    if show or (not edit and not validate):
        try:
            machines_config = settings.load_machines_config()
            
            console.print("📋 Current Configuration:")
            console.print(f"Config file: {settings.config_file}")
            console.print(f"Clients: {len(machines_config.clients)}")
            console.print(f"Credential sets: {len(machines_config.credentials)}")
            console.print(f"LLM endpoint: {machines_config.llm_config.endpoint}")
            console.print(f"LLM model: {machines_config.llm_config.model}")
            
        except Exception as e:
            console.print(f"❌ Error loading configuration: {e}", style="red")
            raise typer.Exit(1)
    
    if validate:
        try:
            machines_config = settings.load_machines_config()
            console.print("✅ Configuration is valid", style="green")
        except Exception as e:
            console.print(f"❌ Configuration validation failed: {e}", style="red")
            raise typer.Exit(1)
    
    if edit:
        import subprocess
        import os
        
        config_path = Path(settings.config_file)
        if not config_path.exists():
            console.print(f"❌ Configuration file not found: {config_path}", style="red")
            raise typer.Exit(1)
        
        editor = os.environ.get("EDITOR", "notepad" if os.name == "nt" else "nano")
        try:
            subprocess.run([editor, str(config_path)], check=True)
            console.print("✅ Configuration file edited", style="green")
        except subprocess.CalledProcessError:
            console.print(f"❌ Failed to open editor: {editor}", style="red")
            raise typer.Exit(1)


def main():
    """Main entry point for CLI."""
    try:
        app()
    except KeyboardInterrupt:
        console.print("\n⚠️ Interrupted by user", style="yellow")
    except Exception as e:
        console.print(f"❌ Unexpected error: {e}", style="red")
        raise typer.Exit(1)


if __name__ == "__main__":
    main()