"""
CLI command definitions for USBeSafe
"""

import click
import sys

from .daemon import DaemonManager


@click.group()
@click.version_option(version="0.1.0")
@click.pass_context
def cli(ctx):
    """
    USBeSafe - Secure USB device handling with automated malware scanning
    
    Central orchestrator for VM lifecycle, USB detection, malware scanning,
    and controlled file transfer via virtual USB.
    """
    ctx.ensure_object(dict)
    ctx.obj['daemon'] = DaemonManager()

@cli.command()
def hello():
    """Simple test command to verify CLI is working"""
    click.echo("Hello from USBeSafe CLI!")

@cli.command()
@click.pass_context
def start(ctx):
    """Start USBeSafe services"""
    daemon_mgr = ctx.obj['daemon']
    
    if not daemon_mgr.start():
        click.echo("✗ Failed to start daemon", err=True)
        sys.exit(1)
    
    click.echo("✓ USBeSafe services started successfully") 
