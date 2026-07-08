# USBeSafe
This is the result of the project study "Secure Systems" at Munich University of Applied Sciences. This tool is WIP!

We redirect all plugged in USB devices into a fresh sandbox VM. 
Inside the VM different checks are performed, depending of the reported capabilities:
- If the device is a mass-storage device, ClamAV is used to detect malware
- If the device reports keyboard capabilities (e.g. also single buttons), the user has to play a Red-Light-Green-Light game
Only after all challenges have been passed successfully, the device becomes usable on the host PC.

Also, there is no danger of locking out: The device is always usable inside the VM to pass the challenges, e.g. in case of a keyboard or a mouse!

## 🧾 Management Summary

## 📁 Directory Structure

## Instructions for Running the Application

### Installation

1. Install qemu: *apt-get install qemu-system*
2. Install requirements: *sudo apt-get install -y qemu-system-x86 qemu-utils libvirt-clients qemu-kvm wget curl yad*
3. Run: *sudo python3 components/host/usbesafed/src/host_daemon.py*

## 📝 Additional Documentation:

- **Definition of Requirements and Work Packages:** see `/docs/Requirements_Specifications.md`
