#!/bin/sh

# Pfade anpassen falls nötig
USB_REAL="/mnt/realusb"
USB_VIRTUAL="/mnt/virtusb"
VIRTIO_PORT="/dev/virtio-ports/securepass"

log() {
    echo "[DAEMON] $1"
}

send_msg() {
    echo "$1" > "$VIRTIO_PORT"
    log "→ HOST: $1"
}

log "Starte VM-Daemon..."
log "Warte auf USB-Device im Pfad: $USB_REAL"

# Warten bis echter USB-Stick erscheint
while [ ! -d "$USB_REAL" ] || [ -z "$(ls -A "$USB_REAL" 2>/dev/null)" ]; do
    sleep 1
done

log "USB erkannt! Starte Scan... (Scanlogik extern/angepasst)"
# --------------------------------------------------------------
# Hier würde normalerweise der Virenscan laufen.
# Wir simulieren ihn nur durch ein externes Ergebnis.
# --------------------------------------------------------------

# Beispiel: Ergebnisdatei prüfen (ersetze später durch echten Scan)
SCAN_RESULT_FILE="$USB_REAL/result.txt"

if [ -f "$SCAN_RESULT_FILE" ] && grep -q "fail" "$SCAN_RESULT_FILE"; then
    send_msg "fail"
    log "Scan ergab FAIL, beende."
    exit 0
fi

# Standard: Erfolg
send_msg "ok"
log "Scan war OK, warte auf virtuellen USB-Stick..."

# Warten auf virtuellen USB-Stick
while [ ! -d "$USB_VIRTUAL" ] || [ -z "$(ls -A "$USB_VIRTUAL" 2>/dev/null)" ]; do
    sleep 1
done

log "Virtueller USB-Stick erkannt: $USB_VIRTUAL"
log "Kopiere Dateien..."

cp -r "$USB_REAL"/* "$USB_VIRTUAL"/

log "Kopieren abgeschlossen."
send_msg "copy_done"

log "Daemon beendet."
exit 0
