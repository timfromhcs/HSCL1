/*global loadTemplate, desktopsForActivity, currentActivity, getApiVersion */
// HCS Hybrid Desktop layout: HSCL1 number-rain wallpaper (static when animations are off), top bar and floating dock.
function setWallpaper(desktops) {
  for (let i = 0; i < desktops.length; i++) {
    desktops[i].wallpaperPlugin = 'org.hcs.hscl1.rain';
    desktops[i].currentConfigGroup = ['Wallpaper', 'org.hcs.hscl1.rain', 'General'];
    desktops[i].writeConfig('Density', 2);
    desktops[i].writeConfig('Speed', 2);
    desktops[i].writeConfig('ShowMark', true);
    // the still wallpaper stays available as the image plugin's default
    desktops[i].currentConfigGroup = ['Wallpaper', 'org.kde.image', 'General'];
    desktops[i].writeConfig('Image', 'file:///usr/share/wallpapers/HSCL1Midnight');
  }
}

getApiVersion(1);
loadTemplate('org.hcs.hscl1.topbar');
loadTemplate('org.hcs.hscl1.dock');
setWallpaper(desktopsForActivity(currentActivity()));
