import QtQuick 2.0
import calamares.slideshow 1.0

// HSCL1 installer slideshow: three text slides in the language of the installer (en, de, fr).
Presentation {
    id: presentation

    function tr(en, de, fr) {
        var l = Qt.locale().name.substring(0, 2)
        return l === "de" ? de : (l === "fr" ? fr : en)
    }

    Timer {
        interval: 9000
        running: presentation.activatedInCalamares
        repeat: true
        onTriggered: presentation.goToNextSlide()
    }

    Slide {
        Rectangle { anchors.fill: parent; color: "#0e1117" }
        Text {
            anchors.centerIn: parent
            width: parent.width * 0.8
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.Wrap
            color: "#e8ecf3"
            font.pixelSize: 26
            text: "HSCL1\n" + presentation.tr("Made with love by hcsmedia", "Mit Liebe gemacht von hcsmedia", "Fait avec amour par hcsmedia")
        }
    }
    Slide {
        Rectangle { anchors.fill: parent; color: "#0e1117" }
        Text {
            anchors.centerIn: parent
            width: parent.width * 0.8
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.Wrap
            color: "#e8ecf3"
            font.pixelSize: 22
            text: presentation.tr("Your files stay yours: HSCL1 sends no telemetry.",
                                  "Ihre Dateien bleiben Ihre: HSCL1 sendet keine Telemetrie.",
                                  "Vos fichiers restent les vôtres : HSCL1 n'envoie aucune télémétrie.")
        }
    }
    Slide {
        Rectangle { anchors.fill: parent; color: "#0e1117" }
        Text {
            anchors.centerIn: parent
            width: parent.width * 0.8
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.Wrap
            color: "#e8ecf3"
            font.pixelSize: 22
            text: presentation.tr("Press Meta+K after installation for the shortcut overview and open the HSCL1 Handbook from the dock.",
                                  "Drücken Sie nach der Installation Meta+K für die Tastenkürzel und öffnen Sie das HSCL1-Handbuch im Dock.",
                                  "Après l'installation, appuyez sur Meta+K pour les raccourcis et ouvrez le manuel HSCL1 depuis le dock.")
        }
    }
}
