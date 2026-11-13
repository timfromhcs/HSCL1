import QtQuick
import QtQuick.Layouts
import ".."

HcsPage {
    id: page
    title: qsTr("Updates & Recovery")
    subtitle: qsTr("Read-only checks. Nothing is downloaded, installed or changed here.")

    StateText { id: st }
    Fetcher { id: updFetch; backend: page.backend; args: ["system", "updates", "--check"] }
    Fetcher { id: recFetch; backend: page.backend; args: ["recovery", "status"] }
    Component.onCompleted: { updFetch.reload(); recFetch.reload() }

    error: updFetch.error !== "" || recFetch.error !== ""
        ? qsTr("Could not read every value. The cards show what answered.") : ""

    onRefreshRequested: { updFetch.reload(); recFetch.reload() }

    function listAge() {
        if (!updFetch.result || updFetch.result.lists_age_days === null || updFetch.result.lists_age_days === undefined)
            return "—"
        return String(updFetch.result.lists_age_days)
    }

    Card {
        title: qsTr("Packages")
        Row2 { label: qsTr("Upgradable"); value: updFetch.result ? String(updFetch.result.upgradable) : (updFetch.error ? qsTr("Could not read data") : qsTr("Loading…")) }
        Row2 { label: qsTr("Security updates"); value: updFetch.result ? String(updFetch.result.security) : "" }
        Row2 { label: qsTr("New packages"); value: updFetch.result ? String(updFetch.result.new_packages) : "" }
        Row2 { label: qsTr("To remove"); value: updFetch.result ? String(updFetch.result.to_remove) : "" }
        Row2 { label: qsTr("Reboot required"); value: updFetch.result ? st.present(updFetch.result.reboot_required) : "" }
        Row2 { label: qsTr("Package lists stale"); value: updFetch.result ? st.present(updFetch.result.lists_stale) : "" }
        Row2 { label: qsTr("Lists age (days)"); value: updFetch.result ? page.listAge() : "" }
    }

    Text {
        visible: updFetch.result !== null && updFetch.result.lists_stale === true
        text: qsTr("The package lists are stale or missing, so these counts say nothing about what is available upstream. Run sudo apt update first.")
        color: Theme.textSecondary
        font.pixelSize: Theme.fontSm
        wrapMode: Text.Wrap
        Layout.fillWidth: true
    }

    Card {
        title: qsTr("Recovery")
        Row2 { label: qsTr("Readiness"); value: recFetch.result ? st.status(recFetch.result.readiness) : (recFetch.error ? qsTr("Could not read data") : qsTr("Loading…")) }
        Row2 { label: qsTr("Snapshots found"); value: recFetch.result ? String(recFetch.result.snapshots_found) : "" }
        Row2 { label: qsTr("Timeshift detected"); value: recFetch.result ? st.present(recFetch.result.timeshift_detected) : "" }
        Row2 { label: qsTr("Snapper detected"); value: recFetch.result ? st.present(recFetch.result.snapper_detected) : "" }
        Row2 { label: qsTr("Backup directory exists"); value: recFetch.result ? st.present(recFetch.result.backup_dir_exists) : "" }
    }
}
