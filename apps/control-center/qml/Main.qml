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

    readonly property var pageTitles: [qsTr("Overview"), qsTr("Appearance"), qsTr("Security"), qsTr("Miner"), qsTr("About")]

    /// main.cpp installs the CLI bridge as the context property `cli`. Reading it once here and handing the
    /// value to a declared property keeps every page binding qualified, so qmllint stops flagging each use as
    /// unqualified access (and the pages get a typed member instead of a global).
    readonly property var cliBackend: typeof cli !== "undefined" ? cli : null

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
            OverviewPage { backend: win.cliBackend }
            AppearancePage { backend: win.cliBackend }
            SecurityPage { backend: win.cliBackend }
            MinerPage { backend: win.cliBackend }
            AboutPage { backend: win.cliBackend }
        }
    }
}
