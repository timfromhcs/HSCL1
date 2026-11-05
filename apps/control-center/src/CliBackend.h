#pragma once
#include <QJsonDocument>
#include <QObject>
#include <QProcess>
#include <QString>
#include <QStringList>
#include <QVariant>

// Runs the `hscl` CLI with --json and reports parsed results to QML.
// Only a closed set of commands is allowed; arguments are passed as a list (no shell, no free-form text).
class CliBackend : public QObject {
    Q_OBJECT
public:
    explicit CliBackend(QString executable = QStringLiteral("hscl"), QObject *parent = nullptr);

    // True when `args` is exactly one of the allowed command shapes.
    Q_INVOKABLE static bool isAllowed(const QStringList &args);
    // Starts the command asynchronously; the result arrives through finished().
    Q_INVOKABLE void request(const QString &id, const QStringList &args);

signals:
    void finished(const QString &id, bool ok, const QVariant &data, const QString &error);

private:
    QString m_exe;
};
