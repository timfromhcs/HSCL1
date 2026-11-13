pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls.Basic
import ".."

Rectangle {
    id: rail
    property var model: []
    property alias currentIndex: list.currentIndex
    color: Theme.surface1
    Accessible.role: Accessible.PageTabList
    Accessible.name: qsTr("Navigation")
    focus: true
    activeFocusOnTab: true
    // keyboard users land on the list when the rail is focused
    onActiveFocusChanged: if (activeFocus) list.forceActiveFocus()

    Text {
        id: brand
        text: "HSCL1"
        color: Theme.accent
        font.pixelSize: Theme.font2xl
        font.bold: true
        anchors { left: parent.left; top: parent.top; margins: Theme.space5 }
    }

    ListView {
        id: list
        anchors { left: parent.left; right: parent.right; top: brand.bottom; bottom: parent.bottom; topMargin: Theme.space5 }
        model: rail.model
        focus: true
        keyNavigationEnabled: true
        currentIndex: 0
        clip: true
        delegate: ItemDelegate {
            id: item
            // Declared so qmllint resolves them instead of reporting unqualified access, and so the delegate is
            // typed for a reader. `ListView.view` replaces the outer `list` id for the same reason.
            required property int index
            required property string modelData
            width: ListView.view.width
            height: 44
            highlighted: ListView.isCurrentItem
            text: item.modelData
            Accessible.role: Accessible.PageTab
            Accessible.name: item.modelData
            onClicked: ListView.view.currentIndex = item.index
            contentItem: Text {
                text: item.text
                color: item.highlighted ? Theme.textPrimary : Theme.textSecondary
                font.pixelSize: Theme.fontMd
                font.bold: item.highlighted
                verticalAlignment: Text.AlignVCenter
                leftPadding: Theme.space4
                rightPadding: Theme.space2
                // "Updates & Wiederherstellung" is longer than the rail; elide instead of clipping the glyphs.
                elide: Text.ElideRight
            }
            background: Rectangle {
                color: item.highlighted ? Theme.accentSoft : "transparent"
                border.color: item.activeFocus ? Theme.focusRing : "transparent"
                border.width: 2
                radius: Theme.radiusMd
            }
        }
    }

    Text {
        text: qsTr("Made with love by hcsmedia")
        color: Theme.textMuted
        font.pixelSize: Theme.fontXs
        anchors { left: parent.left; bottom: parent.bottom; margins: Theme.space4 }
    }
}
