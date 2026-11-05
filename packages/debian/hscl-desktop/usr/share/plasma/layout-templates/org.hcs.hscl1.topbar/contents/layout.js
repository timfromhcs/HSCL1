/*global Panel, gridUnit */
// HSCL1 top bar: launcher, global menu, centred clock, system tray. Slim (about 36 px at 100% scale).
const bar = new Panel;
bar.location = 'top';
bar.screen = 0;
bar.floating = 0;
bar.hiding = 'normal';
bar.height = Math.round(2 * gridUnit);

const launcher = bar.addWidget('org.kde.plasma.kickoff');
launcher.currentConfigGroup = ['Shortcuts'];
launcher.writeConfig('global', 'Alt+F1');
launcher.currentConfigGroup = ['General'];
launcher.writeConfig('icon', 'hscl1');
launcher.writeConfig('showAppsByName', 'true');

bar.addWidget('org.kde.plasma.appmenu');
bar.addWidget('org.kde.plasma.panelspacer');
const clock = bar.addWidget('org.kde.plasma.digitalclock');
clock.currentConfigGroup = ['Appearance'];
clock.writeConfig('showDate', 'true');
clock.writeConfig('showSeconds', 'false');
bar.addWidget('org.kde.plasma.panelspacer');
bar.addWidget('org.kde.plasma.systemtray');
