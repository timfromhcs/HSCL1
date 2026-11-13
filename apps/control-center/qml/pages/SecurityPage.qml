pragma ComponentBehavior: Bound

import QtQuick
import ".."

HcsPage {
    id: page
    title: qsTr("Security")
    subtitle: qsTr("Posture from hscl security status and the checks hscl doctor runs.")

    StateText { id: st }
    Fetcher { id: secFetch; backend: page.backend; args: ["security", "status"] }
    Fetcher { id: docFetch; backend: page.backend; args: ["doctor"] }
    Component.onCompleted: { secFetch.reload(); docFetch.reload() }

    error: secFetch.error !== "" || docFetch.error !== ""
        ? qsTr("Could not read every value. The cards show what answered.") : ""

    onRefreshRequested: { secFetch.reload(); docFetch.reload() }

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
            delegate: Row2 {
                // declared so the model field reads resolve (Q-19)
                required property var modelData
                label: page.checkLabel(modelData.id)
                value: st.label(modelData.level) + " - " + modelData.detail
            }
        }
    }
}
