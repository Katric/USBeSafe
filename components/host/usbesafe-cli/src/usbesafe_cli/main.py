"""
USBeSafe CLI - Central orchestrator for secure USB device handling

This CLI manages the complete lifecycle of USB device scanning and virtualization,
coordinating between the daemon, VM, scanner, and virtual USB components.
"""

import click
import sys

from .commands import cli


def main():
    """Main entry point for USBeSafe CLI"""
    try:
        cli(obj={})
    except KeyboardInterrupt:
        click.echo("\nOperation cancelled by user", err=True)
        sys.exit(130)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

