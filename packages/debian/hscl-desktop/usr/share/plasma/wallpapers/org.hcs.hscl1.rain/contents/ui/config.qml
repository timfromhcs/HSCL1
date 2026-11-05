import QtQuick
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami
import org.kde.kcmutils as KCM

KCM.SimpleKCM {
    property alias cfg_Density: density.value
    property alias cfg_Speed: speed.value
    property alias cfg_ShowMark: mark.checked

    Kirigami.FormLayout {
        QQC2.SpinBox { id: density; from: 1; to: 3; Kirigami.FormData.label: i18n("Density:") }
        QQC2.SpinBox { id: speed; from: 1; to: 3; Kirigami.FormData.label: i18n("Speed:") }
        QQC2.CheckBox { id: mark; text: i18n("Show the HSCL1 mark"); Kirigami.FormData.label: i18n("Logo:") }
    }
}
