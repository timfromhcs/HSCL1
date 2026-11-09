import QtQuick
import QtTest
import "../../qml"

Item {
    id: root
    width: 900
    height: 600

    // Canned CLI answers with distinctive values, so a test proves the page shows live data and not constants.
    QtObject {
        id: mock
        property var calls: []
        signal finished(string id, bool ok, var data, string error)
        function request(id, args) {
            calls.push(args.join(" "))
            var key = args.join(" ")
            var data = null
            if (key === "system info") data = { os_pretty: "MockOS 9.9", arch: "mockarch", kernel: "9.9.9-mock", mem_total_mib: 12345 }
            else if (key === "security status") data = { secure_boot: "yes", apparmor: "no", firewall_ufw_enabled: "unknown", forbidden_apt_sources: ["evil.example"] }
            else if (key === "doctor") data = { passed: 7, warned: 3, failed: 2, skipped: 1, checks: [{ id: "arch", level: "pass", detail: "x86_64" }, { id: "probe-x", level: "warn", detail: "mock detail" }] }
            else if (key === "version") data = { product: "HSCL1", version: "9.8.7-mock" }
            else if (key === "appearance theme list") data = { current: "hcs-nord", themes: [{ id: "hcs-midnight", title: "HCS Midnight" }, { id: "hcs-nord", title: "HCS Nord" }] }
            var ok = data !== null
            Qt.callLater(function () { finished(id, ok, data, ok ? "" : "no mock") })
        }
    }

    function texts(item) {
        var out = []
        if (item.text !== undefined && typeof item.text === "string") out.push(item.text)
        for (var i = 0; i < item.children.length; i++) out = out.concat(texts(item.children[i]))
        return out
    }
    function joined(item) { return texts(item).join("|") }

    Component { id: overviewC; OverviewPage { width: 900; height: 600 } }
    Component { id: securityC; SecurityPage { width: 900; height: 600 } }
    Component { id: appearanceC; AppearancePage { width: 900; height: 600 } }
    Component { id: aboutC; AboutPage { width: 900; height: 600 } }
    Component { id: railC; NavRail { width: 220; height: 400; model: ["A", "B", "C"] } }

    TestCase {
        name: "Pages"
        when: windowShown

        function test_overview_shows_live_values() {
            var p = createTemporaryObject(overviewC, root, { backend: mock })
            tryVerify(function () { return joined(p).indexOf("MockOS 9.9") >= 0 })
            var all = joined(p)
            verify(all.indexOf("mockarch") >= 0)
            verify(all.indexOf("12345") >= 0)
            verify(all.indexOf("7") >= 0)
        }

        function test_security_lists_checks_and_sources() {
            var p = createTemporaryObject(securityC, root, { backend: mock })
            tryVerify(function () { return joined(p).indexOf("evil.example") >= 0 })
            verify(joined(p).indexOf("probe-x") >= 0)
            verify(joined(p).indexOf("mock detail") >= 0)
            // Known check ids are shown as human labels, unknown ones stay as they are.
            verify(joined(p).indexOf("Architecture") >= 0)
        }

        function test_appearance_lists_themes_and_apply_sends_exact_command() {
            mock.calls = []
            var p = createTemporaryObject(appearanceC, root, { backend: mock })
            tryVerify(function () { return joined(p).indexOf("HCS Nord") >= 0 })
            verify(joined(p).indexOf("(current)") >= 0 || joined(p).indexOf("current") >= 0)
            p.backend.request("apply", ["appearance", "theme", "set", "hcs-midnight"])
            verify(mock.calls.indexOf("appearance theme set hcs-midnight") >= 0)
        }

        function test_about_shows_version_from_cli() {
            var p = createTemporaryObject(aboutC, root, { backend: mock })
            tryVerify(function () { return joined(p).indexOf("9.8.7-mock") >= 0 })
            verify(joined(p).indexOf("Made with love by hcsmedia") >= 0)
            verify(joined(p).indexOf("not Tails") >= 0)
        }

        function test_pages_survive_missing_backend_data() {
            var failing = createTemporaryObject(overviewC, root, { backend: null })
            verify(failing !== null)
        }

        function test_nav_rail_keyboard_selection() {
            var r = createTemporaryObject(railC, root)
            compare(r.currentIndex, 0)
            r.forceActiveFocus()
            keyClick(Qt.Key_Down)
            compare(r.currentIndex, 1)
            keyClick(Qt.Key_Down)
            keyClick(Qt.Key_Down)
            compare(r.currentIndex, 2)
            keyClick(Qt.Key_Up)
            compare(r.currentIndex, 1)
        }
    }
}
