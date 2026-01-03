"""
Daemon management for USBeSafe background service
"""

import sys
import subprocess
from pathlib import Path
import click


class DaemonManager:
    """Manages the USBeSafe background daemon"""
    
    def __init__(self):
        self.pid_file = "tbd"
        self.log_file = "tbd"
        # Path to the usbesafed daemon script
        self.daemon_script = Path("/home/devbox/securepass/components/host/usbesafed/src/host_daemon.py")

    def start(self) -> bool:
        """
        Start the background daemon
        """

        click.echo("Starting USBeSafe daemon...")
        
        if not self.daemon_script.exists():
            click.echo(f"Error: Daemon script not found at {self.daemon_script}", err=True)
            return False
        
        try:
            # Run the daemon script directly
            subprocess.run([sys.executable, str(self.daemon_script)], check=True)
            return True
        except subprocess.CalledProcessError as e:
            click.echo(f"Error starting daemon: {e}", err=True)
            return False
