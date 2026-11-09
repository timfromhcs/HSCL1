import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import ".."

Item {
    id: page
    property var backend: null
    StateText { id: st }
    Fetcher { id: secFetch; backend: page.backend; args: ["security", "status"] }
    Fetcher { id: docFetch; backend: page.backend; args: ["doctor"] }
    Component.onCompleted: { secFetch.reload(); docFetch.reload() }

    function checkLabel(id) {
        switch (id) {
        case "arch": return qsTr("Architecture")
        case "memory": return qsTr("Memory")
        case "apparmor": return qsTr("AppArmor")
        case "firewall": return qsTr("Firewall")
        case "apt-sources": return qsTr("APT sources")
        case "secure-boot": return qsTr("Secure Boot")
        case "theme": return qsTr("Theme")
        default: return id
        }
    }

    ScrollView {
        anchors.fill: parent
        contentWidth: availableWidth
        ColumnLayout {
            width: page.width - 2 * Theme.space5
            x: Theme.space5
            spacing: Theme.space4
            Item { Layout.preferredHeight: Theme.space3 }
            Text { text: qsTr("Security"); color: Theme.textPrimary; font.pixelSize: Theme.font2xl; font.bold: true; Accessible.role: Accessible.Heading; Accessible.name: text }
            Card {
                title: qsTr("Status")
                Row2 { label: qsTr("Secure Boot"); value: secFetch.result ? st.label(secFetch.result.secure_boot) : (secFetch.error ? qsTr("Could not read data") : qsTr("Loading…")) }
                Row2 { label: qsTr("AppArmor"); value: secFetch.result ? st.label(secFetch.result.apparmor) : "" }
                Row2 { label: qsTr("Firewall"); value: secFetch.result ? st.label(secFetch.result.firewall_ufw_enabled) : "" }
                Row2 { label: qsTr("Unwanted APT sources"); value: secFetch.result ? (secFetch.result.forbidden_apt_sources.length === 0 ? qsTr("none") : secFetch.result.forbidden_apt_sources.join(", ")) : "" }
            }
            Card {
                title: qsTr("Health check")
                Repeater {
                    model: docFetch.result ? docFetch.result.checks : []
                    delegate: Row2 { label: page.checkLabel(modelData.id); value: st.label(modelData.level) + " - " + modelData.detail }
                }
            }
            Item { Layout.preferredHeight: Theme.space5 }
        }
    }
}
