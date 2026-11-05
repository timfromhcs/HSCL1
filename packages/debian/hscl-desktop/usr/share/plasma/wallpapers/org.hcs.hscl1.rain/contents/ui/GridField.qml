import QtQuick

// Grid pulse: a quiet grid with a bright band that sweeps across it.
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

    readonly property int cell: d === 1 ? 96 : d === 2 ? 64 : 44
    function countRunning() { return sweep.running ? 1 : 0 }

    Rectangle { anchors.fill: parent; color: field.background }
    Repeater {
        model: Math.ceil(field.width / field.cell)
        delegate: Rectangle { x: index * field.cell; width: 1; height: field.height; color: field.accent; opacity: 0.10 }
    }
    Repeater {
        model: Math.ceil(field.height / field.cell)
        delegate: Rectangle { y: index * field.cell; height: 1; width: field.width; color: field.accent; opacity: 0.10 }
    }
    Rectangle {
        id: band
        y: -height
        width: field.width
        height: field.height * 0.25
        opacity: 0.22
        gradient: Gradient {
            GradientStop { position: 0.0; color: "transparent" }
            GradientStop { position: 0.5; color: field.accent }
            GradientStop { position: 1.0; color: "transparent" }
        }
        SequentialAnimation on y {
            id: sweep
            running: field.animate
            loops: Animation.Infinite
            NumberAnimation { from: -band.height; to: field.height; duration: 9000 / field.tempo; easing.type: Easing.Linear }
            PauseAnimation { duration: 1500 }
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
        opacity: 0.09
    }
}
