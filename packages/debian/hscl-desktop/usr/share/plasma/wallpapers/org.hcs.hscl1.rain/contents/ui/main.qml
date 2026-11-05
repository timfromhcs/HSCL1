import QtQuick
import org.kde.kirigami as Kirigami
import org.kde.plasma.plasmoid

// HSCL1 Number Rain wallpaper. Respects the system animation setting: with animations off the rain stands still.
WallpaperItem {
    id: root

    RainField {
        anchors.fill: parent
        density: root.configuration.Density
        speed: root.configuration.Speed
        showMark: root.configuration.ShowMark
        animate: Kirigami.Units.longDuration > 0
    }
}
