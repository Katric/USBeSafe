# USBeSafe CLI

Central orchestrator for secure USB device handling with automated malware scanning.

## Installation

```bash
# Install with uv
uv pip install -e .

# Or with pip
pip install -e .
```

## Usage

### Daemon Management

```bash
# Start the background daemon
usbesafe daemon start

# Stop the daemon
usbesafe daemon stop

# Check daemon status
usbesafe daemon status
```

### USB Device Management

```bash
# List all attached USB devices
usbesafe list-devices

# List devices in JSON format
usbesafe list-devices --json

# Monitor for USB device insertion events
usbesafe watch-devices
```

### Malware Scanning

```bash
# Scan specific paths
usbesafe scan /path/to/device

# Scan in batch mode (non-interactive)
usbesafe scan /path/to/device --batch

# Generate JSON report
usbesafe scan /path/to/device --report-format json
```

### File Transfer

```bash
# Transfer files to virtual USB
usbesafe transfer file1.txt file2.pdf

# Auto-approve all clean files
usbesafe transfer file1.txt --auto-approve
```

### Virtual Machine Management

```bash
# Start the VM
usbesafe vm start

# Start VM with custom image
usbesafe vm start --image /path/to/image.qcow2

# Stop the VM
usbesafe vm stop

# Restart VM with clean base image
usbesafe vm restart

# Destroy VM and cleanup
usbesafe vm destroy

# Check VM status
usbesafe vm status
```

### Configuration

```bash
# Show current configuration
usbesafe config show

# Show config in JSON format
usbesafe config show --format json

# Edit configuration
usbesafe config edit

# Validate configuration
usbesafe config validate
```
