import QtQuick

// Aurora ribbons: soft vertical-gradient bands that drift and breathe. No blur effect (cheap on weak GPUs).
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

    property color second: "#b07cff"
    function countRunning() {
        var n = 0
        for (var i = 0; i < bands.count; i++) {
            var it = bands.itemAt(i)
            if (it && it.drift.running) n++
        }
        return n
    }

    Rectangle { anchors.fill: parent; color: field.background }
    Repeater {
        id: bands
        model: 2 + field.d
        delegate: Rectangle {
            property alias drift: dr
            readonly property color tint: index % 2 === 0 ? field.accent : field.second
            width: field.width * 0.55
            height: field.height * 0.9
            x: field.width * (0.1 + 0.25 * index)
            y: field.height * 0.05
            radius: width / 2
            opacity: 0.16
            gradient: Gradient {
                GradientStop { position: 0.0; color: "transparent" }
                GradientStop { position: 0.45; color: tint }
                GradientStop { position: 1.0; color: "transparent" }
            }
            SequentialAnimation on x {
                id: dr
                running: field.animate
                loops: Animation.Infinite
                NumberAnimation { to: field.width * (0.25 + 0.2 * index); duration: (14000 + index * 2600) / field.tempo; easing.type: Easing.InOutSine }
                NumberAnimation { to: field.width * (0.05 + 0.2 * index); duration: (14000 + index * 3100) / field.tempo; easing.type: Easing.InOutSine }
            }
            SequentialAnimation on opacity {
                running: field.animate
                loops: Animation.Infinite
                NumberAnimation { to: 0.26; duration: 6000 / field.tempo; easing.type: Easing.InOutSine }
                NumberAnimation { to: 0.10; duration: 7000 / field.tempo; easing.type: Easing.InOutSine }
            }
        }
    }
    Image {
        visible: field.showMark
        anchors.centerIn: parent
        width: Math.min(parent.width, parent.height) * 0.30
        height: width
        source: field.markSource
        sourceSize.width: 512
        sourceSize.height: 512
        opacity: 0.10
    }
}
