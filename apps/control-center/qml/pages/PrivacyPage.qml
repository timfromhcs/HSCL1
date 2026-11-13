import QtQuick
import QtQuick.Layouts
import ".."

HcsPage {
    id: page
    title: qsTr("Privacy")
    subtitle: qsTr("Session facts from hscl privacy status. This page makes no anonymity promise.")

    StateText { id: st }
    Fetcher { id: privFetch; backend: page.backend; args: ["privacy", "status"] }
    Component.onCompleted: privFetch.reload()

    error: privFetch.error !== "" ? qsTr("Could not read the privacy state") : ""
    onRefreshRequested: privFetch.reload()

    function diskCount() {
        if (!privFetch.result || !privFetch.result.internal_disks_automounted)
            return "—"
        var n = privFetch.result.internal_disks_automounted.length
        return n === 0 ? qsTr("none") : String(n)
    }

    Card {
        title: qsTr("Session")
        Row2 { label: qsTr("Ephemeral overlay"); value: privFetch.result ? st.flip(privFetch.result.ephemeral_overlay) : (privFetch.error ? qsTr("Could not read data") : qsTr("Loading…")) }
        Row2 { label: qsTr("Root filesystem"); value: privFetch.result ? privFetch.result.root_fstype : "" }
        Row2 { label: qsTr("Memory swap (zram)"); value: privFetch.result ? st.flip(privFetch.result.zram_swap_active) : "" }
        Row2 { label: qsTr("Persistent disk swap"); value: privFetch.result ? st.flip(privFetch.result.persistent_swap_active) : "" }
        Row2 { label: qsTr("Core dumps disabled"); value: privFetch.result ? st.flip(privFetch.result.suid_dumpable_disabled) : "" }
        Row2 { label: qsTr("Internal disks mounted"); value: privFetch.result ? page.diskCount() : "" }
    }

    Card {
        title: qsTr("Tor")
        Row2 { label: qsTr("Tor service"); value: privFetch.result ? st.flip(privFetch.result.tor_service_active) : "" }
        Row2 { label: qsTr("Tor Browser installed"); value: privFetch.result ? st.present(privFetch.result.tor_browser_installed) : "" }
    }

    Card {
        title: qsTr("What this is not")
        Text {
            text: qsTr("HSCL1 is not Tails. In the live session the root filesystem is ephemeral and internal disks stay unmounted, but network traffic is not filtered: this mode reports the session, it does not route it through Tor. Where strong anonymity matters, use the official Tails release.")
            color: Theme.textSecondary
            font.pixelSize: Theme.fontSm
            wrapMode: Text.Wrap
            Layout.fillWidth: true
        }
    }
}
