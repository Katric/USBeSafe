use std::thread;
use std::time::Duration;
use std::io;

struct UsbManager;

impl UsbManager {
    fn block_and_identify(&self) {
        // TODO
    }

    fn create_virtual_usb(&self) {
        // TODO
    }
}

struct VmManager;

impl VmManager {
    fn launch_vm(&self) {
        // TODO: spawn QEMU process
    }

    fn destroy_vm(&self) {
        // TODO: kill QEMU process
    }

    fn send_to_guest(&self, msg: &str) {
        // TODO: virtio write
    }

    fn recv_from_guest(&self) -> Option<String> {
        // TODO: virtio read
        Some("XXX".to_string())
    }
}

struct IpcServer;

impl IpcServer {
    fn run(&self, path: &str) {
        // TODO: create and bind to socket, accept connections
    }

    fn handle_client(&self) {
        // TODO: read messages from CLI/GUI
    }
}

fn main() {
    println!("usbesafed daemon starting...");

    let usb = UsbManager;
    let vm = VmManager;
    let ipc = IpcServer;

    usb.block_and_identify();
    usb.create_virtual_usb();

    vm.launch_vm();

    thread::spawn(move || {
        ipc.run("/opt/usbesafe/run/usbesafed.sock");
    });

    println!("usbesafed running. Press Enter to exit.");

    let mut input = String::new();
    io::stdin().read_line(&mut input).unwrap();

    vm.destroy_vm();

    println!("usbesafed exiting.");
}

