import QtQuick
import ".."

// Localised rendering of the CLI vocabulary (yes / no / unknown / pass / warn / fail / skip).
QtObject {
    function label(v) {
        switch (String(v)) {
        case "yes": return qsTr("yes")
        case "no": return qsTr("no")
        case "unknown": return qsTr("unknown")
        case "pass": return qsTr("pass")
        case "warn": return qsTr("warning")
        case "fail": return qsTr("fail")
        case "skip": return qsTr("skipped")
        default: return String(v)
        }
    }

    /// A boolean fact that is either on or off (overlay, swap, a service).
    function flip(v) {
        if (v === true) return qsTr("active")
        if (v === false) return qsTr("inactive")
        return qsTr("unknown")
    }

    /// A boolean fact that is present or absent (a package, a tool).
    function present(v) {
        if (v === true) return qsTr("yes")
        if (v === false) return qsTr("no")
        return qsTr("unknown")
    }

    /// The CLI's readiness vocabulary (`configured`, `not_configured`, `ready`, `partial`, `minimal`).
    function status(v) {
        switch (String(v)) {
        case "configured": return qsTr("configured")
        case "not_configured": return qsTr("not configured")
        case "ready": return qsTr("ready")
        case "partial": return qsTr("partial")
        case "minimal": return qsTr("minimal")
        default: return String(v)
        }
    }
}
