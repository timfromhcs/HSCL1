/*global Panel, gridUnit, applicationExists */
// HSCL1 dock: centred, floating, icons only; pinned apps plus running windows. Never auto-hides by default.
const dock = new Panel;
dock.location = 'bottom';
dock.screen = 0;
dock.floating = 1;
dock.hiding = 'normal';
dock.alignment = 'center';
dock.height = Math.round(3.2 * gridUnit);
try {
  dock.lengthMode = 'fit';   // available in current Plasma 6; otherwise the fixed length below applies
} catch (e) {
  dock.minimumLength = Math.round(30 * gridUnit);
  dock.maximumLength = Math.round(30 * gridUnit);
}

const tasks = dock.addWidget('org.kde.plasma.icontasks');
const pinned = [
  'applications:org.kde.dolphin.desktop',
  'preferred://browser',
  'applications:org.kde.konsole.desktop',
  'applications:org.kde.discover.desktop',
  'applications:systemsettings.desktop'
];
if (applicationExists('hscl-handbook')) {
  pinned.push('applications:hscl-handbook.desktop');
}
if (applicationExists('hscl-control-center')) {
  pinned.push('applications:hscl-control-center.desktop');
}
tasks.currentConfigGroup = ['General'];
tasks.writeConfig('launchers', pinned);
dock.addWidget('org.kde.plasma.marginsseparator');
dock.addWidget('org.kde.plasma.trash');
