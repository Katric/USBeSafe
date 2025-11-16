#!/bin/sh

PORT_PATH="/dev/virtio-ports/com.usbesafe.scan"

echo "[*] USBeSafe Guest Agent - starting"

# Wait for the virtio port to appear
echo "[*] Waiting for virtio port: $PORT_PATH"
ATTEMPTS=0
while [ ! -e "$PORT_PATH" ] && [ $ATTEMPTS -lt 60 ]; do
    sleep 1
    ATTEMPTS=$((ATTEMPTS + 1))
done

if [ ! -e "$PORT_PATH" ]; then
    echo "[!] Virtio port not found after 60 seconds. Exiting."
    exit 1
fi

echo "[+] Virtio port found: $PORT_PATH"
echo "[+] Agent ready, listening for commands"

# Open the port and keep it open for bidirectional communication
exec 3<>"$PORT_PATH"

# Read and respond to commands
while true; do
    read -r CMD <&3
    
    echo "[+] Received: $CMD"
    
    case "$CMD" in
        SCAN_USB_DEVICE)
            RESPONSE="CLEAN"
            ;;
        SHUTDOWN)
            echo "[*] Shutdown requested, sending ACK and halting"
            RESPONSE="ACK"
            echo "$RESPONSE" >&3
            exec 3>&-
            sleep 1
            exit 0
            ;;
        *)
            RESPONSE="UNKNOWN"
            ;;
    esac
    
    echo "$RESPONSE" >&3
    echo "[+] Sent: $RESPONSE"
done

echo "[*] Agent terminated"
