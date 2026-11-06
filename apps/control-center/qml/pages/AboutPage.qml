import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import ".."

Item {
    id: page
    property var backend: null
    Fetcher { id: verFetch; backend: page.backend; args: ["version"] }
    Component.onCompleted: verFetch.reload()

    ColumnLayout {
        anchors { fill: parent; margins: Theme.space5 }
        spacing: Theme.space4
        Text { text: qsTr("About"); color: Theme.textPrimary; font.pixelSize: Theme.font2xl; font.bold: true; Accessible.role: Accessible.Heading; Accessible.name: text }
        Card {
            title: "HSCL1"
            Text { text: "Hypercharged Supreme Computing Layout 1"; color: Theme.textSecondary; font.pixelSize: Theme.fontMd; wrapMode: Text.Wrap; Layout.fillWidth: true; Accessible.name: text }
            Row2 { label: qsTr("Version"); value: verFetch.result ? verFetch.result.version : "" }
            Row2 { label: qsTr("Publisher"); value: "HCSMEDIA" }
            Text {
                text: qsTr("Made with love by hcsmedia")
                color: Theme.textPrimary
                font.pixelSize: Theme.fontMd
            }
            Text {
                text: qsTr("HSCL1 is not Tails and not an official Kali release. It is pre-alpha software.")
                color: Theme.textSecondary
                font.pixelSize: Theme.fontSm
                wrapMode: Text.Wrap
                Layout.fillWidth: true
            }
        }
        Item { Layout.fillHeight: true }
    }
}
