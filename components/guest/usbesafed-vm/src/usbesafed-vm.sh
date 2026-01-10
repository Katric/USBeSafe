#!/bin/sh
set -eu

# ============================================================
# USBeSafe VM Daemon (Guest-Side)
# ============================================================
#
# GUEST RESPONSIBILITIES (HIGH-LEVEL OVERVIEW)
#
# 1. Wait until a REAL USB stick becomes visible inside the VM
#    (mounted at a predefined path).
#
# 2. Automatically run a malware scan on the REAL USB stick.
#
# 3. If the scan FAILS:
#      - Send "fail" to the host via virtio
#      - Do nothing else (host will destroy VM + overlay)
#
# 4. If the scan SUCCEEDS:
#      - Calculate the USED size of the REAL USB stick
#      - Round the size UP to full GiB units
#      - Send "size_gb:<N>" to the host via virtio
#        (Host uses this to create a fitting virtual USB stick)
#      - Send "ok" to the host
#
# 5. Wait until the host attaches a VIRTUAL USB stick (via QMP)
#    and it becomes mounted inside the VM.
#
# 6. Copy all data from REAL USB → VIRTUAL USB.
#
# 7. Send "copy_done" to the host via virtio.
#
# 8. Wait until both USBs are removed to avoid re-triggering.
#
# IMPORTANT:
# - This daemon NEVER:
#     * creates USB devices
#     * attaches USB devices
#     * deletes overlays
#     * shuts down the VM
# - The host is the single authority for lifecycle control.
#
# ============================================================


# -----------------------------
# Placeholder paths (adjust later)
# -----------------------------

# ============================================================
# Startup Banner
# ============================================================

# Used for logging the vm, logs can be looke at by running `grep usbesafed-vm /var/log/messages` in the vm
log() {
  logger -t usbesafed-vm -- "$*"
}


log "============================================================"
log "USBeSafe VM Daemon started"
log "Role      : Guest-side USB scanning daemon"
log "State     : Initializing"
log "============================================================"


# Mount point of the real, physical USB stick inside the VM
REAL_USB_MOUNT="/mnt/realusb"

# Mount point of the virtual USB stick created by the host
VUSB_MOUNT="/mnt/vusb"

# Virtio serial port created by QEMU (name=com.securepass.comm)
VIRTIO_PORT="/dev/virtio-ports/com.securepass.comm"

# Placeholder scanner script (actual logic lives there)
SCANNER_CMD="/opt/scanner/scanner.py"

# Polling interval in seconds
POLL_SEC=1

# Create the mount point directories (if missing)
mkdir -p "$REAL_USB_MOUNT" "$VUSB_MOUNT"

# -----------------------------
# Helper functions
# -----------------------------

send_virtio() {
  # Send a single line message to the host via virtio
  # This is the ONLY communication channel VM → Host
  if [ ! -e "$VIRTIO_PORT" ]; then
    log "ERROR: virtio port not found: $VIRTIO_PORT"
    return 1
  fi

  # Try to send; if it fails, log the error
  if ! printf "%s\n" "$1" > "$VIRTIO_PORT"; then
    log "ERROR: failed to write to virtio port: $VIRTIO_PORT"
    return 1
  fi

  log "VM → HOST: $1"
}

wait_for_mount() {
  # Block until a filesystem is actually mounted at the given path
  log "Waiting for mount at: $1"
  while ! mount | grep -q " $1 "; do
    sleep "$POLL_SEC"
  done
  log "Mounted filesystem detected at: $1"
}

run_scan() {
  # Placeholder scan invocation
  #
  # Expected semantics:
  #   return 0 → scan OK
  #   return 1 → scan FAIL
  #
  # Actual scanning logic lives in scanner.py

  log "Starting scan. USB mount: $REAL_USB_MOUNT"
  if [ ! -d "$REAL_USB_MOUNT" ]; then
    log "WARN: REAL_USB_MOUNT is not a directory (yet?): $REAL_USB_MOUNT"
  fi

  if [ -f "$SCANNER_CMD" ]; then
    log "Scanner script found: $SCANNER_CMD"

    if command -v python3 >/dev/null 2>&1; then
      log "python3 found. Executing scanner..."
      python3 "$SCANNER_CMD" "$REAL_USB_MOUNT"
      rc=$?
      log "Scanner finished with exit code: $rc"
      return $rc
    fi

    log "WARN: python3 not found. Trying to execute scanner directly..."
    "$SCANNER_CMD" "$REAL_USB_MOUNT"
    rc=$?
    log "Scanner finished with exit code: $rc"
    return $rc
  fi

  # Scanner missing is a hard failure (fail closed)
  log "ERROR: Scanner missing at $SCANNER_CMD -> rejecting USB"
  return 1
}

send_usb_size_gb() {
  # Determine how much space is USED on the REAL USB stick
  #
  # Purpose:
  #   Inform the host how large the virtual USB stick must be.
  #   Host will round-create the virtual USB accordingly.
  #
  # Output format:
  #   size_gb:<N>

  log "Calculating USB used size for: $REAL_USB_MOUNT"

  if ! command -v df >/dev/null 2>&1; then
    log "ERROR: df not available. Cannot calculate USB size."
    return 0
  fi

  if ! command -v awk >/dev/null 2>&1; then
    log "ERROR: awk not available. Cannot parse df output."
    return 0
  fi

  if ! used_kb="$(df -P "$REAL_USB_MOUNT" 2>/dev/null | awk 'NR==2 {print $3}')"; then
    log "ERROR: df failed for mount: $REAL_USB_MOUNT"
    return 0
  fi

  if [ -z "${used_kb:-}" ] || ! echo "$used_kb" | grep -Eq '^[0-9]+$'; then
    log "ERROR: Could not parse used_kb from df output (got: '${used_kb:-}')"
    log "DEBUG: df output:"
    df -P "$REAL_USB_MOUNT" || true
    return 0
  fi

  log "Used space (df): ${used_kb} KiB"

  # Convert to bytes
  used_bytes=$(( used_kb * 1024 ))

  # One GiB in bytes
  gib=$(( 1024 * 1024 * 1024 ))

  # Ceiling division: round UP to full GiB
  size_gb=$(( (used_bytes + gib - 1) / gib ))

  # Safety: minimum size is 1 GiB
  [ "$size_gb" -lt 1 ] && size_gb=1

  log "Rounded size (GiB): $size_gb"
  send_virtio "$size_gb" || log "WARN: failed to send size_gb message"
}

copy_real_to_vusb() {
  # Copy all contents from REAL USB → VIRTUAL USB
  #
  # -a preserves attributes and directories

  log "Starting copy: $REAL_USB_MOUNT -> $VUSB_MOUNT"

  if [ ! -d "$REAL_USB_MOUNT" ]; then
    log "ERROR: real USB mount directory missing: $REAL_USB_MOUNT"
    return 1
  fi

  if [ ! -d "$VUSB_MOUNT" ]; then
    log "ERROR: virtual USB mount directory missing: $VUSB_MOUNT"
    return 1
  fi

  # Optional debug: show a quick listing (can be noisy, but helpful)
  log "DEBUG: real USB content (top-level):"
  ls -la "$REAL_USB_MOUNT" 2>/dev/null | head -n 30 || true

  if cp -a "$REAL_USB_MOUNT"/. "$VUSB_MOUNT"/; then
    log "Copy completed successfully"
    return 0
  fi

  log "ERROR: copy failed (cp returned non-zero)"
  return 1
}


# ============================================================
# Main Daemon Loop
# ============================================================

# Wait until QEMU exposes the virtio serial port
log "Daemon boot: waiting for virtio port $VIRTIO_PORT"
while [ ! -e "$VIRTIO_PORT" ]; do
  log "Still waiting for virtio port: $VIRTIO_PORT"
  sleep "$POLL_SEC"
done
log "Virtio port detected: $VIRTIO_PORT"

# Startup banner with current config
log "Daemon started"
log "Config: REAL_USB_MOUNT=$REAL_USB_MOUNT"
log "Config: VUSB_MOUNT=$VUSB_MOUNT"
log "Config: VIRTIO_PORT=$VIRTIO_PORT"
log "Config: SCANNER_CMD=$SCANNER_CMD"
log "Config: POLL_SEC=$POLL_SEC"

while :; do
  # ----------------------------------------------------------
  # 1) Wait for REAL USB stick
  # ----------------------------------------------------------
  wait_for_mount "$REAL_USB_MOUNT"
  log "Real USB detected"

  # ----------------------------------------------------------
  # 2) Run malware scan
  # ----------------------------------------------------------
  if run_scan; then
    # ------------------------------------------------------
    # 3a) Scan OK
    # ------------------------------------------------------
    log "Scan result: OK"
    send_virtio "ok"     # positive scan result
    send_usb_size_gb     # inform host about required vUSB size
  else
    # ------------------------------------------------------
    # 3b) Scan FAIL
    # ------------------------------------------------------
    log "Scan result: FAIL"
    send_virtio "fail"
    log "Scan failed, waiting for USB removal"

    # Debounce: wait until USB is removed
    while mount | grep -q " $REAL_USB_MOUNT "; do
      sleep "$POLL_SEC"
    done
    log "Real USB removed"
    continue
  fi

  # ----------------------------------------------------------
  # 4) Wait for VIRTUAL USB stick (host attaches via QMP)
  # ----------------------------------------------------------
  # Wait until the vUSB is actually mounted at $VUSB_MOUNT
  # (Directory existence is not enough; /mnt/vusb usually exists already)
  while ! mount | grep -q " $VUSB_MOUNT "; do
    mount -t vfat /dev/disk/by-label/USBeSafe "$VUSB_MOUNT" 2>/dev/null || true
    sleep "$POLL_SEC"
  done
  log "Virtual USB mounted and ready"

  # ----------------------------------------------------------
  # 5) Copy data
  # ----------------------------------------------------------
  if copy_real_to_vusb; then
    send_virtio "copy_done"
  else
    # Copy failing is important to see on the host.
    # We still log here; you can later decide if you want an explicit protocol message.
    log "ERROR: Copy failed. (Host-side reaction TBD)"
  fi

  # ----------------------------------------------------------
  # 6) Debounce until both USBs are removed
  # ----------------------------------------------------------
  log "Copy finished, waiting for USB removal"
  while mount | grep -q " $REAL_USB_MOUNT " || mount | grep -q " $VUSB_MOUNT "; do
    sleep "$POLL_SEC"
  done
  log "USBs removed, returning to idle state"
done
