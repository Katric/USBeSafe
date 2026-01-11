VIRTIO_PORT_PATH = "/dev/virtio-ports/com.securepass.comm"


def send_to_host(message: str):
    """
    Sends a message via virtio to host system.
    """
    try:
        with open(VIRTIO_PORT_PATH, "w") as f:
            f.write(message + "\n")
            f.flush()
            print(f"[INFO] Sent message via Virtio: {message}")

    except Exception as e:
        print(f"[ERROR] Virtio Error: {e}")
