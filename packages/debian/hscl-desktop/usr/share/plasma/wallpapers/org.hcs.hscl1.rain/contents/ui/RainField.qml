import QtQuick

// Falling number rain. Pure QtQuick (no Plasma imports) so it can be tested on its own.
// When `animate` is false (the user turned animations off) nothing moves: a still HSCL1 frame is shown.
Item {
    id: field
    property color background: "#0e1117"
    property color glyphColor: "#6c8cff"
    property color headColor: "#e8ecf3"
    property int density: 2          // 1..3
    property int speed: 2            // 1..3
    property bool animate: true
    property bool showMark: true
    property url markSource: "file:///usr/share/hscl/brand/hscl1-mark-dark.svg"

    readonly property int fontPx: 16
    readonly property int columnWidth: Math.round(fontPx * (density === 1 ? 3.4 : density === 2 ? 2.2 : 1.5))
    readonly property int columnCount: Math.max(1, Math.floor(width / columnWidth))
    readonly property int glyphCount: Math.max(8, Math.floor(height / (fontPx * 1.15)) + 6)
    readonly property int runningCount: {
        var n = 0
        for (var i = 0; i < columns.count; i++) {
            var it = columns.itemAt(i)
            if (it && it.fall.running) n++
        }
        return n
    }

    function glyphs(n) {
        var set = "01234567890123456789ABCDEF01<>/{}"
        var s = ""
        for (var i = 0; i < n; i++) s += set.charAt(Math.floor(Math.random() * set.length)) + (i < n - 1 ? "\n" : "")
        return s
    }

    Rectangle { anchors.fill: parent; color: field.background }

    Image {
        visible: field.showMark
        anchors.centerIn: parent
        width: Math.min(parent.width, parent.height) * 0.42
        height: width
        source: field.markSource
        sourceSize.width: 512
        sourceSize.height: 512
        opacity: 0.07
        SequentialAnimation on opacity {
            running: field.animate && field.showMark
            loops: Animation.Infinite
            NumberAnimation { to: 0.13; duration: 4200; easing.type: Easing.InOutSine }
            NumberAnimation { to: 0.06; duration: 4200; easing.type: Easing.InOutSine }
        }
    }

    Repeater {
        id: columns
        model: field.columnCount
        delegate: Item {
            id: col
            property alias fall: fallAnim
            readonly property real tailLength: field.glyphCount * field.fontPx * 1.15
            x: index * field.columnWidth + 2
            width: field.columnWidth - 4
            height: field.height
            clip: true
            opacity: 0.35 + ((index * 37) % 5) * 0.12

            Text {
                id: txt
                width: parent.width
                y: field.animate ? -tailLength : field.height * (0.15 + ((index * 53) % 7) / 10)
                text: field.glyphs(field.glyphCount)
                color: field.glyphColor
                font.family: "monospace"
                font.pixelSize: field.fontPx
                lineHeight: 1.15
                horizontalAlignment: Text.AlignHCenter
                renderType: Text.QtRendering

                // fade the tail: transparent at the top, background colour overlay on the upper part of the block
                Rectangle {
                    anchors { left: parent.left; right: parent.right; top: parent.top }
                    height: parent.height * 0.8
                    gradient: Gradient {
                        GradientStop { position: 0.0; color: field.background }
                        GradientStop { position: 1.0; color: "transparent" }
                    }
                }
                // bright head glyph at the bottom of the block
                Text {
                    anchors { horizontalCenter: parent.horizontalCenter; bottom: parent.bottom }
                    text: txt.text.charAt(txt.text.length - 1)
                    color: field.headColor
                    font.family: "monospace"
                    font.pixelSize: field.fontPx
                }

                SequentialAnimation on y {
                    id: fallAnim
                    running: field.animate
                    loops: Animation.Infinite
                    PauseAnimation { duration: ((index * 977) % 5200) }
                    ScriptAction { script: txt.text = field.glyphs(field.glyphCount) }
                    NumberAnimation {
                        from: -col.tailLength
                        to: field.height
                        duration: (7000 + ((index * 1291) % 6000)) / (field.speed === 1 ? 0.6 : field.speed === 2 ? 1 : 1.7)
                        easing.type: Easing.Linear
                    }
                }
            }
        }
    }
}
