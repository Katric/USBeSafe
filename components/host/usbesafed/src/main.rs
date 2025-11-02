use nix::libc::{POLLIN, nfds_t, pollfd, ppoll};
use std::io::Error;
use std::os::fd::AsRawFd;
use std::thread;
use std::time::Duration;
use std::{io, ptr};

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

fn poll_usb() -> Result<(), Error> {
    println!("Starting USB device monitor...");

    // Create a monitor builder to set up the udev monitoring.
    let builder = udev::MonitorBuilder::new()?.match_subsystem("usb")?;

    // Build the monitor, which gives us a socket to listen on.
    let monitor = builder.listen()?;

    println!("Listening for 'add' events on the 'usb' subsystem...");

    let mut fds = vec![pollfd {
        fd: monitor.as_raw_fd(),
        events: POLLIN,
        revents: 0,
    }];

    loop {
        let result = unsafe {
            ppoll(
                (&mut fds[..]).as_mut_ptr(),
                fds.len() as nfds_t,
                ptr::null_mut(),
                ptr::null(),
            )
        };

        if result < 0 {
            return Err(io::Error::last_os_error());
        }

        let event = match monitor.iter().next() {
            Some(evt) => evt,
            None => {
                println!("Usb monitor None Event");
                thread::sleep(Duration::from_millis(10));
                continue;
            }
        };

        let device = event.device();

        let vendor = device.attribute_value("idVendor");

        println!("{}", vendor.unwrap().to_string_lossy());

        //println!("{:?}", event);
    }
}

fn main() {
    let _ = poll_usb();

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
