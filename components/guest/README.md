## VM Component Overview (Already Implemented)

The VM already contains all core components required for installation, virus & bad usb scanning, and daemon management.
Their responsibilities and interactions are structured as follows:

---

### 1 `init-script/install.sh`

**Purpose:** Initial setup script for the VM.

**Responsibilities:**

- installs all **required packages and dependencies**
- configures and enables **autologin**, allowing the VM to boot without manual interaction

**Role in the workflow:**

- executed **first** to bootstrap the VM and prepare it for daemon-based operation

**VM Path:**

- /usr/local/sbin/securepass-init.sh

---

### 2 `scanner/scanner.py`

**Purpose:** Implements the **virus scanning logic**.

**Responsibilities:**

- contains the core **scan pipeline** (e.g. invoking the scanner, evaluating results)
- encapsulates all scanner-specific functionality used by the daemon

**Role in the workflow:**

- called by the daemon whenever a scan operation is requested

**VM Path:**

- /opt/scanner/scanner.py

---

### 3 `usbesafed-vm/src/usbesafed-vm.sh`

**Purpose:** The **main VM daemon** (runtime component).

**Responsibilities:**

- runs continuously inside the VM
- processes incoming requests (e.g. start scan, report status, return results)
- invokes the scanner logic (`scanner.py`) to perform scans

**Role in the workflow:**

- acts as the central orchestration and communication layer within the VM

**VM Path:**
/usr/local/bin/usbesafed-vm.sh

---

### 4 `usbesafed-vm/src/usbesafed-vm`

**Purpose:** **OpenRC init script** for daemon management.

**Responsibilities:**

- integrates `usbesafed-vm.sh` into OpenRC
- defines start/stop/restart behavior
- ensures the daemon is started automatically during system boot

**Role in the workflow:**

- provides the service wrapper that allows the daemon to run as a managed system service

**VM Path:**
/etc/init.d/usbesafed-vm

---

### 5 `usbesafed-vm/src/badusb/bad_usb_check.py`

**Purpose:** Perform BadUSB checks on the VM

**Responsibilities:**

- Detect USB HID Devices with Keyboard Capabilities
- Detect BadUSB devices which send malicious input

**Role in the workflow:**

- called by orchestrator.py on the VM if USB device inside the VM has keyboard input capabilities

**VM Path:**

- /opt/scanner/bad_usb_check.py

---

### 6 `usbesafed-vm/src/orchestrator.py`

**Purpose:** Detect USB Devices on the VM that have to be scanned and trigger necessary checks

**Responsibilities:**

- Find the USB device that has to be scanned
- if usb-hid driver is loaded -> perform BadUSB checks
- if usb-storage driver is loaded -> execute malware scan

**Role in the workflow:**

- Orchestrate workflow on VM, depending on device type. Called from main shell script.

**VM Path:**

- /opt/scanner/orchestrator.py

---

### 4 `usbesafed-vm/src/orchestrator-vm`

**Purpose:** **OpenRC file** to run orchestrator.py once.

**Responsibilities:**

- run orchestrator.py once

**Role in the workflow:**

- provides the entry point to find the device that has to be scanned and initiate scans by its loaded drivers

**VM Path:**
/etc/init.d/orchestrator-vm




---

## Logical Execution Flow

1. **Bootstrap:** `install.sh` prepares the VM (packages, autologin).
2. **Service Management:** `usbesafed-vm` enables OpenRC to manage the daemon lifecycle.
3. **Runtime:** `usbesafed-vm.sh` runs as a persistent daemon and waits for virus scan requests.
4. **Orchestration:** `orchestrator-vm` finds the device that has to be scanned and initiates scans depending on drivers
   loaded
5. **BadUSB-Checks:** `orchestrator.py` runs BadUSB checks if "usbhid" drivers are loaded by the USB device to be
   scanned and returns results
6. **Mounting of USB:** `orchestrator.py` mounts the USB if usb-storage driver is loaded, which then triggers the
   usbesafed-vm to run virus scans and manage the vUSB
7. **Scan Execution:** `scanner.py` performs the actual virus scanning and returns results.
