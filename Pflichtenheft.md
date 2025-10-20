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