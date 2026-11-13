#include "CliBackend.h"

#include <QJsonParseError>
#include <QRegularExpression>

CliBackend::CliBackend(QString executable, QObject *parent) : QObject(parent), m_exe(std::move(executable)) {}

bool CliBackend::isAllowed(const QStringList &a) {
    static const QRegularExpression themeId(QStringLiteral("^hcs-[a-z0-9]+(-[a-z0-9]+)*$"));
    // A device address as the CLI reports it: an IPv4 literal or a plain hostname. No spaces, no slashes, no
    // leading '-', so an allowed probe cannot turn into an option or a path.
    static const QRegularExpression deviceHost(QStringLiteral("^[A-Za-z0-9][A-Za-z0-9.-]{0,63}$"));
    static const QList<QStringList> fixed = {
        {"version"}, {"about"}, {"status"}, {"doctor"},
        {"system", "info"}, {"security", "status"}, {"ai", "detect"},
        {"appearance", "theme", "list"}, {"appearance", "theme", "current"}, {"appearance", "theme", "restore"},
        // The pages added on 2026-11-13 are strictly read-only: a status/JSON query each, never a setter.
        {"privacy", "status"}, {"lab", "status"}, {"recovery", "status"},
        {"dev", "status"}, {"language", "status"},
        // A read-only apt simulation (`--check`), not `--install`.
        {"system", "updates", "--check"},
        // The Miner page reads the last device and probes it read-only; without these it could only ever show its
        // error banner (measured 2026-11-11).
        {"miner", "status"},
    };
    if (fixed.contains(a))
        return true;
    if (a.size() == 3 && a[0] == "miner" && a[1] == "probe" && deviceHost.match(a[2]).hasMatch())
        return true;
    auto validId = [&](const QString &s) { return s.size() <= 24 && themeId.match(s).hasMatch(); };
    if (a.size() >= 4 && a[0] == "appearance" && a[1] == "theme" && (a[2] == "show" || a[2] == "set") && validId(a[3])) {
        if (a.size() == 4)
            return true;
        return a.size() == 5 && a[2] == "set" && a[4] == "--dry-run";
    }
    return false;
}

void CliBackend::request(const QString &id, const QStringList &args) {
    if (!isAllowed(args)) {
        emit finished(id, false, QVariant(), QStringLiteral("command not allowed"));
        return;
    }
    auto *p = new QProcess(this);
    connect(p, &QProcess::errorOccurred, this, [this, p, id](QProcess::ProcessError e) {
        if (e == QProcess::FailedToStart) {
            emit finished(id, false, QVariant(), QStringLiteral("cannot start hscl"));
            p->deleteLater();
        }
    });
    connect(p, &QProcess::finished, this, [this, p, id](int, QProcess::ExitStatus) {
        QJsonParseError err;
        const QJsonDocument doc = QJsonDocument::fromJson(p->readAllStandardOutput(), &err);
        if (err.error == QJsonParseError::NoError)
            emit finished(id, true, doc.toVariant(), QString());
        else
            emit finished(id, false, QVariant(), QString::fromUtf8(p->readAllStandardError()).trimmed());
        p->deleteLater();
    });
    QStringList full = args;
    full << QStringLiteral("--json");
    p->start(m_exe, full);
}
