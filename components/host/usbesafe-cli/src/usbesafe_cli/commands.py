"""
CLI command definitions for USBeSafe
"""

import click
import json
import sys

from .config import Config
from .daemon import DaemonManager
from .usb import USBDeviceManager
from .vm import VMManager
from .scanner import ScannerCoordinator
from .virtual_usb import VirtualUSBManager


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
    ctx.obj['config'] = Config()
    ctx.obj['daemon'] = DaemonManager()
    ctx.obj['usb'] = USBDeviceManager()
    ctx.obj['vm'] = VMManager()
    ctx.obj['scanner'] = ScannerCoordinator()
    ctx.obj['vusb'] = VirtualUSBManager()


# ============================================================================
# Daemon Commands
# ============================================================================

@cli.group()
def daemon():
    """Manage the USBeSafe background daemon"""
    pass


@daemon.command()
@click.pass_context
def start(ctx):
    """Start the background daemon"""
    daemon_mgr = ctx.obj['daemon']
    if daemon_mgr.start():
        click.echo("✓ Daemon started successfully", err=False)
    else:
        click.echo("✗ Failed to start daemon", err=True)
        sys.exit(1)


@daemon.command()
@click.pass_context
def stop(ctx):
    """Stop the background daemon"""
    daemon_mgr = ctx.obj['daemon']
    if daemon_mgr.stop():
        click.echo("✓ Daemon stopped successfully", err=False)
    else:
        click.echo("✗ Failed to stop daemon", err=True)
        sys.exit(1)


@daemon.command()
@click.pass_context
def status(ctx):
    """Show daemon status"""
    daemon_mgr = ctx.obj['daemon']
    status_info = daemon_mgr.get_status()
    click.echo(json.dumps(status_info, indent=2))


# ============================================================================
# USB Device Commands
# ============================================================================

@cli.command()
@click.option('--json', 'output_json', is_flag=True, help='Output in JSON format')
@click.pass_context
def list_devices(ctx, output_json):
    """List all attached USB devices"""
    usb_mgr = ctx.obj['usb']
    devices = usb_mgr.list_devices()
    
    if output_json:
        click.echo(json.dumps(devices, indent=2))
    else:
        if not devices:
            click.echo("No USB devices found")
        else:
            for idx, device in enumerate(devices, 1):
                click.echo(f"{idx}. {device.get('name', 'Unknown')} - {device.get('path', 'N/A')}")


@cli.command()
@click.option('--json', 'output_json', is_flag=True, help='Output events in JSON format')
@click.pass_context
def watch_devices(ctx, output_json):
    """Monitor for USB device insertion events"""
    usb_mgr = ctx.obj['usb']
    
    def on_device_event(event):
        if output_json:
            click.echo(json.dumps(event))
        else:
            click.echo(f"Device {event.get('action', 'unknown')}: {event.get('path', 'N/A')}")
    
    try:
        usb_mgr.watch_devices(on_device_event)
    except KeyboardInterrupt:
        click.echo("\nStopped watching devices")


# ============================================================================
# Scanning Commands
# ============================================================================

@cli.command()
@click.argument('paths', nargs=-1, type=click.Path(exists=True))
@click.option('--batch', is_flag=True, help='Non-interactive batch mode')
@click.option('--report-format', type=click.Choice(['text', 'json', 'html']), default='text')
@click.pass_context
def scan(ctx, paths, batch, report_format):
    """Execute malware scan on specified paths"""
    scanner = ctx.obj['scanner']
    
    if not paths:
        click.echo("No paths specified for scanning", err=True)
        sys.exit(1)
    
    # Interactive file selection if not in batch mode
    interactive = not batch
    
    with click.progressbar(length=len(paths), label='Scanning files') as bar:
        results = scanner.scan(list(paths), interactive=interactive)
        bar.update(len(paths))
    
    report = scanner.generate_report(results, format=report_format)
    click.echo("\n" + report)


# ============================================================================
# Transfer Commands
# ============================================================================

@cli.command()
@click.argument('files', nargs=-1, type=click.Path(exists=True))
@click.option('--auto-approve', is_flag=True, help='Automatically approve all clean files')
@click.pass_context
def transfer(ctx, files, auto_approve):
    """Transfer approved files to virtual USB"""
    vusb_mgr = ctx.obj['vusb']
    
    if not files:
        click.echo("No files specified for transfer", err=True)
        sys.exit(1)
    
    # File approval workflow
    if not auto_approve:
        click.confirm(f"Transfer {len(files)} file(s) to virtual USB?", abort=True)
    
    if vusb_mgr.transfer_files(list(files)):
        click.echo("✓ Files transferred successfully")
        
        if click.confirm("Enable host access to virtual USB?", default=True):
            vusb_mgr.enable_host_access()
            click.echo("✓ Host access enabled")
    else:
        click.echo("✗ Transfer failed", err=True)
        sys.exit(1)


# ============================================================================
# VM Management Commands
# ============================================================================

@cli.group()
def vm():
    """Manage the virtual machine"""
    pass


@vm.command(name='start')
@click.option('--image', type=click.Path(exists=True), help='VM image path')
@click.pass_context
def start_vm(ctx, image):
    """Start the virtual machine"""
    vm_mgr = ctx.obj['vm']
    if vm_mgr.start(image):
        click.echo("✓ VM started successfully")
    else:
        click.echo("✗ Failed to start VM", err=True)
        sys.exit(1)


@vm.command(name='stop')
@click.pass_context
def stop_vm(ctx):
    """Stop the virtual machine"""
    vm_mgr = ctx.obj['vm']
    if vm_mgr.stop():
        click.echo("✓ VM stopped successfully")
    else:
        click.echo("✗ Failed to stop VM", err=True)
        sys.exit(1)


@vm.command(name='restart')
@click.pass_context
def restart_vm(ctx):
    """Restart VM with clean base image"""
    vm_mgr = ctx.obj['vm']
    if vm_mgr.restart():
        click.echo("✓ VM restarted with clean image")
    else:
        click.echo("✗ Failed to restart VM", err=True)
        sys.exit(1)


@vm.command(name='destroy')
@click.confirmation_option(prompt='This will destroy the VM and all data. Continue?')
@click.pass_context
def destroy_vm(ctx):
    """Destroy VM and cleanup all artifacts"""
    vm_mgr = ctx.obj['vm']
    if vm_mgr.destroy():
        click.echo("✓ VM destroyed and cleaned up")
    else:
        click.echo("✗ Failed to destroy VM", err=True)
        sys.exit(1)


@vm.command(name='status')
@click.pass_context
def vm_status(ctx):
    """Show VM status"""
    vm_mgr = ctx.obj['vm']
    status_info = vm_mgr.get_status()
    click.echo(json.dumps(status_info, indent=2))


# ============================================================================
# Configuration Commands
# ============================================================================

@cli.group()
def config():
    """Manage USBeSafe configuration"""
    pass


@config.command()
@click.option('--format', 'output_format', type=click.Choice(['yaml', 'json']), default='yaml')
@click.pass_context
def show(ctx, output_format):
    """Display current configuration"""
    cfg = ctx.obj['config']
    config_data = cfg.load()
    
    if output_format == 'json':
        click.echo(json.dumps(config_data, indent=2))
    else:
        # Format as YAML
        click.echo("Configuration:")
        click.echo(json.dumps(config_data, indent=2))


@config.command()
@click.option('--editor', envvar='EDITOR', default='nano', help='Text editor to use')
@click.pass_context
def edit(ctx, editor):
    """Edit configuration file"""
    cfg = ctx.obj['config']
    
    # TODO: Implement config editing with validation
    click.echo(f"Opening configuration in {editor}...")
    click.echo(f"Config file: {cfg.config_path}")


@config.command()
@click.pass_context
def validate(ctx):
    """Validate configuration file"""
    cfg = ctx.obj['config']
    
    if cfg.validate():
        click.echo("✓ Configuration is valid")
    else:
        click.echo("✗ Configuration validation failed", err=True)
        sys.exit(1)
