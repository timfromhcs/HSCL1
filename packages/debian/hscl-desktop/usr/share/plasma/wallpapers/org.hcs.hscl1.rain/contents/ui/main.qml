import QtQuick
import org.kde.kirigami as Kirigami
import org.kde.plasma.plasmoid

// HSCL1 wallpaper: number rain (default), starfield, aurora ribbons or grid pulse. Respects the system animation setting:
// with animations off every effect stands still. Parameters are clamped inside each effect.
WallpaperItem {
    id: root

    readonly property string effect: root.configuration.Effect || "rain"
    readonly property bool animate: Kirigami.Units.longDuration > 0
    readonly property color bg: root.configuration.Background ? root.configuration.Background : "#0e1117"
    readonly property color fg: root.configuration.Accent ? root.configuration.Accent : "#6c8cff"

    Loader {
        anchors.fill: parent
        sourceComponent: root.effect === "starfield" ? starC : root.effect === "aurora" ? auroraC : root.effect === "grid" ? gridC : rainC
    }

    Component { id: rainC; RainField { density: root.configuration.Density; speed: root.configuration.Speed; showMark: root.configuration.ShowMark; animate: root.animate; background: root.bg; glyphColor: root.fg } }
    Component { id: starC; StarField { density: root.configuration.Density; speed: root.configuration.Speed; showMark: root.configuration.ShowMark; animate: root.animate; background: root.bg; accent: root.fg } }
    Component { id: auroraC; AuroraField { density: root.configuration.Density; speed: root.configuration.Speed; showMark: root.configuration.ShowMark; animate: root.animate; background: root.bg; accent: root.fg } }
    Component { id: gridC; GridField { density: root.configuration.Density; speed: root.configuration.Speed; showMark: root.configuration.ShowMark; animate: root.animate; background: root.bg; accent: root.fg } }
}
