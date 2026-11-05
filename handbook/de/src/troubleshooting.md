# Fehlerbehebung

| Problem | Lösungsvorschlag |
|---|---|
| Schwarzer Bildschirm in der VM | Standard-VGA verwenden und 3D-Beschleunigung ausschalten. |
| Sehr langsamer Start | Hardwarebeschleunigung (KVM oder WHPX) aktivieren; Softwareemulation braucht mehrere Minuten. |
| Der Installer meldet „keine Partitionen" | Der virtuellen Maschine ist keine Festplatte zugewiesen. Eine virtuelle Wegwerf-Festplatte anhängen. |
| `hscl doctor` meldet AppArmor deaktiviert | Normal unter WSL oder Kerneln ohne AppArmor; auf einer echten HSCL1-Installation sollte es aktiv sein. |
