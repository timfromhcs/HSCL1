import QtQuick
import QtQuick.Controls.Basic
import ".."

// Themed button. The Basic style's default button is a light rectangle that does not belong to the HCS
// palette at all (measured in the 2026-11-13 render of the Privacy page); every action in the panel now goes
// through this component so the surface, the border and the focus ring use the same tokens as the rest.
//
// `accent: true` is the primary action (Appearance → Apply). Everything else is a quiet secondary action.
Button {
    id: control
    property bool accent: false

    hoverEnabled: true
    Accessible.role: Accessible.Button
    implicitWidth: contentItem.implicitWidth + 2 * Theme.space4
    implicitHeight: Math.max(36, contentItem.implicitHeight + 2 * Theme.space2)

    contentItem: Text {
        text: control.text
        color: !control.enabled ? Theme.textMuted
             : control.accent ? Theme.textInverse : Theme.textPrimary
        font.pixelSize: Theme.fontSm
        font.bold: control.accent
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
        leftPadding: Theme.space4
        rightPadding: Theme.space4
    }

    background: Rectangle {
        radius: Theme.radiusMd
        color: control.accent
            ? (control.down ? Theme.accentPressed : (control.hovered ? Theme.accentHover : Theme.accent))
            : (control.down || control.hovered ? Theme.accentSoft : "transparent")
        border.width: control.visualFocus ? 2 : 1
        border.color: control.visualFocus ? Theme.focusRing : (control.accent ? "transparent" : Theme.borderStrong)
    }
}
