import QtQuick
import QtQuick.Layouts
import ".."

HcsPage {
    id: page
    title: qsTr("Local AI")
    subtitle: qsTr("Hardware detection only. A GPU backend counts as verified only after a real inference run.")

    StateText { id: st }
    Fetcher { id: aiFetch; backend: page.backend; args: ["ai", "detect"] }
    Component.onCompleted: aiFetch.reload()

    error: aiFetch.error !== "" ? qsTr("Could not read the hardware data") : ""
    onRefreshRequested: aiFetch.reload()

    function count(list) {
        return list && list.length !== undefined ? String(list.length) : "—"
    }

    Card {
        title: qsTr("Hardware")
        Row2 { label: qsTr("CPU threads"); value: aiFetch.result ? String(aiFetch.result.cpu_threads) : (aiFetch.error ? qsTr("Could not read data") : qsTr("Loading…")) }
        Row2 { label: qsTr("Memory"); value: aiFetch.result ? qsTr("%1 MiB").arg(aiFetch.result.mem_total_mib) : "" }
        Row2 { label: qsTr("GPUs detected"); value: aiFetch.result ? page.count(aiFetch.result.gpus) : "" }
        Row2 { label: qsTr("Vulkan ICD files"); value: aiFetch.result ? page.count(aiFetch.result.vulkan_icd_files) : "" }
        Row2 { label: qsTr("GPU acceleration verified"); value: aiFetch.result ? st.present(aiFetch.result.gpu_acceleration_verified) : "" }
    }

    Card {
        title: qsTr("Recommendation")
        Row2 { label: qsTr("Backend"); value: aiFetch.result ? aiFetch.result.recommended_backend : "" }
        Text {
            text: qsTr("CPU inference is the safe fallback. No model, download or server is configured from this page.")
            color: Theme.textSecondary
            font.pixelSize: Theme.fontSm
            wrapMode: Text.Wrap
            Layout.fillWidth: true
        }
    }
}
