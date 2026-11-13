pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import ".."

HcsPage {
    id: page
    title: qsTr("Appearance")
    subtitle: qsTr("Themes shipped with HSCL1. Applying one changes the colour scheme and the wallpaper.")

    Fetcher { id: listFetch; backend: page.backend; args: ["appearance", "theme", "list"] }
    property string message: ""
    Component.onCompleted: listFetch.reload()

    error: listFetch.error !== "" ? qsTr("Could not read the theme list") : ""

    onRefreshRequested: listFetch.reload()

    Connections {
        target: page.backend
        function onFinished(id, ok, data, err) {
            if (id === "apply") {
                page.message = ok ? qsTr("Theme applied.") : qsTr("Could not apply the theme: %1").arg(err)
                listFetch.reload()
            } else if (id === "preview") {
                page.message = ok ? qsTr("Plan: %1").arg(data.plan.commands.map(function (c) { return c.join(" ") }).join("; ")) : err
            }
        }
    }

    Card {
        title: qsTr("Themes")
        Repeater {
            model: listFetch.result ? listFetch.result.themes : []
            delegate: RowLayout {
                id: themeRow
                // `required property` instead of the implicit model role: qmllint then resolves every use, and
                // the delegate is explicitly typed (Q-19).
                required property var modelData
                Layout.fillWidth: true
                spacing: Theme.space3
                Text {
                    text: themeRow.modelData.title + (listFetch.result.current === themeRow.modelData.id ? "  (" + qsTr("current") + ")" : "")
                    color: Theme.textPrimary
                    font.pixelSize: Theme.fontMd
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                }
                HcsButton {
                    text: qsTr("Preview")
                    Accessible.name: qsTr("Preview %1").arg(themeRow.modelData.title)
                    onClicked: page.backend.request("preview", ["appearance", "theme", "set", themeRow.modelData.id, "--dry-run"])
                }
                HcsButton {
                    text: qsTr("Apply")
                    accent: true
                    Accessible.name: qsTr("Apply %1").arg(themeRow.modelData.title)
                    onClicked: page.backend.request("apply", ["appearance", "theme", "set", themeRow.modelData.id])
                }
            }
        }
    }

    Text {
        visible: page.message !== ""
        text: page.message
        color: Theme.textSecondary
        font.pixelSize: Theme.fontSm
        wrapMode: Text.Wrap
        Layout.fillWidth: true
        Accessible.role: Accessible.AlertMessage
        Accessible.name: text
    }
}
