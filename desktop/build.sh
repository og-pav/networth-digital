#!/bin/bash
# Build "NetWorth Routine.app" — a self-contained macOS app around the web files.
# Re-run after any change to index.html or assets/; the bundle carries its own copy.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$HERE")"
APP="$ROOT/dist/NetWorth Routine.app"
CONTENTS="$APP/Contents"

echo "==> cleaning"
rm -rf "$ROOT/dist"
mkdir -p "$CONTENTS/MacOS" "$CONTENTS/Resources/web"

echo "==> compiling"
clang -fobjc-arc -O2 \
  -o "$CONTENTS/MacOS/NetWorthRoutine" \
  "$HERE/main.m" \
  -framework Cocoa -framework WebKit

echo "==> copying web app"
cp "$ROOT/index.html" "$ROOT/manifest.webmanifest" "$ROOT/sw.js" "$CONTENTS/Resources/web/"
cp -R "$ROOT/assets" "$CONTENTS/Resources/web/assets"

echo "==> building icon"
ICONSET="$(mktemp -d)/AppIcon.iconset"
mkdir -p "$ICONSET"
for s in 16 32 64 128 256 512; do
  sips -z $s $s "$ROOT/assets/icon-1024.png" --out "$ICONSET/icon_${s}x${s}.png" >/dev/null
  d=$((s*2))
  sips -z $d $d "$ROOT/assets/icon-1024.png" --out "$ICONSET/icon_${s}x${s}@2x.png" >/dev/null
done
iconutil -c icns "$ICONSET" -o "$CONTENTS/Resources/AppIcon.icns"

echo "==> writing Info.plist"
cat > "$CONTENTS/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>NetWorth Routine</string>
  <key>CFBundleDisplayName</key><string>NetWorth Routine</string>
  <key>CFBundleExecutable</key><string>NetWorthRoutine</string>
  <key>CFBundleIdentifier</key><string>com.networthdigital.routine</string>
  <key>CFBundleIconFile</key><string>AppIcon</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>1.1</string>
  <key>CFBundleVersion</key><string>1</string>
  <key>LSMinimumSystemVersion</key><string>12.0</string>
  <key>NSHighResolutionCapable</key><true/>
  <key>LSApplicationCategoryType</key><string>public.app-category.productivity</string>
</dict>
</plist>
PLIST

echo "==> signing (ad-hoc, local use)"
codesign --force --deep --sign - "$APP" 2>/dev/null || echo "    (unsigned — still fine locally)"

echo
echo "Built: $APP"
echo "Install with:  cp -R \"$APP\" ~/Applications/"
