import QtQuick 2.15

// HSCL1 installer page: what disk encryption does and does not do (AGENTS.md 6.3).
// Strings are English source text; German and French come from lang/calamares-hscl1_<lang>.qm (Calamares branding translations).
// The page object is created once at installer start, before the user picks a language, and is not retranslated by Calamares on its own
// (seen on screen 2026-11-07), so every text depends on `tick` and the page bumps it whenever it is shown.
Rectangle {
    id: page
    color: "#f0f1f2"

    property int tick: 0
    function retranslate() { page.tick = page.tick + 1 }
    function onActivate() { retranslate() }
    onVisibleChanged: if (visible) retranslate()
    onWidthChanged: retranslate()
    Component.onCompleted: retranslate()

    readonly property var lines: {
        page.tick
        return [
            qsTr("Encryption is off unless you tick \"Encrypt system\" on the next pages."),
            qsTr("With it on, your system partition is encrypted with LUKS2 and you type your passphrase at every start."),
            qsTr("Two small partitions stay readable without the passphrase: the EFI partition and a separate /boot partition (kernel and boot files, not your documents)."),
            qsTr("HSCL1 sets up exactly one passphrase and no recovery key. If you forget it, your data cannot be recovered. Write it down and keep it somewhere safe."),
            qsTr("Encryption protects a switched-off computer. It does not protect a running, unlocked one, and it does not replace backups.")
        ]
    }
    readonly property string heading: {
        page.tick
        return qsTr("Before you choose disk encryption")
    }

    Column {
        anchors.centerIn: parent
        width: Math.min(parent.width * 0.8, 760)
        spacing: 16

        Text {
            width: parent.width
            text: page.heading
            font.pixelSize: 24
            font.bold: true
            color: "#111418"
            wrapMode: Text.WordWrap
        }
        Repeater {
            model: page.lines
            Text {
                width: parent.width
                text: "•  " + modelData
                font.pixelSize: 16
                color: "#1c2128"
                wrapMode: Text.WordWrap
            }
        }
    }
}
