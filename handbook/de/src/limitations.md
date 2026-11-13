# Bekannte Einschränkungen

- Pre-Alpha: Auf echter Hardware wurde nichts getestet. Alles Folgende wurde in virtuellen Maschinen gemessen
  (UEFI, QEMU/KVM oder WHPX).
- Die Release-Artefakte sind **nicht signiert**; veröffentlicht werden nur SHA-256-Prüfsummen.
- Secure Boot wird im Gast ausgelesen (`mokutil --sb-state`, `hscl doctor`), aber ein positiver Secure-Boot-Start
  wurde nicht nachgewiesen: Dieser Host kann unter WHPX oder WSL/KVM nicht in den SMM wechseln. Es wird keine
  Secure-Boot-Aussage gemacht.
- Der Startabsturz des Installers (ein Segfault in der Notizseite, während der Fortschrittsbaum sie zeichnete) ist
  seit 0.1.8 behoben. `/usr/bin/hscl-calamares` startet einen Assistenten, der in der ersten Minute stirbt,
  weiterhin vorsorglich neu.
- `hscl` (Version, Status, Doctor, Themes, Hintergründe, Privacy-Status, Lab-Befehle, KI-Erkennung) und das
  Control Center (**elf reine Anzeigeseiten**: Übersicht, Erscheinungsbild, Sicherheit, Datenschutz,
  Sicherheitslabor, Lokale KI, Updates & Wiederherstellung, Entwicklung, Sprache & Region, Miner, Über) sind
  umgesetzt. Ein Theme anzuwenden ist die einzige Aktion des Panels; alles, was das System ändert, bleibt auf der
  Kommandozeile. Security Lab und Privacy-Ablauf sind weiterhin **Kommandozeilen-Abläufe**, keine eigenen
  Desktop-Modi.
- Das Security Lab führt Werkzeuge in rootless-Podman-Containern aus. GUI-Werkzeuge, WLAN-/USB-Durchreichung und
  wegwerfbare VM-Profile gibt es nicht.
- Der Privacy-Modus ist **nicht Tails**: Es gibt keinen verifizierten Netzwerk-Kill-Switch und keine
  verschlüsselte dauerhafte Ablage.
- Das Welcome Center öffnet die HSCL1-Seite, wenn es aus dem Menü gestartet wird; eine frische Installation
  meldet sich am nackten HSCL1-Desktop an, weil die Zustandsdatei vorbelegt ist und die KDE-Tour ausbleibt.
- Zweizeilige Desktop-Symbole sind unter ihrem Symbol zentriert (innerhalb 1 px gemessen); der frühere Hinweis auf
  eine nach links verschobene zweite Zeile war ein Eindruck aus dem gerenderten Bild, keine Messung.
- Deutsch und Französisch folgen der englischen Struktur Kapitel für Kapitel.
