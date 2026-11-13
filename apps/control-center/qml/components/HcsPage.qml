import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import ".."

// Shared page frame for every Control Center page.
//
// Why: before this, each page repeated the same ScrollView/ColumnLayout/heading block and each one invented
// its own way of reporting a failed CLI call (or forgot to report it at all - the Appearance page had no
// error path until 2026-11-13). One frame means one heading level, one refresh affordance, one readable
// error banner, and one place to change the page rhythm.
Item {
    id: page

    property string title: ""
    property string subtitle: ""
    /// The CLI bridge (context property from main.cpp, handed down by Main.qml).
    property var backend: null
    /// Empty when everything answered; a short localised sentence otherwise. Pages set this from their Fetcher.
    property string error: ""
    property bool showRefresh: true

    /// Page content; each `Card` lands in the body column.
    default property alias content: body.data

    /// Emitted by the header button. Every page reloads its own fetchers.
    signal refreshRequested()

    ScrollView {
        id: scroll
        anchors.fill: parent
        contentWidth: availableWidth

        ColumnLayout {
            width: page.width - 2 * Theme.space5
            x: Theme.space5
            spacing: Theme.space4

            Item { Layout.preferredHeight: Theme.space3 }

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.space3

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: Theme.space1

                    Text {
                        text: page.title
                        color: Theme.textPrimary
                        font.pixelSize: Theme.font2xl
                        font.bold: true
                        Layout.fillWidth: true
                        wrapMode: Text.Wrap
                        maximumLineCount: 2
                        elide: Text.ElideRight
                        Accessible.role: Accessible.Heading
                        Accessible.name: page.title
                    }
                    Text {
                        visible: page.subtitle !== ""
                        text: page.subtitle
                        color: Theme.textSecondary
                        font.pixelSize: Theme.fontSm
                        wrapMode: Text.Wrap
                        Layout.fillWidth: true
                        Accessible.name: page.subtitle
                    }
                }

                HcsButton {
                    visible: page.showRefresh
                    text: qsTr("Refresh")
                    Accessible.name: qsTr("Refresh this page")
                    onClicked: page.refreshRequested()
                }
            }

            // One error surface for the whole application: readable, labelled for screen readers, and never
            // the only thing on the page.
            Rectangle {
                id: banner
                visible: page.error !== ""
                Layout.fillWidth: true
                implicitHeight: bannerText.implicitHeight + 2 * Theme.space3
                color: Theme.surface2
                radius: Theme.radiusMd
                border.color: Theme.danger
                border.width: 1
                Accessible.role: Accessible.AlertMessage
                Accessible.name: page.error

                Text {
                    id: bannerText
                    anchors { left: parent.left; right: parent.right; top: parent.top; margins: Theme.space3 }
                    text: page.error
                    color: Theme.textPrimary
                    font.pixelSize: Theme.fontSm
                    wrapMode: Text.Wrap
                }
            }

            ColumnLayout {
                id: body
                Layout.fillWidth: true
                spacing: Theme.space4
            }

            Item { Layout.preferredHeight: Theme.space5 }
        }
    }
}
