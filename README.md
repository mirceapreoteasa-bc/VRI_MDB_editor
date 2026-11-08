# VRI MDB Validator

Validator for BC VRI / VRIMS personal geodatabases (`.mdb`). It reads the attribute
tables with `mdbtools`, joins them by `FOREST_COVER_OBJECT_ID`, applies the rules from
the *VRIMS Vegetation Cover Polygon Validation Rules V2.0.0*, and writes an HTML and/or
CSV report.

By default it is read-only. With `--recalculate` (or the GUI checkbox) it regenerates
BCLCS levels 1-5, `FOREST_COVER_RANK_CODE`, and `LAND_COVER_ORDER`, writing a
timestamped backup next to the database first. Recalculation requires Java 8+; the
Jackcess helper and its jars are bundled.

## Requirements

- Python 3.10+
- `mdbtools` (`sudo apt install mdbtools`); `mdb-export` must be on `PATH`
- Tkinter for the GUI (`sudo apt install python3-tk` on Ubuntu)
- Java 8+ for `--recalculate`; validation does not use Java
- No Python packages are required

## Install

From the built wheel:

```bash
pip install dist/vri_validator-0.3.2-py3-none-any.whl
vri-validate --version
vri-validate-gui --version
```

From a source checkout:

```bash
pip install .
```

The `codes.xml` and `species_max.json` data files are bundled inside the
`vri_validator` package, so installed copies work without the source tree.

## QGIS PGeo support

GDAL's PGeo driver can read `.mdb` files read-only. Ubuntu does not install the
MDB Tools ODBC driver by default, so run the user-local setup once:

```bash
./scripts/setup_qgis_pgeo.sh
```

It downloads/extracts `odbc-mdbtools` without `sudo`, registers the driver in
`~/.odbcinst.ini`, creates a QGIS launcher at `~/bin/qgis`, and adds a user desktop
entry. After that, open `.mdb` files with **Layer > Add Layer > Add Vector Layer**
and choose **All files**, or enter the full path. `FOREST_COVER_OBJECT` opens as
EPSG:3005 with its polygon geometry.

For direct GDAL/PyQGIS use, export `MDBDRIVER_PATH` to the driver library:

```bash
export MDBDRIVER_PATH="$HOME/.local/lib/odbc/libmdbodbc.so"
ogrinfo -ro -so /path/to/file.mdb
```

## Usage

After installation:

```bash
vri-validate /path/to/093k050_VRIMS.mdb
vri-validate file.mdb --format csv --out reports
vri-validate file.mdb --fail-on warning
vri-validate file.mdb --recalculate
```

`--recalculate` writes the derived values in place and creates a backup such as
`092n025_VRIMS.vri-backup-20261022-151359.mdb`. Close ArcMap/VegCap first so the
`.mdb` is not locked. The command then validates the recalculated database.

Recalculated fields:

- `BCLCS_LEVEL1..5` for inventory standards `V` and `I`, following the VegCap II
  code-generation rules. `F` and `L` polygons are left unchanged.
- `FOREST_COVER_RANK_CODE` for `V`/`I`: rank 1 is the first live layer (ascending
  layer ID) with crown closure above 10%; if none, the live layer with the largest
  crown closure. All other layers are null. `F`/`L` ranks are retained.
- `LAND_COVER_ORDER` is renumbered consecutively by descending `COVERAGE_PCT`.

From a source checkout, use `python3 -m vri_validator` in place of `vri-validate`.

Reports are written to `reports/<database>_validation.html` and
`reports/<database>_validation.csv` by default.

Exit codes:

- `0` no findings at the selected failure level
- `1` findings at or above `--fail-on` (`error` by default; `warning` also fails on warnings)
- `2` usage or database read error

## Desktop GUI

Launch the GUI from a terminal:

```bash
vri-validate-gui
```

Choose the `.mdb`, output folder, and report format. Tick **Recalculate BCLCS,
layer rank and LCC order (backup first)** if needed, then click **Validate**.
The report opens in your browser when finished. From a source checkout:

```bash
python3 -m vri_validator.gui
```

To add an application-menu launcher and icon, run:

```bash
vri-validate-install-launcher
```

If the GUI executable is not found automatically, pass it explicitly:

```bash
vri-validate-install-launcher --exe ~/.venvs/vri/bin/vri-validate-gui
```

The launcher is written to `~/.local/share/applications/vri-validator.desktop`
and the icon to `~/.local/share/icons/hicolor/256x256/apps/vri-validator.png`.
From a source checkout, use `python3 -m vri_validator.launcher` in place of
`vri-validate-install-launcher`.

## Scope

Implemented: Forest Cover Object identity and referential integrity, VCPE codes and
conditional fields, TCL layer order and required fields, TSE species order/percentages/
age-height checks, LCC order/coverage and derived TB/TC/TM, NVCE order/coverage, disturbance
and opening checks, selected Access query checks from `QUERIESforMDBpgdb`, BCLCS/rank/LCC
recalculation with backup, a Tkinter desktop GUI, CSV/HTML reports, and a console-script
installer.

Not implemented: geometry/topology validation, spatial BEC subzone/variant checks, and
recalculation of fields other than BCLCS, layer rank, and LCC order. `BEC_ZONE_CODE` is
the only BEC field in the schema and is often blank; subzone/variant data would require
a spatial join.

## Data calibration

Files whose names contain `final` are treated as valid reference data during development.
Run the validator against those first and review remaining findings for false positives
before using it on new submissions.

`W-LCC-P-1460` (possible missing treed LCC) is suppressed when total live tree crown
closure is below 5%; polygons below that threshold are treated as non-treed. From 5%
to below 20%, the warning remains enabled.

## Files not included in this repository

- `vri_editor/data/template.mdb` (the blank map used by New map) is not published, because the copy
  on the development machine holds interpreter and project names. Create a blank map with
  File > New, or supply your own template at that path.
- `data/si_table_v154.csv.gz` (site-index table generated from the Ministry DLL with SiteToolsCmd)
  is not published, pending a check of redistribution terms. Without it, site-index estimates that
  use the table are unavailable.
- `reports/` (validation output for real maps) is not published.

## Licence

MIT, see `LICENSE`. The bundled Jackcess and Apache Commons jars (`vri_editor/data/`) are Apache 2.0.

