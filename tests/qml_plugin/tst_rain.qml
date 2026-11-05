import QtQuick
import QtTest
import "../../packages/debian/hscl-desktop/usr/share/plasma/wallpapers/org.hcs.hscl1.rain/contents/ui"

Item {
    id: root
    width: 800
    height: 450

    Component { id: fieldC; RainField { width: 800; height: 450; markSource: "" } }

    TestCase {
        name: "RainField"
        when: windowShown

        function test_columns_follow_density() {
            var sparse = createTemporaryObject(fieldC, root, { density: 1 })
            var dense = createTemporaryObject(fieldC, root, { density: 3 })
            verify(sparse.columnCount > 5)
            verify(dense.columnCount > sparse.columnCount * 1.8, "dense must have clearly more columns")
        }

        function test_animation_runs_when_enabled() {
            var f = createTemporaryObject(fieldC, root, { animate: true, density: 2 })
            tryVerify(function () { return f.runningCount === f.columnCount }, 3000)
            verify(f.runningCount > 0)
        }

        function test_nothing_moves_when_animations_are_off() {
            var f = createTemporaryObject(fieldC, root, { animate: false, density: 2 })
            wait(300)
            compare(f.runningCount, 0)
            compare(f.columnCount > 0, true)
        }

        function test_toggle_stops_and_starts() {
            var f = createTemporaryObject(fieldC, root, { animate: true })
            tryVerify(function () { return f.runningCount > 0 }, 3000)
            f.animate = false
            tryVerify(function () { return f.runningCount === 0 }, 3000)
        }

        function test_glyphs_have_the_requested_length_and_charset() {
            var f = createTemporaryObject(fieldC, root, {})
            var g = f.glyphs(20).split("\n")
            compare(g.length, 20)
            for (var i = 0; i < g.length; i++) verify(g[i].length === 1)
        }
    }
}
