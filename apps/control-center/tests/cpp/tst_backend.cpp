#include <QSignalSpy>
#include <QtTest>

#include "CliBackend.h"

class TstBackend : public QObject {
    Q_OBJECT
private slots:
    void allowsKnownCommands() {
        for (const auto &c : QList<QStringList>{{"status"}, {"doctor"}, {"system", "info"}, {"security", "status"},
                                                {"appearance", "theme", "list"}, {"appearance", "theme", "set", "hcs-nord"},
                                                {"appearance", "theme", "set", "hcs-nord", "--dry-run"},
                                                {"appearance", "theme", "show", "hcs-midnight"}})
            QVERIFY2(CliBackend::isAllowed(c), qPrintable(c.join(' ')));
    }
    void rejectsEverythingElse() {
        for (const auto &c : QList<QStringList>{{}, {"rm", "-rf", "/"}, {"status", "--output", "/etc/x"}, {"report"},
                                                {"appearance", "theme", "set", "../x"}, {"appearance", "theme", "set", "hcs-a;id"},
                                                {"appearance", "theme", "set", "hcs-nord", "--yes"},
                                                {"appearance", "theme", "show", "hcs-nord", "extra"},
                                                {"appearance", "theme", "set", "HCS-Nord"}, {"doctor", "--full"}})
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
