#include "CliBackend.h"

#include <QJsonParseError>
#include <QRegularExpression>

CliBackend::CliBackend(QString executable, QObject *parent) : QObject(parent), m_exe(std::move(executable)) {}

bool CliBackend::isAllowed(const QStringList &a) {
    static const QRegularExpression themeId(QStringLiteral("^hcs-[a-z0-9]+(-[a-z0-9]+)*$"));
    static const QList<QStringList> fixed = {
        {"version"}, {"about"}, {"status"}, {"doctor"},
        {"system", "info"}, {"security", "status"}, {"ai", "detect"},
        {"appearance", "theme", "list"}, {"appearance", "theme", "current"}, {"appearance", "theme", "restore"},
    };
    if (fixed.contains(a))
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
