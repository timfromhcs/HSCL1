#include <QCoreApplication>
#include <QDir>
#include <QGuiApplication>
#include <QLocale>
#include <QQmlApplicationEngine>
#include <QQmlContext>
#include <QQuickStyle>
#include <QTranslator>

#include "CliBackend.h"

static QString envOr(const char *name, const QString &fallback) {
    const QByteArray v = qgetenv(name);
    return v.isEmpty() ? fallback : QString::fromLocal8Bit(v);
}

int main(int argc, char *argv[]) {
    QGuiApplication app(argc, argv);
    app.setApplicationName(QStringLiteral("hscl-control-center"));
    app.setOrganizationName(QStringLiteral("HCSMEDIA"));
    QQuickStyle::setStyle(QStringLiteral("Basic"));

    const QString base = QStringLiteral("/usr/share/hscl/control-center");
    const QString qmlDir = envOr("HSCL_CC_QML", base + QStringLiteral("/qml"));
    const QString i18nDir = envOr("HSCL_CC_I18N", base + QStringLiteral("/i18n"));

    QTranslator translator;
    if (translator.load(QLocale(), QStringLiteral("hscl-cc"), QStringLiteral("_"), i18nDir))
        app.installTranslator(&translator);

    CliBackend backend(envOr("HSCL_BIN", QStringLiteral("hscl")));
    QQmlApplicationEngine engine;
    engine.addImportPath(qmlDir);
    engine.rootContext()->setContextProperty(QStringLiteral("backend"), &backend);
    engine.load(QUrl::fromLocalFile(qmlDir + QStringLiteral("/Main.qml")));
    if (engine.rootObjects().isEmpty())
        return 1;
    return app.exec();
}
