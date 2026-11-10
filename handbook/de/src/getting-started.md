# Erste Schritte

## In einer virtuellen Maschine ausprobieren

Verwenden Sie QEMU mit UEFI-Firmware (OVMF/edk2) oder klassischem BIOS. Getestete Einstellungen (Pre-Alpha):

| Einstellung | Wert |
|---|---|
| Arbeitsspeicher | 4 GB |
| CPUs | 4 |
| Grafik | Standard-VGA, kein 3D |
| Netzwerk | Benutzermodus (NAT) |

Auf einem beschleunigten Host erscheint der Live-Desktop nach etwa zwei Minuten. Wählen Sie im Boot-Menü **Try or Install HSCL1**.

## Installation

Der Installer ist der **HSCL1 Installer**, ein gebrandetes Calamares. Er braucht eine Festplatte, die gelöscht werden darf:
**verwenden Sie eine virtuelle Wegwerf-Festplatte.**

- **Unverschlüsselte Installation:** geprüft mit **4 GB** Arbeitsspeicher (ESP + ext4-Root, endet mit „All done").
- **LUKS2-verschlüsselte Installation:** geben Sie der VM **8 GB** Arbeitsspeicher. Ein Versuch mit 6 GB ist einmal
  abgestürzt; dokumentiert sind 8 GB.
- Die Systempartition wird mit LUKS2 verschlüsselt; Sie geben die Passphrase bei jedem Start ein. EFI-Partition und
  ein separates `/boot` bleiben ohne Passphrase lesbar. Es gibt **eine** Passphrase und **keinen Recovery-Key**:
  Wer sie vergisst, kann die Daten nicht wiederherstellen.

Der Installer schreibt auf die gewählte Festplatte. Ein geprüfter Dual-Boot-Aufbau wird nicht angeboten, und auf
physischer Hardware wurde nichts getestet.
