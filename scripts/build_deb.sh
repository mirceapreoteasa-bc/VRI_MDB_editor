#!/usr/bin/env bash
# Build the VRI Editor Debian package.
#   scripts/build_deb.sh [output_dir]   (default output: ~/Forest_MDB_editor)
# Installs to /opt/vri-editor (python packages + data) with a launcher in /usr/bin.
set -euo pipefail
SRC="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${1:-$HOME/Forest_MDB_editor}"
VERSION="$(sed -n 's/^__version__ = "\(.*\)"/\1/p' "$SRC/vri_editor/__init__.py")"
PKG="vri-editor"
STAGE="$(mktemp -d)"
ROOT="$STAGE/${PKG}_${VERSION}-1_all"
APP="$ROOT/opt/vri-editor"

mkdir -p "$ROOT/DEBIAN" "$APP" "$ROOT/usr/bin" "$ROOT/usr/share/applications" \
         "$ROOT/usr/share/icons/hicolor/256x256/apps" "$ROOT/usr/share/doc/$PKG"

# python packages (no caches, no build output) and shared data
copy_tree() {
  (cd "$1" && tar --exclude='__pycache__' --exclude='classes' --exclude='*.pyc' -cf - .) | (cd "$2" && tar -xf -)
}
mkdir -p "$APP/vri_editor" "$APP/vri_validator"
copy_tree "$SRC/vri_editor" "$APP/vri_editor"
copy_tree "$SRC/vri_validator" "$APP/vri_validator"
mkdir -p "$APP/data"
copy_tree "$SRC/data" "$APP/data"

# the Java helpers are compiled now, so the installed program needs only a JRE
CP="$(cd "$SRC" && python3 -c 'from vri_editor import db; print(db._classpath())' | sed "s#$SRC/vri_editor/data/classes##")"
mkdir -p "$APP/vri_editor/data/classes"
java -m jdk.compiler/com.sun.tools.javac.Main -cp "$CP" -d "$APP/vri_editor/data/classes" \
     "$APP/vri_editor/java/VriEdit.java" "$APP/vri_editor/java/VriDump.java"

# launcher, desktop entry, icon, licence note
cat > "$ROOT/usr/bin/vri-editor" <<'EOF'
#!/bin/sh
PYTHONPATH=/opt/vri-editor exec python3 -m vri_editor "$@"
EOF
chmod 755 "$ROOT/usr/bin/vri-editor"
cat > "$ROOT/usr/share/applications/vri-editor.desktop" <<EOF
[Desktop Entry]
Name=VRI Editor
Comment=Native editor for BC VRI/VRIMS personal geodatabases
Exec=vri-editor %F
Icon=vri-editor
Terminal=false
Type=Application
Categories=Science;Geography;
MimeType=application/x-msaccess;
EOF
cp "$SRC/vri_validator/data/vri-validator.png" "$ROOT/usr/share/icons/hicolor/256x256/apps/vri-editor.png"
cat > "$ROOT/usr/share/doc/$PKG/copyright" <<EOF
VRI Editor $VERSION - internal tool for BC VRI/VRIMS map editing.
Third-party: Jackcess (Apache 2.0), Apache Commons Lang/Logging (Apache 2.0),
GDAL/OGR (MIT/X), Ministry Sindex DLL v1.54 data (table generated with SiteToolsCmd).
EOF

# remove stale bytecode and make sure the tree is readable
find "$APP" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
chmod -R a+rX "$APP"

INSTALLED_KB="$(du -sk "$ROOT" | cut -f1)"
cat > "$ROOT/DEBIAN/control" <<EOF
Package: $PKG
Version: $VERSION-1
Section: science
Priority: optional
Architecture: all
Installed-Size: $INSTALLED_KB
Maintainer: VRI Editor contributors <noreply@localhost>
Depends: python3 (>= 3.10), python3-pyqt5, python3-gdal, mdbtools, default-jre-headless | java-runtime-headless
Description: VRI/VRIMS map editor (native Linux)
 Opens, creates and edits BC Vegetation Resources Inventory personal geodatabases
 (_VRIMS.mdb): classification form, validation warnings, RESULTS import, spatial
 import, site index and basal area estimates, GeoPackage and shapefile export.
 Each map opens in its own window. Writes keep a backup of the previous file.
EOF

mkdir -p "$OUT"
DEB="$OUT/${PKG}_${VERSION}-1_all.deb"
dpkg-deb --root-owner-group --build "$ROOT" "$DEB" >/dev/null
rm -rf "$STAGE"
echo "built $DEB"
