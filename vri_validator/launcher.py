"""Install a desktop launcher for the VRI Validator GUI."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from . import __version__

APP_NAME = "VRI Validator"
ICON_SRC = Path(__file__).resolve().parent / "data" / "vri-validator.png"


def _gui_executable(explicit: str | None) -> Path:
    if explicit:
        candidate = Path(explicit).expanduser()
    else:
        candidate = Path(sys.executable).with_name("vri-validate-gui")
        if not candidate.is_file():
            found = shutil.which("vri-validate-gui")
            if found is None:
                raise RuntimeError(
                    "vri-validate-gui was not found; pass --exe /path/to/vri-validate-gui"
                )
            candidate = Path(found)
    candidate = candidate.resolve()
    if not candidate.is_file():
        raise RuntimeError(f"GUI executable not found: {candidate}")
    return candidate


def install_launcher(exe: str | Path | None = None) -> tuple[Path, Path]:
    gui = _gui_executable(None if exe is None else str(exe))
    if not ICON_SRC.is_file():
        raise RuntimeError(f"bundled icon not found: {ICON_SRC}")

    data_home = Path.home() / ".local" / "share"
    icon_dir = data_home / "icons" / "hicolor" / "256x256" / "apps"
    desktop_dir = data_home / "applications"
    icon_dir.mkdir(parents=True, exist_ok=True)
    desktop_dir.mkdir(parents=True, exist_ok=True)

    icon = icon_dir / "vri-validator.png"
    shutil.copyfile(ICON_SRC, icon)

    desktop = desktop_dir / "vri-validator.desktop"
    desktop.write_text(
        "[Desktop Entry]\n"
        "Type=Application\n"
        f"Name={APP_NAME}\n"
        "Comment=Validate BC VRI/VRIMS personal geodatabases\n"
        f'Exec="{gui}"\n'
        f"Icon={icon}\n"
        "Terminal=false\n"
        "Categories=Utility;Science;\n"
        "StartupNotify=true\n",
        encoding="utf-8",
    )
    desktop.chmod(0o755)

    subprocess.run(
        ["update-desktop-database", str(desktop_dir)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    subprocess.run(
        ["gtk-update-icon-cache", "-f", "-t", str(data_home / "icons" / "hicolor")],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return desktop, icon


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="vri-validate-install-launcher",
        description="Add VRI Validator to the desktop application menu.",
    )
    parser.add_argument(
        "--exe",
        help="path to vri-validate-gui (default: next to the current Python or on PATH)",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = parser.parse_args(argv)
    try:
        desktop, icon = install_launcher(args.exe)
    except Exception as exc:  # noqa: BLE001 - reported to the user
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"Installed launcher: {desktop}")
    print(f"Icon: {icon}")
    print(f'Look for "{APP_NAME}" in your application menu.')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
