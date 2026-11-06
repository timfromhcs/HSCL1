/*
 *  SPDX-FileCopyrightText: 2026 HCSMEDIA
 *  SPDX-License-Identifier: GPL-3.0-or-later
 *
 *  First page of the Plasma Welcome Center on HSCL1 (replaces the upstream flavour page). Structure follows the upstream extra pages
 *  (GenericPage with heading and description) so it loads in the stock Welcome Center.
 */

import QtQuick
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

import org.kde.plasma.welcome

GenericPage {
    heading: i18nc("@info:window", "Welcome to HSCL1")
    description: i18nc("@info:usagetip",
    '<p><b>HSCL1 = Hypercharged Supreme Computing Layout 1.</b> A KDE Plasma desktop with a calm,
      keyboard-friendly layout, built by HCSMEDIA. Made with love by hcsmedia.</p>

    <ul>
      <li>No telemetry and no account needed</li>
      <li>Open the Control Center from the panel to change appearance, security and AI settings</li>
      <li>The HSCL1 Handbook on the desktop explains the three modes and what is tested</li>
      <li>Use <tt>hscl doctor</tt> in a terminal for a health report</li>
    </ul>

    <p>This is an early pre-release that has only been tested in virtual machines. HSCL1 is built on
    Ubuntu 26.04 LTS packages with KDE Plasma and is not an official product of Canonical or the
    Kubuntu project.</p>
    ');
}
