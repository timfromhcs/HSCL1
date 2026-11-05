import QtQuick
import ".."

// One CLI request whose result is exposed as properties. `backend` must provide request(id, args) and finished(...).
QtObject {
    id: f
    property var backend: null
    property var args: []
    property var result: null
    property bool loading: false
    property string error: ""
    readonly property string fid: "f" + Math.floor(Math.random() * 1e9)

    function reload() {
        if (!backend)
            return
        loading = true
        error = ""
        backend.request(fid, args)
    }

    property Connections conn: Connections {
        target: f.backend
        function onFinished(id, ok, data, err) {
            if (id !== f.fid)
                return
            f.loading = false
            if (ok) {
                f.result = data
                f.error = ""
            } else {
                f.error = err
            }
        }
    }
}
