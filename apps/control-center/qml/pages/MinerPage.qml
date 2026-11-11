import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import ".."

Item {
    id: page
    property var backend: null
    StateText { id: st }
    property string device: ""
    Fetcher { id: statusFetch; backend: page.backend; args: ["miner", "status"] }
    Fetcher { id: probeFetch; backend: page.backend; args: [] }
    Component.onCompleted: statusFetch.reload()

    Connections {
        target: statusFetch
        function onResultChanged() {
            if (statusFetch.result && statusFetch.result.last_device) {
                page.device = statusFetch.result.last_device
                probeFetch.args = ["miner", "probe", page.device]
                probeFetch.reload()
            }
        }
    }

    function number(value, digits) {
        return value === undefined || value === null ? "—" : Number(value).toFixed(digits)
    }

    ScrollView {
        anchors.fill: parent
        contentWidth: availableWidth
        ColumnLayout {
            width: page.width - 2 * Theme.space5
            x: Theme.space5
            spacing: Theme.space4
            Item { Layout.preferredHeight: Theme.space3 }
            Text { text: qsTr("Miner"); color: Theme.textPrimary; font.pixelSize: Theme.font2xl; font.bold: true; Accessible.role: Accessible.Heading; Accessible.name: text }
            Text {
                text: qsTr("Read-only view of the miner this workspace last contacted. Nothing is configured here.")
                color: Theme.textSecondary
                font.pixelSize: Theme.fontSm
                wrapMode: Text.Wrap
                Layout.fillWidth: true
            }
            Card {
                title: qsTr("Device")
                Row2 { label: qsTr("Address"); value: page.device !== "" ? page.device : qsTr("No device configured") }
                Row2 { label: qsTr("Hostname"); value: probeFetch.result && probeFetch.result.hostname ? probeFetch.result.hostname : "—" }
                Row2 { label: qsTr("Board"); value: probeFetch.result && probeFetch.result.board_version ? probeFetch.result.board_version + " / " + (probeFetch.result.asic || "—") : "—" }
                Row2 { label: qsTr("Firmware"); value: probeFetch.result && probeFetch.result.firmware ? probeFetch.result.firmware : "—" }
            }
            Card {
                title: qsTr("Mining")
                Row2 { label: qsTr("Hashrate"); value: page.number(probeFetch.result ? probeFetch.result.hash_rate : null, 1) + " GH/s" }
                Row2 { label: qsTr("Temperature"); value: page.number(probeFetch.result ? probeFetch.result.temp_c : null, 0) + " °C" }
                Row2 { label: qsTr("Power"); value: page.number(probeFetch.result ? probeFetch.result.power_w : null, 2) + " W" }
                Row2 {
                    label: qsTr("Shares")
                    value: probeFetch.result && probeFetch.result.shares_accepted !== null && probeFetch.result.shares_accepted !== undefined
                        ? probeFetch.result.shares_accepted + " / " + probeFetch.result.shares_rejected
                        : "—"
                }
                Row2 {
                    label: qsTr("Pool")
                    value: probeFetch.result && probeFetch.result.pool_url ? probeFetch.result.pool_url + ":" + probeFetch.result.pool_port : "—"
                }
            }
            Text {
                visible: statusFetch.error !== ""
                text: qsTr("Could not read miner data")
                color: Theme.danger
                font.pixelSize: Theme.fontMd
            }
            Text {
                // A fresh system has no miner, and that is not an error: say what to do instead of painting the
                // page red. Measured 2026-11-11 in the rc6 guest: with no device configured the page showed
                // "Could not read miner data" in red, although `hscl miner status --json` answers fine with
                // `last_device: null`.
                visible: statusFetch.error === "" && page.device === ""
                text: qsTr("No miner configured. Nothing is contacted until you add one.")
                color: Theme.textSecondary
                font.pixelSize: Theme.fontMd
                wrapMode: Text.Wrap
                Layout.fillWidth: true
            }
            Button {
                text: qsTr("Refresh")
                Accessible.name: qsTr("Refresh miner data")
                onClicked: statusFetch.reload()
            }
            Item { Layout.preferredHeight: Theme.space5 }
        }
    }
}
