import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import ".."

Item {
    id: page
    property var backend: null
    StateText { id: st }
    property alias sys: sysFetch
    Fetcher { id: sysFetch; backend: page.backend; args: ["system", "info"] }
    Fetcher { id: secFetch; backend: page.backend; args: ["security", "status"] }
    Fetcher { id: docFetch; backend: page.backend; args: ["doctor"] }
    Component.onCompleted: { sysFetch.reload(); secFetch.reload(); docFetch.reload() }

    ScrollView {
        anchors.fill: parent
        contentWidth: availableWidth
        ColumnLayout {
            width: page.width - 2 * Theme.space5
            x: Theme.space5
            spacing: Theme.space4
            Item { Layout.preferredHeight: Theme.space3 }
            Text { text: qsTr("Overview"); color: Theme.textPrimary; font.pixelSize: Theme.font2xl; font.bold: true; Accessible.role: Accessible.Heading; Accessible.name: text }
            Card {
                title: qsTr("System")
                Row2 { label: qsTr("Operating system"); value: sysFetch.result ? sysFetch.result.os_pretty : (sysFetch.error ? qsTr("Could not read data") : qsTr("Loading…")) }
                Row2 { label: qsTr("Architecture"); value: sysFetch.result ? sysFetch.result.arch : "" }
                Row2 { label: qsTr("Kernel"); value: sysFetch.result ? sysFetch.result.kernel : "" }
                Row2 { label: qsTr("Memory"); value: sysFetch.result ? qsTr("%1 MiB").arg(sysFetch.result.mem_total_mib) : "" }
            }
            Card {
                title: qsTr("Security")
                Row2 { label: qsTr("Secure Boot"); value: secFetch.result ? st.label(secFetch.result.secure_boot) : "" }
                Row2 { label: qsTr("AppArmor"); value: secFetch.result ? st.label(secFetch.result.apparmor) : "" }
                Row2 { label: qsTr("Firewall"); value: secFetch.result ? st.label(secFetch.result.firewall_ufw_enabled) : "" }
            }
            Card {
                title: qsTr("Health check")
                Row2 { label: qsTr("Passed"); value: docFetch.result ? String(docFetch.result.passed) : "" }
                Row2 { label: qsTr("Warnings"); value: docFetch.result ? String(docFetch.result.warned) : "" }
                Row2 { label: qsTr("Failed"); value: docFetch.result ? String(docFetch.result.failed) : "" }
                Row2 { label: qsTr("Skipped"); value: docFetch.result ? String(docFetch.result.skipped) : "" }
            }
            Item { Layout.preferredHeight: Theme.space5 }
        }
    }
}
