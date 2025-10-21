# SecurePass (Maybe USBeSafe? ;))

---

**Start date:** October 16, 2025  
**Planned end:** January 22, 2026  
**Responsible for updates:** All team members  

---

### Minimum requirements for the project:
- A functioning CLI tool that scans USB sticks for malware, displays a report in _Nautilus_, and mounts the stick on the host system afterwards

### SecurePass Workflow

1. Start the SecurePass app  
2. Insert the USB stick into the VM  
3. The file view opens automatically  
4. Automatic scan (traffic-light system to evaluate security)  
5. Flagging of compromised files  
6. Timer starts and automatic VM reset (user can abort)  
7. Files are verified as safe → a virtual USB can be inserted into the host system  

### Ideas:
- [ ] Shared Zotero group for literature? → unified `.bib` file  
- [ ] Final paper in Overleaf (requires Premium) or directly within the project?  

---

## Work Packages & Responsibilities

| Module / Task | Responsible |
|-----------------|--------------|
| **VM / Security environment** | Linus Rode |
| **Virtual USB stick** | Paul Ilitz |
| **CLI (VM start, USB script)** | Paul Ilitz |
| **Virus scan & traffic-light system** | Constantin Scheryer |
| **USB pass-through Host → VM (interface)** | Richard Kats, Tizian Everke |
| **GUI (automated file management)** | Aaron Debebe |

---

### 1. VM / Security Environment: Linus Rode



### 2. Virtual USB Stick: Paul Ilitz

The core concept behind the virtual USB stick is to create a secure intermediary storage space that can be accessed from both the host system and the virtual machine.  
This virtual device should operate with dynamic permission controls, starting in a read-only mode and transitioning to read-write access only after the scanned data has been verified as clean.

#### Workflow of the virtual USB-Stick

- When the VM is started by the CLI script, a virtual USB stick will be automatically created
- Initially, this virtual device will be mounted as read-only for both the host system and the VM
- The size of the virtual USB stick will be dynamically adjusted to match either the file size of the data on the physical USB stick or the total capacity of the USB stick itself
- Once the malware scanning process completes, the system will respond based on the scan results:
  - If all files are classified as green (safe) or yellow (potentially suspicious but not dangerous):
    - The virtual USB stick will be switched to read-write mode for the VM
    - The user will be presented with the option to select which files should be transferred to the host system, providing granular control over data flow
  - If any files are flagged as red (malicious):
    - The system will initiate an automatic cleanup procedure
    - The virtual USB stick will be destroyed after a 30-second countdown
    - The entire VM will be rebuilt to ensure no persistence of potentially malicious code
- When the VM or CLI script is terminated, either manually by the user or automatically by the system:
  - The virtual USB stick and all files stored on it will be immediately deleted
  - This ensures that no residual data remains that could pose a security risk

#### Security Considerations

Several potential security issues must be addressed in the implementation:
- **VM escape attacks**: The virtual USB stick represents a communication channel between the isolated VM and the host system
- **Data leakage**: Malicious code might access the virtual stick before it is properly isolated or destroyed
- **Size estimation challenges**: Technical difficulties when dealing with USB devices that may contain hidden partitions, zipped files or report incorrect capacity information

#### Technical Approaches

Two main technical solutions are being considered for implementing the virtual USB stick:

**Option 1: Shared Folder Mechanism**
- Advantages:
  - Simplicity and ease of implementation
  - No special drivers required
  - Straightforward permission control
  - Well-supported by most virtualization platforms
- Disadvantages:
  - Not truly a USB device
  - Might not behave exactly like a physical USB stick in all scenarios

**Option 2: Disk Image Emulation**
- Advantages:
  - Behaves like an actual USB device
  - Better isolation between the VM and host system
- Disadvantages:
  - More complex to implement
  - Requires careful filesystem operations
  - Presents challenges in dynamic size management

#### Possible useful links
- [How to create a disk image](https://unix.stackexchange.com/questions/328156/create-virtual-usb-drive) -> [fallocate](https://man7.org/linux/man-pages/man1/fallocate.1.html)
- [Linus MSG](https://www.kernel.org/doc/Documentation/usb/mass-storage.txt)
- [Raw Gadget](https://github.com/xairy/raw-gadget)
- [Shared Folder](https://askubuntu.com/questions/161759/how-to-access-a-shared-folder-in-virtualbox)


### 3. CLI (VM Start, USB Script): Paul Ilitz



### 4. Virus Scan & Traffic-Light System: Constantin Scheryer



### 5. USB Pass-Through Host → VM (Interface): Tizian Everke & Richard Kats

We aim to identify an inserted USB stick (is it a keyboard? a flash drive?) and pass it through to the VM.

#### Thoughts / Notes:
- Detect whether it’s really a USB stick (or a keyboard, mouse, etc.) → defined in firmware  
- If yes, determine how USB filters (e.g., in VirtualBox) work and forward the device to the VM  
- Do not mount on the host until the scan is complete (success or exception can be communicated via SSH)

#### Proposed Process / Possible Solution
1. CLI tool (Rust?) is started by the user  
2. CLI tool prompts the user to insert a USB device  
3. Detect what kind of device was inserted (USB stick, keyboard, …) (driver level?)  
   - [ ] Ideally **before enumeration!** USB sticks often have malicious firmware that pretends to be a keyboard (read papers)  
   - [ ] Where does enumeration happen?  
   - [ ] What exactly happens during enumeration?  
   - [ ] How can enumeration be aborted if it’s not a USB stick (while the tool is running)?  
   → Ensures that a USB stick cannot pretend to be, e.g., a keyboard  
4. Start VM *  
5. Run virus scan *  
6. Display result *  
7. Show data on host system *  

#### Possible Issues
- At which layer does inserting a USB stick become dangerous? (driver level, …)  
- A USB stick might have smaller or multiple (hidden?) partitions to conceal data  
- Most USB-based malware resides in the firmware  
  - How and where could this be detected?  

#### Sources
In shared Zotero group, to be added here later  



### 6. GUI (Automated File Management): Aaron Debebe