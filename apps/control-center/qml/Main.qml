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

    /// Rail labels. They must stay in the same order and number as the pages in the StackLayout below;
    /// `tests/unit/test_cc_pages.py` fails when the two drift apart.
    readonly property var pageTitles: [
        qsTr("Overview"), qsTr("Appearance"), qsTr("Security"), qsTr("Privacy"),
        qsTr("Security Lab"), qsTr("Local AI"), qsTr("Updates & Recovery"),
        qsTr("Developer"), qsTr("Language & Region"), qsTr("Miner"), qsTr("About")
    ]

    /// main.cpp installs the CLI bridge as the context property `cli`. Reading it once here and handing the
    /// value to a declared property keeps every page binding qualified, so qmllint stops flagging each use as
    /// unqualified access (and the pages get a typed member instead of a global).
    /// A C++ context property can never be resolved by the linter, so this single intentional read is suppressed
    /// locally rather than carried in the warning budget forever (Q-19).
    // qmllint disable unqualified
    readonly property var cliBackend: typeof cli !== "undefined" ? cli : null
    // qmllint enable unqualified

    RowLayout {
        anchors.fill: parent
        spacing: 0

        NavRail {
            id: rail
            Layout.fillHeight: true
            Layout.preferredWidth: 270
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
            PrivacyPage { backend: win.cliBackend }
            LabPage { backend: win.cliBackend }
            LocalAiPage { backend: win.cliBackend }
            UpdatesPage { backend: win.cliBackend }
            DeveloperPage { backend: win.cliBackend }
            LanguagePage { backend: win.cliBackend }
            MinerPage { backend: win.cliBackend }
            AboutPage { backend: win.cliBackend }
        }
    }
}
