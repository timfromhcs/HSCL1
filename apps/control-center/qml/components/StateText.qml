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
}
