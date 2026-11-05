#!/usr/bin/env bash
# Generates wallpapers, logos, icons and os-release into $STAGE. Env: STAGE, ROOT, VERSION.
set -Eeuo pipefail
: "${STAGE:?}" "${ROOT:?}" "${VERSION:?}"

declare -A names=([hcs-midnight]=HSCL1Midnight [hcs-light]=HSCL1Light [hcs-nord]=HSCL1Nord [hcs-aurora]=HSCL1Aurora)
declare -A titles=([hcs-midnight]="HSCL1 Midnight" [hcs-light]="HSCL1 Light" [hcs-nord]="HSCL1 Nord" [hcs-aurora]="HSCL1 Aurora")
for theme in "${!names[@]}"; do
  d="$STAGE/usr/share/wallpapers/${names[$theme]}"
  mkdir -p "$d/contents/images"
  python3 "$ROOT/scripts/gen-wallpaper.py" "$d/contents/images/1920x1080.png" 1920 1080 "$theme" >/dev/null
  cat > "$d/metadata.json" <<JSON
{
  "KPlugin": {
    "Authors": [{ "Name": "HCSMEDIA" }],
    "Id": "${names[$theme]}",
    "License": "see NOTICE",
    "Name": "${titles[$theme]}"
  }
}
JSON
done

brand="$STAGE/usr/share/hscl/brand"
mkdir -p "$brand"
python3 "$ROOT/scripts/gen_brand.py" "$brand" >/dev/null
for s in 16 32 48 64 128 256 512; do
  install -D -m 0644 "$brand/hscl1-mark-$s.png" "$STAGE/usr/share/icons/hicolor/${s}x${s}/apps/hscl1.png"
done
install -D -m 0644 "$brand/hscl1-mark-dark.svg" "$STAGE/usr/share/icons/hicolor/scalable/apps/hscl1.svg"
install -D -m 0644 "$brand/hscl1-mark-128.png" "$STAGE/usr/share/pixmaps/hscl1.png"

# design tokens (read by `hscl appearance`) and Plasma colour schemes generated from them
install -D -m 0644 "$ROOT/themes/tokens/tokens.json" "$STAGE/usr/share/hscl/themes/tokens.json"
python3 "$ROOT/scripts/gen_colorschemes.py" "$STAGE/usr/share/color-schemes" >/dev/null

mkdir -p "$STAGE/usr/lib"
sed "s/@VERSION@/$VERSION/g" "$STAGE/os-release.in" > "$STAGE/usr/lib/os-release"
rm -f "$STAGE/os-release.in"
sed -i "s/\\S{VERSION}/$VERSION/" "$STAGE/etc/issue"
