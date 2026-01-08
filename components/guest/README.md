## VM Component Overview (Already Implemented)

The VM already contains all core components required for installation, virus scanning, and daemon management. Their responsibilities and interactions are structured as follows:

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

### 4 `usbesafed-vm/src/usbesafed-vm.init`
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

### 5 `placeholder/placeholder/`
**Purpose:**

**Responsibilities:**

**Role in the workflow:**

**VM Path:**
- /opt/scanner/placeholder.py

---

## Logical Execution Flow

1. **Bootstrap:** `install.sh` prepares the VM (packages, autologin).
2. **Service Management:** `usbesafed-vm.init` enables OpenRC to manage the daemon lifecycle.
3. **Runtime:** `usbesafed-vm.sh` runs as a persistent daemon and waits for scan requests.
4. Placeholder
5. **Scan Execution:** `scanner.py` performs the actual virus scanning and returns results.
