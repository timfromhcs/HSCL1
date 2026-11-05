import QtQuick
import QtQuick.Layouts
import ".."

RowLayout {
    id: row
    property string label: ""
    property string value: ""
    Layout.fillWidth: true
    spacing: Theme.space3
    Accessible.role: Accessible.StaticText
    Accessible.name: label + ": " + value
    Text {
        text: row.label
        color: Theme.textSecondary
        font.pixelSize: Theme.fontMd
        Layout.preferredWidth: 180
        elide: Text.ElideRight
    }
    Text {
        text: row.value
        color: Theme.textPrimary
        font.pixelSize: Theme.fontMd
        Layout.fillWidth: true
        wrapMode: Text.Wrap
    }
}
