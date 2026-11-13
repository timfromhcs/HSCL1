import QtQuick
import ".."

HcsPage {
    id: page
    title: qsTr("Overview")
    subtitle: qsTr("Live system, security and health values from hscl.")

    StateText { id: st }
    property alias sys: sysFetch
    Fetcher { id: sysFetch; backend: page.backend; args: ["system", "info"] }
    Fetcher { id: secFetch; backend: page.backend; args: ["security", "status"] }
    Fetcher { id: docFetch; backend: page.backend; args: ["doctor"] }
    Component.onCompleted: { sysFetch.reload(); secFetch.reload(); docFetch.reload() }

    error: sysFetch.error !== "" || secFetch.error !== "" || docFetch.error !== ""
        ? qsTr("Could not read every value. The cards show what answered.") : ""

    onRefreshRequested: { sysFetch.reload(); secFetch.reload(); docFetch.reload() }

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
}
