/*global loadTemplate, desktopsForActivity, currentActivity, getApiVersion */
// HCS Hybrid Desktop layout: HSCL1 Midnight wallpaper, top bar and floating dock.
function setWallpaper(desktops) {
  for (let i = 0; i < desktops.length; i++) {
    desktops[i].wallpaperPlugin = 'org.kde.image';
    desktops[i].currentConfigGroup = ['Wallpaper', 'org.kde.image', 'General'];
    desktops[i].writeConfig('Image', 'file:///usr/share/wallpapers/HSCL1Midnight');
  }
}

getApiVersion(1);
loadTemplate('org.hcs.hscl1.topbar');
loadTemplate('org.hcs.hscl1.dock');
setWallpaper(desktopsForActivity(currentActivity()));
