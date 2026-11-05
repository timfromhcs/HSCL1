import QtQuick
import QtTest
import "../../packages/debian/hscl-desktop/usr/share/plasma/wallpapers/org.hcs.hscl1.rain/contents/ui"

Item {
    id: root
    width: 640
    height: 360

    Component { id: starC; StarField { width: 640; height: 360; markSource: "" } }
    Component { id: auroraC; AuroraField { width: 640; height: 360; markSource: "" } }
    Component { id: gridC; GridField { width: 640; height: 360; markSource: "" } }

    TestCase {
        name: "Effects"
        when: windowShown

        function check(comp) {
            var on = createTemporaryObject(comp, root, { animate: true })
            tryVerify(function () { return on.runningCount > 0 }, 3000)
            var off = createTemporaryObject(comp, root, { animate: false })
            wait(300)
            compare(off.runningCount, 0, "nothing moves when animations are off")
            on.animate = false
            tryVerify(function () { return on.runningCount === 0 }, 3000)
        }

        function test_starfield() { check(starC) }
        function test_aurora() { check(auroraC) }
        function test_grid() { check(gridC) }

        function test_parameters_are_clamped() {
            var f = createTemporaryObject(starC, root, { density: 99, speed: -5 })
            compare(f.d, 3)
            compare(f.s, 1)
            var g = createTemporaryObject(gridC, root, { density: 0 })
            compare(g.d, 1)
        }

        function test_density_changes_star_count() {
            var a = createTemporaryObject(starC, root, { density: 1, animate: false })
            var b = createTemporaryObject(starC, root, { density: 3, animate: false })
            verify(b.children.length >= a.children.length)
        }
    }
}
