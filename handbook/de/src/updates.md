# Aktualisierungen

HSCL1 erhält Aktualisierungen über APT aus den Archiven von Ubuntu 26.04 LTS (`resolute`). Es wird nichts an einen HSCL1-Server gesendet.

## Nach Aktualisierungen suchen

```console
$ hscl system updates --check
```

Das ist eine Simulation: Der Befehl listet, was aktualisiert werden könnte, wie viele Pakete aus dem Sicherheits-Kanal stammen und ob ein Neustart nötig ist. Es wird nichts installiert. Ist apt selbst defekt, meldet der Befehl einen Fehler statt „0 Aktualisierungen".

## Installiertes System

- **Sicherheitsaktualisierungen** werden automatisch installiert (unbeaufsichtigte Aktualisierungen, nur Sicherheits-Kanal).
- Andere Aktualisierungen installieren Sie selbst, zum Beispiel in Discover oder mit `sudo apt update && sudo apt upgrade`.
- HSCL1 startet den Computer nie von selbst neu. Ist ein Neustart nötig, sagt es `hscl system updates --check`.

## Live-Sitzung

Das Live-ISO ist schreibgeschützt. Änderungen, auch installierte Aktualisierungen, gehen beim Herunterfahren verloren. Für dauerhaft neuere Pakete installieren Sie HSCL1 oder verwenden ein neueres Abbild.

## Vorgefertigtes Abbild

Das vorgefertigte Festplattenabbild wird wie ein installiertes System aktualisiert. Ein neueres Abbild brauchen Sie nur für einen frischen Start.
