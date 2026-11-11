# Bekannte Einschränkungen

- Pre-Alpha: Auf echter Hardware wurde nichts getestet. Alles Folgende wurde in virtuellen Maschinen gemessen
  (UEFI, QEMU/KVM oder WHPX).
- Die Release-Artefakte sind **nicht signiert**; veröffentlicht werden nur SHA-256-Prüfsummen.
- Secure Boot ist für HSCL1-Images nicht verifiziert.
- Der Installer beendet sich gelegentlich 2-3 s nach dem Start (etwa einer von sechs bis zwölf Starts) und wird
  dann von `/usr/bin/hscl-calamares` neu gestartet. Auf Images ohne diesen Wrapper hilft ein erneuter Start -
  der nächste Versuch gelingt in der Regel.
- `hscl` (Version, Status, Doctor, Themes, Hintergründe, Privacy-Status, Lab-Befehle, KI-Erkennung) und das
  Control Center (Übersicht, Erscheinungsbild, Sicherheit, Miner, Über) sind umgesetzt. Security Lab und
  Privacy-Ablauf sind **Kommandozeilen-Abläufe**, keine eigenen Desktop-Modi.
- Das Security Lab führt Werkzeuge in rootless-Podman-Containern aus. GUI-Werkzeuge, WLAN-/USB-Durchreichung und
  wegwerfbare VM-Profile gibt es nicht.
- Der Privacy-Modus ist **nicht Tails**: Es gibt keinen verifizierten Netzwerk-Kill-Switch und keine
  verschlüsselte dauerhafte Ablage.
- Das Welcome Center zeigt nur die HSCL1-Seite, wenn es aus dem Menü geöffnet wird; das Verhalten beim ersten
  Login auf einem installierten System ist nicht verifiziert.
- Bei einem zweizeiligen Desktop-Symbol bricht die zweite Zeile links vom Symbolmittelpunkt um.
- Deutsch und Französisch folgen der englischen Struktur Kapitel für Kapitel.
