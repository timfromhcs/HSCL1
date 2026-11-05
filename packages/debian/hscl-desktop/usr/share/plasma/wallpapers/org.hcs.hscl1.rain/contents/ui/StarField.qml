import QtQuick

// Twinkling starfield. Pure QtQuick; stands still when `animate` is false.
Item {
    id: field
    property color background: "#0e1117"
    property color accent: "#6c8cff"
    property int density: 2          // 1..3
    property int speed: 2            // 1..3
    property bool animate: true
    property bool showMark: true
    property url markSource: "file:///usr/share/hscl/brand/hscl1-mark-dark.svg"
    readonly property int d: Math.max(1, Math.min(3, density))
    readonly property int s: Math.max(1, Math.min(3, speed))
    readonly property real tempo: s === 1 ? 0.6 : s === 2 ? 1.0 : 1.7
    readonly property int runningCount: countRunning()

    function countRunning() {
        var n = 0
        for (var i = 0; i < stars.count; i++) {
            var it = stars.itemAt(i)
            if (it && it.twinkle.running) n++
        }
        return n
    }

    Rectangle { anchors.fill: parent; color: field.background }
    Image {
        visible: field.showMark
        anchors.centerIn: parent
        width: Math.min(parent.width, parent.height) * 0.38
        height: width
        source: field.markSource
        sourceSize.width: 512
        sourceSize.height: 512
        opacity: 0.08
    }
    Repeater {
        id: stars
        model: 40 * field.d
        delegate: Rectangle {
            property alias twinkle: tw
            readonly property real size: 1 + ((index * 7) % 3)
            x: ((index * 7919) % 1000) / 1000 * field.width
            y: ((index * 104729) % 1000) / 1000 * field.height
            width: size
            height: size
            radius: size / 2
            color: index % 5 === 0 ? "#e8ecf3" : field.accent
            opacity: 0.25 + ((index * 13) % 6) * 0.1
            SequentialAnimation on opacity {
                id: tw
                running: field.animate
                loops: Animation.Infinite
                NumberAnimation { to: 0.95; duration: (1800 + (index * 311) % 3200) / field.tempo; easing.type: Easing.InOutSine }
                NumberAnimation { to: 0.15; duration: (1800 + (index * 523) % 3200) / field.tempo; easing.type: Easing.InOutSine }
            }
        }
    }
}
