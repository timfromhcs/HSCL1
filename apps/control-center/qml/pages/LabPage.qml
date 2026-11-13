import QtQuick
import QtQuick.Layouts
import ".."

HcsPage {
    id: page
    title: qsTr("Security Lab")
    subtitle: qsTr("Authorized testing only. Kali tools run inside rootless containers, never from the host's package sources.")

    StateText { id: st }
    Fetcher { id: labFetch; backend: page.backend; args: ["lab", "status"] }
    Component.onCompleted: labFetch.reload()

    error: labFetch.error !== "" ? qsTr("Could not read the lab state") : ""
    onRefreshRequested: labFetch.reload()

    Card {
        title: qsTr("Container runtime")
        Row2 { label: qsTr("Podman installed"); value: labFetch.result ? st.present(labFetch.result.podman_installed) : (labFetch.error ? qsTr("Could not read data") : qsTr("Loading…")) }
        Row2 { label: qsTr("Lab folder"); value: labFetch.result ? labFetch.result.labs_root : "" }
        Row2 { label: qsTr("Folder exists"); value: labFetch.result ? st.present(labFetch.result.labs_root_exists) : "" }
        Row2 { label: qsTr("Default network"); value: labFetch.result && labFetch.result.defaults ? labFetch.result.defaults.network : "" }
    }

    Card {
        title: qsTr("Toolsets")
        Row2 {
            label: qsTr("Available toolsets")
            value: labFetch.result && labFetch.result.toolsets && labFetch.result.toolsets.length > 0
                ? labFetch.result.toolsets.join(", ")
                : qsTr("none")
        }
    }

    Card {
        title: qsTr("Boundaries")
        Text {
            text: qsTr("Nothing on this page starts a container, installs a tool or opens a shell. That stays in the terminal, where hscl lab asks for an attestation phrase first. Containers get no host home directory, no SSH agent and no device access by default.")
            color: Theme.textSecondary
            font.pixelSize: Theme.fontSm
            wrapMode: Text.Wrap
            Layout.fillWidth: true
        }
    }
}
