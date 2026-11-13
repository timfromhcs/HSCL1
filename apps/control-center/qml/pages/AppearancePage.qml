pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import ".."

Item {
    id: page
    property var backend: null
    Fetcher { id: listFetch; backend: page.backend; args: ["appearance", "theme", "list"] }
    property string message: ""
    Component.onCompleted: listFetch.reload()

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

    ScrollView {
        anchors.fill: parent
        contentWidth: availableWidth
        ColumnLayout {
            width: page.width - 2 * Theme.space5
            x: Theme.space5
            spacing: Theme.space4
            Item { Layout.preferredHeight: Theme.space3 }
            Text { text: qsTr("Appearance"); color: Theme.textPrimary; font.pixelSize: Theme.font2xl; font.bold: true; Accessible.role: Accessible.Heading; Accessible.name: text }
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
                        }
                        Button {
                            text: qsTr("Preview")
                            Accessible.name: qsTr("Preview %1").arg(themeRow.modelData.title)
                            onClicked: page.backend.request("preview", ["appearance", "theme", "set", themeRow.modelData.id, "--dry-run"])
                        }
                        Button {
                            text: qsTr("Apply")
                            Accessible.name: qsTr("Apply %1").arg(themeRow.modelData.title)
                            onClicked: page.backend.request("apply", ["appearance", "theme", "set", themeRow.modelData.id])
                        }
                    }
                }
                Text {
                    visible: listFetch.error !== ""
                    text: qsTr("Could not read data")
                    color: Theme.danger
                    font.pixelSize: Theme.fontMd
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
            Item { Layout.preferredHeight: Theme.space5 }
        }
    }
}
