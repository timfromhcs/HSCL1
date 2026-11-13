import QtQuick
import QtQuick.Layouts
import ".."

HcsPage {
    id: page
    title: qsTr("About")

    Fetcher { id: verFetch; backend: page.backend; args: ["version"] }
    Component.onCompleted: verFetch.reload()

    error: verFetch.error !== "" ? qsTr("Could not read the version") : ""
    onRefreshRequested: verFetch.reload()

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
            text: qsTr("HSCL1 is not Tails and not an official Kali release. It is pre-alpha software.\nKALI LINUX™ is a trademark of OffSec. HSCL1 is not affiliated with or endorsed by the Tails project.")
            color: Theme.textSecondary
            font.pixelSize: Theme.fontSm
            wrapMode: Text.Wrap
            Layout.fillWidth: true
        }
    }
}
