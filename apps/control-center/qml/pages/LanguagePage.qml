import QtQuick
import QtQuick.Layouts
import ".."

HcsPage {
    id: page
    title: qsTr("Language & Region")
    subtitle: qsTr("The display language and where it comes from.")

    StateText { id: st }
    Fetcher { id: langFetch; backend: page.backend; args: ["language", "status"] }
    Component.onCompleted: langFetch.reload()

    error: langFetch.error !== "" ? qsTr("Could not read the language data") : ""
    onRefreshRequested: langFetch.reload()

    Card {
        title: qsTr("Language")
        Row2 {
            label: qsTr("Current language")
            value: langFetch.result ? langFetch.result.current_name + " (" + langFetch.result.current + ")" : (langFetch.error ? qsTr("Could not read data") : qsTr("Loading…"))
        }
        Row2 { label: qsTr("System default"); value: langFetch.result ? langFetch.result.system_default : "" }
        Row2 { label: qsTr("Plasma language"); value: langFetch.result && langFetch.result.plasma_language ? langFetch.result.plasma_language : "—" }
        Row2 {
            label: qsTr("Supported languages")
            value: langFetch.result && langFetch.result.supported ? langFetch.result.supported.join(", ") : ""
        }
    }

    Card {
        title: qsTr("Changing it")
        Text {
            text: qsTr("Use hscl language set en, de or fr. It writes the user configuration only; the new language applies to the next session. Nothing is changed from this page.")
            color: Theme.textSecondary
            font.pixelSize: Theme.fontSm
            wrapMode: Text.Wrap
            Layout.fillWidth: true
        }
    }
}
