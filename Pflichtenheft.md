# SecurePass (Maybe USBeSafe? ;))

### Minimale Anforderungen an das Projekt:
- Funktionierendes CLI-Tool, das USB-Sticks auf Schadsoftware analysiert, einen Bericht in _Nautilus_ anzeigt und im Anschluss auf dem Hostsystem mountet

### Ideen:
- [ ] Gemeinsame Zotero Gruppe für Literatur? -> Einheitliches bib File
- [ ] Final Paper in Overleaf (Man braucht Premium) oder hier im Projekt?

---

## Tizian Everke & Richard Kats: USB-Stick sicher zur VM durchreichen

Wir wollen einen eingesteckten USB-Stick identifizieren (Ist es eine Tastatur? Flash Drive? ...) und in die VM durchreichen.

### Gedanken / Notizen:
- Erkennen, ob es wirklich ein USB-Stick ist (oder Tastatur, Maus, etc.) → Wird in der Firmware definiert
- Wenn ja, herausfinden, wie USB-Filter (z.B. in VirtualBox) funktionieren und an VM weiterreichen 
- nicht auf Host mounten, bis Prüfung erfolgreich (Erfolg oder Exception z.B. über ssh kommunizieren)

### Prozessvorschlag/ Lösungsmöglichkeit
1. CLI-Tool (Rust?) wird durch User gestartet
2. CLI-Tool fordert den User auf USB-Device einzustecken
3. Erkennen, welches Gerät eingesteckt wurde (USB-Stick, Tastatur, ...) (Treiber Ebene?)?
   - [ ] Am besten vor Enumeration! USB-Sticks haben oft gefährliche Firmware, die sich als Tastatur ausgibt (Paper lesen)
   - [ ] Wo geschieht die Enumeration?
   - [ ] Was passiert bei der Enumeration?
   - [ ] Wie kann man die Enumeration abbrechen, falls es kein USB-Stick ist (während das Tool läuft)?
   → Dadurch wird sichergestellt, dass sich ein USB-Stick nicht z.B. als Tastatur ausgeben kann
4. VM starten*
5. Virenscan durchführen*
6. Ergebnis anzeigen*
7. Daten auf Host-System anzeigen*

### Mögliche Probleme
- Ab welcher Ebene wird USB-Stick hereinstecken gefährlich? (Treiber, ...)
- USB-Stick kann vielleicht kleinere / mehrere (anonyme?) Partitionen haben, um Sachen zu verstecken
- Meiste USB Schadsoftware sind in Firmware
  - Wie und wo könnte man das erkennen?

### Quellen
In Zotero Gruppe, ggf. später hier einfügen

---
