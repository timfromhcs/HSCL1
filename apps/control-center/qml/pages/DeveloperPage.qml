import QtQuick
import QtQuick.Layouts
import ".."

HcsPage {
    id: page
    title: qsTr("Developer")
    subtitle: qsTr("Detected toolchain, containers and virtualization support.")

    StateText { id: st }
    Fetcher { id: devFetch; backend: page.backend; args: ["dev", "status"] }
    Component.onCompleted: devFetch.reload()

    error: devFetch.error !== "" ? qsTr("Could not read the developer data") : ""
    onRefreshRequested: devFetch.reload()

    Card {
        title: qsTr("Toolchain")
        Row2 { label: qsTr("Git"); value: devFetch.result ? st.present(devFetch.result.git_ready) : (devFetch.error ? qsTr("Could not read data") : qsTr("Loading…")) }
        Row2 { label: qsTr("Rust"); value: devFetch.result ? st.present(devFetch.result.rust_ready) : "" }
        Row2 { label: qsTr("Python"); value: devFetch.result ? st.present(devFetch.result.python_ready) : "" }
        Row2 { label: qsTr("Node.js"); value: devFetch.result ? st.present(devFetch.result.node_ready) : "" }
        Row2 { label: qsTr("Compilers"); value: devFetch.result ? st.present(devFetch.result.compilers_ready) : "" }
        Row2 { label: qsTr("Containers"); value: devFetch.result ? st.present(devFetch.result.containers_ready) : "" }
        Row2 { label: qsTr("Virtualization"); value: devFetch.result ? st.present(devFetch.result.virt_ready) : "" }
    }

    Card {
        title: qsTr("Details")
        Row2 {
            label: qsTr("Missing recommended")
            value: devFetch.result && devFetch.result.missing_recommended && devFetch.result.missing_recommended.length > 0
                ? devFetch.result.missing_recommended.join(", ")
                : qsTr("none")
        }
        Row2 {
            label: qsTr("Installed tools")
            value: devFetch.result && devFetch.result.installed_tools
                ? devFetch.result.installed_tools.filter(function (t) { return t.present }).map(function (t) { return t.name }).join(", ")
                : ""
        }
    }
}
