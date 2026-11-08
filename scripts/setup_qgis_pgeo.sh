#!/usr/bin/env bash
set -euo pipefail

DRIVER_DIR="${DRIVER_DIR:-$HOME/.local/lib/odbc}"
ODBCINST="${ODBCINST:-$HOME/.odbcinst.ini}"
WRAPPER="$HOME/bin/qgis"
ENV_FILE="$HOME/.config/environment.d/90-qgis-pgeo.conf"
SYSTEM_DESKTOP="/usr/share/applications/org.qgis.qgis.desktop"
USER_DESKTOP="$HOME/.local/share/applications/org.qgis.qgis.desktop"
TEST_DB="${1:-$HOME/DOCUMENTE/QGISDATAbase/k50/093k050_VRIMS.mdb}"

mkdir -p "$DRIVER_DIR" "$HOME/bin" "$(dirname "$ENV_FILE")" "$(dirname "$USER_DESKTOP")"

find_driver() {
    local candidate
    for candidate in \
        "$DRIVER_DIR/libmdbodbc.so" \
        /usr/lib/x86_64-linux-gnu/odbc/libmdbodbc.so \
        /usr/lib64/odbc/libmdbodbc.so; do
        if [ -f "$candidate" ]; then
            printf '%s\n' "$candidate"
            return 0
        fi
    done
    return 1
}

if ! find_driver >/dev/null; then
    tmp="$(mktemp -d)"
    trap 'rm -rf "$tmp"' EXIT
    (cd "$tmp" && apt-get download odbc-mdbtools >/dev/null)
    deb="$(find "$tmp" -maxdepth 1 -name 'odbc-mdbtools*.deb' -print -quit)"
    dpkg-deb -x "$deb" "$tmp/root"
    install -m 0644 "$tmp/root/usr/lib/x86_64-linux-gnu/odbc/libmdbodbc.so" "$DRIVER_DIR/libmdbodbc.so"
    install -m 0644 "$tmp/root/usr/lib/x86_64-linux-gnu/odbc/libmdbodbcW.so" "$DRIVER_DIR/libmdbodbcW.so"
fi

driver="$(find_driver)"
touch "$ODBCINST"
for section in "MDB Tools" "Microsoft Access Driver (*.mdb, *.accdb)" "Microsoft Access Driver (*.mdb)"; do
    if ! grep -Fqx "[$section]" "$ODBCINST"; then
        {
            printf '\n[%s]\n' "$section"
            printf 'Description=MDB Tools ODBC driver\n'
            printf 'Driver=%s\n' "$driver"
            printf 'FileUsage=1\n'
        } >> "$ODBCINST"
    fi
done

cat > "$WRAPPER" <<WRAP
#!/usr/bin/env bash
set -euo pipefail
export MDBDRIVER_PATH="\${MDBDRIVER_PATH:-$driver}"
exec /usr/bin/qgis "\$@"
WRAP
chmod 0755 "$WRAPPER"

printf 'MDBDRIVER_PATH=%s\n' "$driver" > "$ENV_FILE"

if [ -f "$SYSTEM_DESKTOP" ]; then
    cp "$SYSTEM_DESKTOP" "$USER_DESKTOP"
    sed -i "s|^TryExec=qgis|TryExec=$WRAPPER|; s|^Exec=qgis %F|Exec=$WRAPPER %F|" "$USER_DESKTOP"
fi

MDBDRIVER_PATH="$driver" ogrinfo -ro -so "$TEST_DB" >/dev/null
printf 'QGIS PGeo ready: %s\n' "$driver"
printf 'Launcher: %s\n' "$WRAPPER"
printf 'Test database opened read-only: %s\n' "$TEST_DB"
