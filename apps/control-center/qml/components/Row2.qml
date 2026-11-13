import QtQuick
import QtQuick.Layouts
import ".."

RowLayout {
    id: row
    property string label: ""
    property string value: ""
    Layout.fillWidth: true
    spacing: Theme.space3
    Accessible.role: Accessible.StaticText
    Accessible.name: label + ": " + value
    // RowLayout sizes itself from implicit heights, and a wrapped Text reports the
    // height of one line. Without this the last health-check row is clipped by the Card.
    Layout.preferredHeight: Math.max(labelItem.implicitHeight, valueItem.contentHeight)
    Text {
        id: labelItem
        text: row.label
        color: Theme.textSecondary
        font.pixelSize: Theme.fontMd
        Layout.preferredWidth: 200
        // German labels ("Sicherungsordner vorhanden") are longer than the English ones; wrapping keeps the
        // meaning visible instead of clipping it at a fixed column width (measured 2026-11-13).
        wrapMode: Text.Wrap
    }
    Text {
        id: valueItem
        text: row.value
        color: Theme.textPrimary
        font.pixelSize: Theme.fontMd
        Layout.fillWidth: true
        wrapMode: Text.Wrap
    }
}
