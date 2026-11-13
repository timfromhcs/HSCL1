#include <QSignalSpy>
#include <QtTest>

#include "CliBackend.h"

class TstBackend : public QObject {
    Q_OBJECT
private slots:
    void allowsKnownCommands() {
        for (const auto &c : QList<QStringList>{{"status"}, {"doctor"}, {"system", "info"}, {"security", "status"},
                                                {"ai", "detect"},
                                                {"appearance", "theme", "list"}, {"appearance", "theme", "set", "hcs-nord"},
                                                {"appearance", "theme", "set", "hcs-nord", "--dry-run"},
                                                {"appearance", "theme", "show", "hcs-midnight"},
                                                // Pages added 2026-11-13: one read-only query each.
                                                {"privacy", "status"}, {"lab", "status"}, {"recovery", "status"},
                                                {"dev", "status"}, {"language", "status"},
                                                {"system", "updates", "--check"},
                                                // The Miner page needs these two; without them every request ended in
                                                // "command not allowed" and the page showed the red error banner even
                                                // with a healthy CLI (measured 2026-11-11 on rc6/rc7).
                                                {"miner", "status"}, {"miner", "probe", "192.168.178.61"},
                                                {"miner", "probe", "timsminer.local"}})
            QVERIFY2(CliBackend::isAllowed(c), qPrintable(c.join(' ')));
    }
    void rejectsEverythingElse() {
        for (const auto &c : QList<QStringList>{{}, {"rm", "-rf", "/"}, {"status", "--output", "/etc/x"}, {"report"},
                                                {"appearance", "theme", "set", "../x"}, {"appearance", "theme", "set", "hcs-a;id"},
                                                {"appearance", "theme", "set", "hcs-nord", "--yes"},
                                                {"appearance", "theme", "show", "hcs-nord", "extra"},
                                                {"appearance", "theme", "set", "HCS-Nord"}, {"doctor", "--full"},
                                                // A setter or an installer is never reachable through the bridge.
                                                {"system", "updates"}, {"system", "updates", "--install"},
                                                {"system", "updates", "--check", "extra"}, {"privacy", "tor"},
                                                {"privacy", "tails", "launch"}, {"lab", "run"},
                                                {"lab", "toolset", "install", "basic"}, {"dev", "setup"},
                                                {"language", "set", "de"}, {"recovery", "snapshots", "create"},
                                                {"miner", "probe"}, {"miner", "probe", "-oProxyCommand=x"},
                                                {"miner", "probe", "../../etc"}, {"miner", "ota", "1.2.3.4"}})
            QVERIFY2(!CliBackend::isAllowed(c), qPrintable(c.join(' ')));
    }
    void disallowedRequestFailsWithoutStartingAProcess() {
        CliBackend b(QStringLiteral("/nonexistent/hscl"));
        QSignalSpy spy(&b, &CliBackend::finished);
        b.request("x", {"rm", "-rf", "/"});
        QCOMPARE(spy.count(), 1);
        QCOMPARE(spy.at(0).at(1).toBool(), false);
        QCOMPARE(spy.at(0).at(3).toString(), QStringLiteral("command not allowed"));
    }
    void missingExecutableReportsError() {
        CliBackend b(QStringLiteral("/nonexistent/hscl"));
        QSignalSpy spy(&b, &CliBackend::finished);
        b.request("y", {"status"});
        QVERIFY(spy.wait(5000));
        QCOMPARE(spy.at(0).at(1).toBool(), false);
    }
};

QTEST_MAIN(TstBackend)
#include "tst_backend.moc"
