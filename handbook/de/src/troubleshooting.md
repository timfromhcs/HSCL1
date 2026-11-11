# Fehlerbehebung

| Problem | Was zu tun ist |
|---|---|
| Schwarzer Bildschirm in einer VM | Standard-VGA verwenden und 3D-Beschleunigung abschalten. |
| Sehr langsamer Start | Hardware-Beschleunigung aktivieren (KVM oder WHPX); reine Software-Emulation braucht mehrere Minuten. |
| Der Installer meldet "keine Partitionen" | Der virtuellen Maschine fehlt eine Festplatte. Eine wegwerfbare virtuelle Festplatte anhängen. |
| Der Installer bricht mit `hscl-verify-esp: … did not populate the EFI system partition` ab | Das System wurde geschrieben, aber kein EFI-Bootloader auf der EFI-Partition abgelegt - der Rechner würde nicht starten. Es geht nichts verloren: Installation erneut starten und, falls es wieder passiert, die genaue Meldung aus `/var/log/calamares.log` melden. |
| Das Installer-Fenster verschwindet kurz nach dem Start | Bekannter, sporadischer Fehler (etwa einer von sechs bis zwölf Starts). Auf aktuellen Images startet der Launcher selbst neu; auf älteren einfach erneut starten. |
| Nach dem Login erscheint ein "Welcome Center" mit KDE-Seiten | Nur bei älteren Images. Aktuelle Images öffnen das Welcome Center auf der HSCL1-Seite, und beim ersten Login öffnet es sich gar nicht. |
| `hscl doctor` meldet AppArmor deaktiviert | In WSL oder auf Kernen ohne AppArmor normal; auf einer echten HSCL1-Installation sollte es aktiv sein. |
