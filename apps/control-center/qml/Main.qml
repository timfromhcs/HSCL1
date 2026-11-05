import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

ApplicationWindow {
    id: win
    width: 1100
    height: 700
    minimumWidth: 800
    minimumHeight: 520
    visible: true
    title: qsTr("HSCL1 Control Center")
    color: Theme.surface0

    Component.onCompleted: rail.forceActiveFocus()

    readonly property var pageTitles: [qsTr("Overview"), qsTr("Appearance"), qsTr("Security"), qsTr("About")]

    RowLayout {
        anchors.fill: parent
        spacing: 0

        NavRail {
            id: rail
            Layout.fillHeight: true
            Layout.preferredWidth: 220
            model: win.pageTitles
            onCurrentIndexChanged: stack.currentIndex = currentIndex
        }

        StackLayout {
            id: stack
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: rail.currentIndex
            OverviewPage { backend: cli }
            AppearancePage { backend: cli }
            SecurityPage { backend: cli }
            AboutPage { backend: cli }
        }
    }
}
