import QtQuick
import QtQuick.Layouts
import ".."

Rectangle {
    id: card
    property string title: ""
    default property alias content: body.data
    color: Theme.surface1
    radius: Theme.radiusLg
    border.color: Theme.borderSubtle
    border.width: 1
    implicitHeight: col.implicitHeight + 2 * Theme.space4
    Layout.fillWidth: true
    Accessible.role: Accessible.Grouping
    Accessible.name: title

    ColumnLayout {
        id: col
        anchors { left: parent.left; right: parent.right; top: parent.top; margins: Theme.space4 }
        spacing: Theme.space3
        Text {
            text: card.title
            color: Theme.textPrimary
            font.pixelSize: Theme.fontLg
            font.bold: true
            Layout.fillWidth: true
            elide: Text.ElideRight
        }
        ColumnLayout {
            id: body
            Layout.fillWidth: true
            spacing: Theme.space2
        }
    }
}
