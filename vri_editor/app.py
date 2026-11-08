"""PyQt5 form editor for VRI polygon attributes."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from PyQt5.QtCore import QDate, Qt, QUrl, pyqtSignal
from PyQt5.QtGui import QDesktopServices, QIcon
from PyQt5.QtGui import QDoubleValidator, QIntValidator
from PyQt5.QtWidgets import (
    QAction,
    QActionGroup,
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QInputDialog,
    QRadioButton,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QStyle,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QToolBar,
    QVBoxLayout,
    QScrollArea,
    QWidget,
)
from PyQt5.QtWidgets import QDockWidget, QGroupBox, QTextEdit, QToolButton

from . import __version__, db, panels
from vri_validator.codes import FIELD_CODES, CodeBook, load_species_max
from vri_validator.model import load_dataset
from vri_validator.rules.engine import RuleContext, run_rules
from vri_validator.species import species_types

CODES = CodeBook()

FIELD_WIDTHS = {
    # widths sized to the longest value actually written in real VRI maps
    "POLYGON_NUMBER": 60,
    "POLYGON_AREA": 110,
    "OPENING_ID": 105,
    "OPENING_NUMBER": 60,
    "REFERENCE_YEAR": 65,
    "TSA_NUMBER": 75,
    "TFL_NUMBER": 75,
    "DISTURBANCE_CODE": 55,
    "DISTURBANCE_TYPE_CODE": 55,
    "DISTURBANCE_START_YEAR": 125,
    "DISTURBANCE_END_YEAR": 125,
    "DATA_CAPTURE_METHOD_CODE": 55,
    "FREE_TO_GROW_IND": 45,
    "SHRUB_HEIGHT": 80,
    "SHRUB_CROWN_CLOSURE": 60,
    "COVER_PATTERN_CODE": 55,
    "HERB_COVER_TYPE_CODE": 55,
    "HERB_COVER_PCT": 60,
    "HERB_COVER_PATTERN_CODE": 55,
    "BRYOID_COVER_PCT": 60,
    "BCLCS_LEVEL1_CODE": 50,
    "BCLCS_LEVEL2_CODE": 50,
    "BCLCS_LEVEL3_CODE": 50,
    "BCLCS_LEVEL4_CODE": 55,
    "BCLCS_LEVEL5_CODE": 55,
    "NON_PRODUCTIVE_CODE": 75,
    "NON_PRODUCTIVE_DESCRIPTOR_CODE": 110,
    "BEC_ZONE_CODE": 70,
    "VRI_DEAD_STEMS_PER_HA": 70,
}


FCO_FIELDS = (
    ("POLYGON_NUMBER", "Polygon number"),
    ("INVENTORY_STANDARD_CODE", "Inventory standard"),
    ("OPENING_ID", "Opening ID"),
    ("OPENING_NUMBER", "Opening number"),
    ("POLYGON_AREA", "Polygon area"),
    ("REFERENCE_YEAR", "Reference year"),
    ("DISTURBANCE_TYPE_CODE", "Disturbance type"),
    ("DISTURBANCE_START_YEAR", "Disturbance start"),
    ("DISTURBANCE_END_YEAR", "Disturbance end"),
    ("DATA_CAPTURE_METHOD_CODE", "Capture method"),
    ("FREE_TO_GROW_IND", "Free to grow (Y/N)"),
    ("DISTURBANCE_CODE", "Disturbance code"),
    ("TSA_NUMBER", "TSA"),
    ("TFL_NUMBER", "TFL"),
    ("INTERPRETER", "Interpreter"),
    ("PROJECT_NAME", "Project"),
)

VCPE_FIELDS = (
    ("NON_PRODUCTIVE_CODE", "Non-productive"),
    ("NON_PRODUCTIVE_DESCRIPTOR_CODE", "Non-productive descriptor"),
    ("SURFACE_EXPRESSION_CODE", "Surface expression"),
    ("MODIFYING_PROCESS_CODE", "Modifying process"),
    ("SITE_POSITION_MESO_CODE", "Site position"),
    ("ALPINE_DESIGNATION_CODE", "Alpine designation"),
    ("SOIL_NUTRIENT_REGIME_CODE", "Soil nutrient regime"),
    ("DATA_SOURCE_ECOSYS_CLASS_CODE", "Ecology data source"),
    ("BEC_ZONE_CODE", "BEC zone"),
    ("BCLCS_LEVEL1_CODE", "BCLCS level 1"),
    ("BCLCS_LEVEL2_CODE", "BCLCS level 2"),
    ("BCLCS_LEVEL3_CODE", "BCLCS level 3"),
    ("BCLCS_LEVEL4_CODE", "BCLCS level 4"),
    ("BCLCS_LEVEL5_CODE", "BCLCS level 5"),
    ("SHRUB_HEIGHT", "Shrub height"),
    ("SHRUB_CROWN_CLOSURE", "Shrub crown closure"),
    ("COVER_PATTERN_CODE", "Shrub cover pattern"),
    ("HERB_COVER_TYPE_CODE", "Herb cover type"),
    ("HERB_COVER_PCT", "Herb cover percent"),
    ("HERB_COVER_PATTERN_CODE", "Herb cover pattern"),
    ("BRYOID_COVER_PCT", "Bryoid cover percent"),
    ("VRI_DEAD_STEMS_PER_HA", "Dead stems/ha"),
    ("REFERENCE_YEAR", "Reference year"),
)

LAYER_COLUMNS = (
    ("LAYER_ORDER", "Order"),
    ("LAYER_LEVEL_CODE", "Level"),
    ("TREE_SPECIES_CODE", "Species"),
    ("COVER_PATTERN_CODE", "Cover pattern"),
    ("CROWN_CLOSURE_PCT", "Crown %"),
    ("BASAL_AREA", "BA"),
    ("DATA_SOURCE_BASAL_AREA_CODE", "BA source"),
    ("VRI_LIVE_STEMS_PER_HA", "Live stems/ha"),
    ("DATA_SRC_VRI_LIVE_STEM_HA_CODE", "Density source"),
    ("ESTIMATED_SITE_INDEX", "Site index"),
    ("ESTIMATED_SINDEX_SOURCE_CODE", "SI source"),
    ("FOREST_COVER_RANK_CODE", "Rank"),
    ("VERTICAL_COMPLEXITY_CODE", "VCC"),
)

SPECIES_COLUMNS = (
    ("SPECIES_ORDER", "Order"),
    ("TREE_SPECIES_CODE", "Species"),
    ("SPECIES_PCT", "Percent"),
    ("AGE", "Age"),
    ("HEIGHT", "Height"),
    ("DATA_SOURCE_AGE_CODE", "Age source"),
    ("DATA_SOURCE_HEIGHT_CODE", "Height source"),
)

LCC_COLUMNS = (
    ("LAND_COVER_ORDER", "Order"),
    ("LAND_COVER_LEVEL_CODE", "Level"),
    ("COVERAGE_PCT", "Coverage %"),
    ("SOIL_MOISTURE_REGIME_CODE", "Moisture"),
    ("LAND_COVER_CLASS_CODE", "Class"),
)

NVCE_COLUMNS = (
    ("NON_VEG_ORDER", "Order"),
    ("LAYER_LEVEL_CODE", "Level"),
    ("NON_VEG_COVER_PCT", "Coverage %"),
    ("COVER_PATTERN_CODE", "Pattern"),
    ("NON_VEG_COVER_TYPE_CODE", "Type"),
)



def _small_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    return label


def _tight_grid(box: QWidget) -> QGridLayout:
    grid = QGridLayout(box)
    grid.setContentsMargins(4, 2, 4, 2)
    grid.setHorizontalSpacing(3)
    grid.setVerticalSpacing(1)
    return grid


class StartupDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("VRI Editor startup")
        self.project = QLineEdit("SUNSHINE_COAST_VRI")
        self.interpreter = QLineEdit("")
        self.map_name = QLineEdit("092N035")
        self.folder = QLineEdit(str(Path.home() / "VRI_MDB_EDITOR" / "SUNSHINE_COAST_VRI"))
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._browse)
        folder_row = QHBoxLayout()
        folder_row.addWidget(self.folder)
        folder_row.addWidget(browse)
        form = QFormLayout()
        form.addRow("Project name", self.project)
        form.addRow("Interpreter", self.interpreter)
        form.addRow("Map name", self.map_name)
        form.addRow("Folder", folder_row)
        form.addRow("Current date", QLabel(QDate.currentDate().toString("yyyy-MM-dd")))
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Apply")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Apply these startup settings?"))
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _browse(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Choose project folder", self.folder.text())
        if path:
            self.folder.setText(path)

    def target(self) -> Path:
        return Path(self.folder.text()).expanduser() / f"{self.map_name.text().strip()}_VRIMS.mdb"


class NewProjectDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("New VRI map")
        self.project = QLineEdit("SUNSHINE_COAST_VRI")
        self.interpreter = QLineEdit("")
        self.map_name = QLineEdit("092N035")
        self.folder = QLineEdit(str(Path.home() / "VRI_MDB_EDITOR" / "SUNSHINE_COAST_VRI"))
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._browse)
        folder_row = QHBoxLayout()
        folder_row.addWidget(self.folder)
        folder_row.addWidget(browse)

        form = QFormLayout()
        form.addRow("Project name", self.project)
        form.addRow("Interpreter", self.interpreter)
        form.addRow("Map name", self.map_name)
        form.addRow("Folder", folder_row)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _browse(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Choose project folder", self.folder.text())
        if path:
            self.folder.setText(path)

    def target(self) -> Path:
        return Path(self.folder.text()).expanduser() / f"{self.map_name.text().strip()}_VRIMS.mdb"


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return default


class ResultsDialog(QDialog):
    def __init__(self, path: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        path = Path(path)
        self.path = path
        self.rows: list[dict[str, str]] = []
        self.setWindowTitle(f"RESULTS — {path.name}")
        self.resize(900, 560)
        from . import results
        try:
            self.rows = results.list_polygons(path)
        except Exception as exc:
            QMessageBox.critical(self, "RESULTS", str(exc))
            self.rows = []
        self.search = QLineEdit()
        self.search.setPlaceholderText("Filter by map, opening, polygon, project…")
        self.search.textChanged.connect(self._filter)
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["Map", "Opening ID", "Opening #", "RES polygon", "Area", "Layers", "BCLCS"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.doubleClicked.connect(self.accept)
        for row in self.rows:
            r = self.table.rowCount()
            self.table.insertRow(r)
            values = [row["map_id"], row["opening_id"], row.get("opening_number", ""),
                      row["polygon_id"], row["area"], row["layers"], row["bclcs"]]
            for c, value in enumerate(values):
                item = QTableWidgetItem(value)
                if c == 0:
                    item.setData(Qt.UserRole, row)
                self.table.setItem(r, c, item)
        self.replace = QCheckBox("Replace existing tree layers, species, land cover and non-veg")
        self.replace.setChecked(True)
        self.allow_duplicates = QCheckBox(
            "One RESULT may be copied to many VRI polygons (one-to-many)")
        self.allow_duplicates.setChecked(True)
        buttons = QDialogButtonBox(QDialogButtonBox.Cancel)
        apply_button = buttons.addButton("Apply to selected VRI polygon",
                                         QDialogButtonBox.AcceptRole)
        apply_button.clicked.connect(self._apply)
        tie_button = buttons.addButton("Tie unique openings",
                                       QDialogButtonBox.ActionRole)
        tie_button.clicked.connect(self._tie)
        geom_button = buttons.addButton("Tie by geometry",
                                        QDialogButtonBox.ActionRole)
        geom_button.clicked.connect(self._tie_geometry)
        self.mode = "selected"
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"{len(self.rows):,} RESULTS polygons"))
        layout.addWidget(self.search)
        layout.addWidget(self.table)
        layout.addWidget(self.replace)
        layout.addWidget(self.allow_duplicates)
        layout.addWidget(buttons)
        if self.table.rowCount():
            self.table.selectRow(0)

    def _filter(self, text: str) -> None:
        text = text.strip().lower()
        for r in range(self.table.rowCount()):
            match = not text or any(
                text in (self.table.item(r, c).text().lower() if self.table.item(r, c) else "")
                for c in range(self.table.columnCount()))
            self.table.setRowHidden(r, not match)

    def _apply(self) -> None:
        if self.selected() is None:
            QMessageBox.warning(self, "RESULTS", "Select a RESULTS polygon first.")
            return
        self.mode = "selected"
        self.accept()

    def _tie(self) -> None:
        if QMessageBox.question(
            self, "Tie unique openings",
            "Apply RESULTS to every VRI polygon whose opening ID matches exactly "
            "one RESULTS polygon?",
        ) != QMessageBox.Yes:
            return
        self.mode = "unique"
        self.accept()

    def _tie_geometry(self) -> None:
        if QMessageBox.question(
            self, "Tie by geometry",
            "Match every opening by geometry overlap, including polygons with "
            "multiple VRI or RESULTS candidates?",
        ) != QMessageBox.Yes:
            return
        self.mode = "geometry"
        self.accept()

    def selected(self) -> dict[str, str] | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return item.data(Qt.UserRole) if item else None


class GeometryImportDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Import spatial geometry")
        self.resize(760, 360)
        self.polygon_mode = QRadioButton("Polygon shapefile with POLYGON_ID")
        self.line_mode = QRadioButton("Line shapefile + point shapefile")
        self.polygon_mode.setChecked(True)
        mode = QHBoxLayout()
        mode.addWidget(self.polygon_mode)
        mode.addWidget(self.line_mode)

        self.poly_path = QLineEdit()
        self.line_path = QLineEdit()
        self.point_path = QLineEdit()
        self.id_field = QLineEdit("POLYGON_ID")
        self.point_id_field = QLineEdit("POLYGON_ID")
        self.create_missing = QCheckBox("Create placeholder rows for geometry polygons not in the MDB")
        self.create_missing.setChecked(False)

        form = QFormLayout()
        form.addRow("Polygon shapefile", self._file_row(self.poly_path))
        form.addRow("Line shapefile", self._file_row(self.line_path))
        form.addRow("Point shapefile", self._file_row(self.point_path))
        form.addRow("Polygon ID field", self.id_field)
        form.addRow("Point ID field", self.point_id_field)
        form.addRow("", self.create_missing)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(mode)
        layout.addLayout(form)
        layout.addWidget(buttons)

    @staticmethod
    def _file_row(edit: QLineEdit) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        browse = QPushButton("Browse…")
        browse.clicked.connect(lambda: GeometryImportDialog._browse(edit))
        layout.addWidget(edit)
        layout.addWidget(browse)
        return row

    @staticmethod
    def _browse(edit: QLineEdit) -> None:
        path, _ = QFileDialog.getOpenFileName(
            edit.parent(), "Choose shapefile", str(Path.home()), "Shapefiles (*.shp)")
        if path:
            edit.setText(path)



_OPEN_MAP_WINDOWS: list = []


def ask_new_map(parent) -> Path | None:
    """Ask for a new map's details, create it, and return its path (or None)."""
    dialog = NewProjectDialog(parent)
    if dialog.exec_() != QDialog.Accepted:
        return None
    project = dialog.project.text().strip()
    interpreter = dialog.interpreter.text().strip()
    map_name = dialog.map_name.text().strip()
    if not project or not interpreter or not map_name:
        QMessageBox.warning(parent, "New map", "Project, interpreter and map name are required.")
        return None
    target = dialog.target()
    if target.exists() and QMessageBox.question(
        parent, "New map", f"{target.name} already exists. Replace it?"
    ) != QMessageBox.Yes:
        return None
    try:
        return db.new_project(target, project=project, interpreter=interpreter,
                              map_name=map_name, overwrite=True)
    except Exception as exc:
        QMessageBox.critical(parent, "New map failed", str(exc))
        return None


def ask_open_map(parent) -> Path | None:
    start = Path.home() / "VRI_MDB_EDITOR" / "SUNSHINE_COAST_VRI"
    if not start.is_dir():
        start = Path.home()
    path, _ = QFileDialog.getOpenFileName(
        parent, "Open VRIMS database", str(start), "Access databases (*.mdb)")
    return Path(path) if path else None


def open_map_window(path: Path) -> "EditorWindow | None":
    """Open a map in its own editing window; other maps stay open."""
    window = EditorWindow()
    window._load(Path(path))
    if window.path is None:
        window.deleteLater()
        return None
    _OPEN_MAP_WINDOWS.append(window)
    window.show()
    return window


class StartWindow(QMainWindow):
    """General screen shown at start-up: no map is loaded until the user opens or creates one."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"VRI Editor {__version__}")
        self.resize(560, 260)
        label = QLabel("No map is open.\n\nUse File > New to create a map, or File > Open to edit "
                       "an existing _VRIMS.mdb. Each map opens in its own window, so several can "
                       "be edited at the same time.")
        label.setWordWrap(True)
        label.setAlignment(Qt.AlignCenter)
        self.setCentralWidget(label)
        file_menu = self.menuBar().addMenu("&File")
        for text, slot, shortcut in (
            ("&New map...", self._new, "Ctrl+N"),
            ("&Open map...", self._open, "Ctrl+O"),
        ):
            action = QAction(text, self)
            action.setShortcut(shortcut)
            action.triggered.connect(slot)
            file_menu.addAction(action)
        file_menu.addSeparator()
        quit_action = QAction("&Quit", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)
        help_menu = self.menuBar().addMenu("&Help")
        about = QAction("About MDB Editor", self)
        about.triggered.connect(lambda: EditorWindow._about(self))
        help_menu.addAction(about)

    def _new(self) -> None:
        path = ask_new_map(self)
        if path is not None:
            open_map_window(path)

    def _open(self) -> None:
        path = ask_open_map(self)
        if path is not None:
            open_map_window(path)

    def closeEvent(self, event) -> None:  # noqa: N802
        # quitting closes every map window; a map with unsaved changes can cancel the quit
        for window in list(_OPEN_MAP_WINDOWS):
            if not window.close():
                event.ignore()
                return
        event.accept()


class ValidateOptionsDialog(QDialog):
    """Options for Validate: output folder, report format, title, recalculate first."""

    def __init__(self, parent, default_out: Path) -> None:
        super().__init__(parent)
        self.setWindowTitle("Validate map")
        form = QFormLayout(self)
        self.out = QLineEdit(str(default_out))
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._browse)
        row = QHBoxLayout()
        row.addWidget(self.out)
        row.addWidget(browse)
        form.addRow("Output folder", row)
        self.fmt = QComboBox()
        self.fmt.addItems(["Both (CSV + HTML)", "CSV only", "HTML only"])
        form.addRow("Report format", self.fmt)
        self.title = QLineEdit()
        self.title.setPlaceholderText("optional")
        form.addRow("Report title", self.title)
        self.recalc = QCheckBox("Recalculate BCLCS, layer rank and LCC order first (backup written)")
        form.addRow("", self.recalc)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _browse(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Output folder", self.out.text())
        if folder:
            self.out.setText(folder)

    def values(self) -> dict:
        return {
            "out": Path(self.out.text().strip() or "reports").expanduser(),
            "format": {0: "both", 1: "csv", 2: "html"}[self.fmt.currentIndex()],
            "title": self.title.text().strip(),
            "recalculate": self.recalc.isChecked(),
        }


class ValidationSummaryDialog(QDialog):
    """Validation results: counts per severity, the top rules, and the report files."""

    def __init__(self, parent, path: Path, result, out_dir: Path) -> None:
        super().__init__(parent)
        from vri_validator.report import counts_by_code
        self.setWindowTitle(f"Validation — {path.name}")
        self.resize(640, 480)
        counts = result.findings.counts()
        layout = QVBoxLayout(self)
        summary = QLabel(f"Errors: {counts['error']}     Warnings: {counts['warning']}     "
                         f"Info: {counts['info']}")
        summary.setStyleSheet("font-size: 14pt; font-weight: bold;")
        layout.addWidget(summary)
        layout.addWidget(QLabel("Top rules (most frequent first):"))
        rules = counts_by_code(result.findings)[:50]
        table = QTableWidget(len(rules), 3)
        table.setHorizontalHeaderLabels(["Rule", "Severity", "Count"])
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        for row, (code, severity, n) in enumerate(rules):
            table.setItem(row, 0, QTableWidgetItem(code))
            table.setItem(row, 1, QTableWidgetItem(severity))
            table.setItem(row, 2, QTableWidgetItem(str(n)))
        table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(table)
        report_html = next((x for x in result.report_paths if x.suffix == ".html"), None)
        report_csv = next((x for x in result.report_paths if x.suffix == ".csv"), None)
        layout.addWidget(QLabel(f"Reports: {out_dir}"))
        buttons = QHBoxLayout()
        for text, target in (("Open HTML report", report_html),
                             ("Open CSV", report_csv),
                             ("Open folder", out_dir)):
            button = QPushButton(text)
            button.setEnabled(target is not None)
            button.clicked.connect(lambda _c=False, t=target: QDesktopServices.openUrl(
                QUrl.fromLocalFile(str(t))))
            buttons.addWidget(button)
        buttons.addStretch(1)
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        buttons.addWidget(close)
        layout.addLayout(buttons)


class EditorWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.path: Path | None = None
        self.rows: dict[int, dict[str, dict[str, str]]] = {}
        self.current_fid: int | None = None
        self.widgets: dict[str, QLineEdit] = {}
        self.original_children: dict[str, list[dict[str, str]]] = {}
        self.species_cache: dict[int, list[dict[str, Any]]] = {}
        self.species_original: dict[int, list[dict[str, str]]] = {}
        self.current_species_layer: int | None = None
        self.current_label: dict[str, str] = {}
        self.layer_rows: list[dict[str, Any]] = []
        self.polygon_order: list[int] = []
        self.classified_fids: set[int] = set()
        self.clipboard: dict[str, Any] | None = None
        self.last_backup: Path | None = None
        self.cursor_layer = 0
        self.cursor_level = 0
        self.active_layer_index = 0
        self.loading = False
        self.pending_snags: str | None = None
        self.pending_reference_year: str | None = None
        self.show_grid = False
        self._level0_fields: dict[str, str] | None = None
        self.default_mode = "empty"
        self.basal_auto_enabled = False
        self.dead_layer_rule = "stems100"
        self.lcc_rows: list[dict[str, Any]] = []
        self.nvce_rows: list[dict[str, Any]] = []
        self.dirty = False
        self.setWindowTitle(f"VRI Editor {__version__}")
        self.resize(1200, 820)
        self._build()
        self._menu()

    def _build(self) -> None:
        self._toolbar()

        central = QWidget()
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(4, 4, 4, 4)
        central_layout.setSpacing(3)
        top_row = QHBoxLayout()
        top_row.setSpacing(4)
        self.map_label = QLabel("")
        self.map_label.setStyleSheet("font-weight: bold;")
        top_row.addWidget(self.map_label)
        top_row.addStretch(1)
        add_polygon = QPushButton("Add polygon")
        add_polygon.clicked.connect(self._add_polygon)
        top_row.addWidget(add_polygon)
        delete_polygon = QPushButton("Delete polygon")
        delete_polygon.clicked.connect(self._delete_polygon)
        top_row.addWidget(delete_polygon)
        central_layout.addLayout(top_row)
        self.geometry_map = QLabel("map view")
        self.geometry_map.setAlignment(Qt.AlignCenter)
        self.geometry_map.setMinimumSize(320, 240)
        self.geometry_map.setStyleSheet("border: 1px solid #999; color: #666;")
        central_layout.addWidget(self.geometry_map)
        self.setCentralWidget(central)

        classification = QWidget()
        classification_layout = QVBoxLayout(classification)
        classification_layout.setContentsMargins(3, 3, 3, 3)
        classification_layout.setSpacing(3)

        # ---- row 1: nine form functions ----
        function_row = QHBoxLayout()
        function_row.setSpacing(2)
        self.function_buttons = {}
        for label, slot, tip in (
            ("Save", self._save, "Save the current polygon"),
            ("Copy", self._copy_polygon, "Copy this polygon classification"),
            ("Find", self._find_polygon, "Find a polygon by number or opening"),
            ("Defaults", self._apply_defaults, "Fill empty fields with defaults"),
            ("Undo", self._undo, "Undo the last save"),
            ("Int", None, "Intersect — not implemented yet"),
            ("Add", self._add_polygon, "Add a polygon"),
            ("Grid", self._toggle_grid, "Toggle the map grid"),
            ("Delete", self._delete_polygon, "Delete the current polygon"),
        ):
            button = QPushButton(label)
            button.setToolTip(tip)
            button.setFixedWidth(52)
            if slot is None:
                button.setEnabled(False)
            else:
                button.clicked.connect(slot)
            self.function_buttons[label] = button
            function_row.addWidget(button)
        function_row.addStretch(1)
        classification_layout.addLayout(function_row)

        # ---- row 2: polygon number, opening id, opening number, opening status ----
        header_box = QWidget()
        header_outer = QHBoxLayout(header_box)
        header_outer.setContentsMargins(0, 0, 0, 0)
        header_outer.setSpacing(6)
        poly_number = self._make_field(
            "POLYGON_NUMBER", "Poly number", "FOREST_COVER_OBJECT", "fco")
        opening_id = self._make_field(
            "OPENING_ID", "Open ID", "FOREST_COVER_OBJECT", "fco")
        opening_num = self._make_field(
            "OPENING_NUMBER", "Open num", "FOREST_COVER_OBJECT", "fco")
        opening_status = self._make_field(
            "FREE_TO_GROW_IND", "Open status", "FOREST_COVER_OBJECT", "fco")
        opening_status.setFixedWidth(40)
        previous = QPushButton("<")
        previous.setFixedWidth(22)
        previous.setToolTip("Previous polygon with a classification")
        previous.clicked.connect(lambda: self._goto_classified(-1))
        following = QPushButton(">")
        following.setFixedWidth(22)
        following.setToolTip("Next polygon with a classification")
        following.clicked.connect(lambda: self._goto_classified(1))
        header_outer.addWidget(QLabel("Poly number"))
        header_outer.addWidget(previous)
        header_outer.addWidget(poly_number)
        header_outer.addWidget(following)
        header_outer.addWidget(QLabel("Open ID"))
        header_outer.addWidget(opening_id)
        header_outer.addWidget(QLabel("Open num"))
        header_outer.addWidget(opening_num)
        header_outer.addWidget(QLabel("Open status"))
        header_outer.addWidget(opening_status)
        header_outer.addStretch(1)
        classification_layout.addWidget(header_box)


        # ---- geometry | ecology | land cover | site index ----
        geometry_box = QGroupBox("Geometry")
        geometry_grid = _tight_grid(geometry_box)
        self.geometry_name = QLabel("")
        self.geometry_area = QLabel("0")
        self.geometry_length = QLabel("0")
        self.percent_left = QLabel("")
        for widget in (self.geometry_name, self.geometry_area, self.geometry_length):
            widget.setFixedWidth(96)
            widget.setStyleSheet("border: 1px solid #bbb; background: #f4f4f4;")
        geometry_grid.addWidget(self.geometry_name, 1, 0)
        geometry_grid.addWidget(_small_label("Area (m2)"), 2, 0)
        geometry_grid.addWidget(self.geometry_area, 3, 0)
        geometry_grid.addWidget(_small_label("Length (m)"), 4, 0)
        geometry_grid.addWidget(self.geometry_length, 5, 0)
        geometry_grid.setRowStretch(6, 1)

        ecology_box = QGroupBox("Ecology")
        ecology_grid = _tight_grid(ecology_box)
        ecology_grid.addWidget(_small_label("Ecology"), 0, 0, 1, 2)
        ecology_names = (
            "SURFACE_EXPRESSION_CODE", "MODIFYING_PROCESS_CODE",
            "SITE_POSITION_MESO_CODE", "ALPINE_DESIGNATION_CODE",
            "SOIL_NUTRIENT_REGIME_CODE", "DATA_SOURCE_ECOSYS_CLASS_CODE",
        )
        ecology_labels = dict(VCPE_FIELDS)
        for index, name in enumerate(ecology_names, 1):
            text = ecology_labels[name]
            widget = self._make_field(name, text, "VEGETATION_COVER_POLYGON_EST", "vcpe")
            ecology_grid.addWidget(_small_label(text), index, 0)
            ecology_grid.addWidget(widget, index, 1)
        ecology_grid.setColumnStretch(2, 1)

        lcc_panel = panels.LandCoverComponents()
        lcc_panel.changed.connect(self._mark_changed)

        site_box = QGroupBox("Site index")
        site_grid = _tight_grid(site_box)
        self.site_species = QLabel("")
        self.site_index = panels._int_edit("", 1, 60)
        self.site_index.textChanged.connect(self._mark_changed)
        self.site_source = panels.code_edit("TREE_COVER_LAYER_ESTIMATED", "ESTIMATED_SINDEX_SOURCE_CODE")
        self.site_source.textChanged.connect(self._mark_changed)
        self.site_species.setFixedWidth(64)
        self.site_species.setStyleSheet("border: 1px solid #bbb; background: #f4f4f4;")
        for widget in (self.site_index, self.site_source):
            widget.setFixedWidth(64)
        site_grid.addWidget(_small_label("Species"), 0, 0)
        site_grid.addWidget(self.site_species, 0, 1)
        site_grid.addWidget(_small_label("Site Indx"), 1, 0)
        site_grid.addWidget(self.site_index, 1, 1)
        site_grid.addWidget(_small_label("Est Src"), 2, 0)
        site_grid.addWidget(self.site_source, 2, 1)
        site_grid.setColumnStretch(2, 1)
        inventory = self._make_field(
            "INVENTORY_STANDARD_CODE", "Inv Std", "FOREST_COVER_OBJECT", "fco")
        self.inv_std_display = inventory
        left_box = QGroupBox("Coverage")
        left_grid = _tight_grid(left_box)
        left_grid.addWidget(_small_label("% Left"), 0, 0)
        left_grid.addWidget(self.percent_left, 0, 1)
        left_grid.setColumnStretch(2, 1)

        top_grid = QGridLayout()
        top_grid.setContentsMargins(0, 0, 0, 0)
        top_grid.setHorizontalSpacing(3)
        top_grid.setVerticalSpacing(3)
        top_grid.addWidget(geometry_box, 0, 0)
        top_grid.addWidget(ecology_box, 0, 1)
        top_grid.addWidget(lcc_panel, 0, 2)
        site_column = QWidget()
        site_column_layout = QVBoxLayout(site_column)
        site_column_layout.setContentsMargins(0, 0, 0, 0)
        site_column_layout.setSpacing(3)
        site_column_layout.addWidget(site_box)
        inv_box = QGroupBox("Inventory")
        inv_grid = _tight_grid(inv_box)
        inv_grid.addWidget(_small_label("Inv Std"), 0, 0)
        inv_grid.addWidget(inventory, 0, 1)
        inv_grid.setColumnStretch(2, 1)
        site_column_layout.addWidget(inv_box)
        site_column_layout.addWidget(left_box)
        site_column_layout.addStretch(1)
        top_grid.addWidget(site_column, 0, 3)
        top_grid.setColumnStretch(0, 1)
        top_grid.setColumnStretch(1, 2)
        top_grid.setColumnStretch(2, 2)
        top_grid.setColumnStretch(3, 1)
        classification_layout.addLayout(top_grid)

        # ---- tree specific data: full width ----
        tree_box = QGroupBox("Tree specific data")
        tree_outer = QVBoxLayout(tree_box)
        tree_outer.setContentsMargins(4, 2, 4, 2)
        tree_outer.setSpacing(2)
        layer_row = QHBoxLayout()
        layer_row.setSpacing(3)
        layer_row.addWidget(_small_label("Layer"))
        self.layer_combo = QComboBox()
        self.layer_combo.setFixedWidth(64)
        self.layer_combo.currentIndexChanged.connect(self._layer_changed)
        self.layer_count = QLabel("1 of 1")
        layer_row.addWidget(self.layer_combo)
        layer_row.addWidget(self.layer_count)
        for text, slot, tip in (
            ("D", self._add_dead_layer, "Add a dead layer (level D)"),
            ("+", self._add_layer, "Add a tree layer"),
            ("-", self._delete_layer, "Delete this tree layer"),
        ):
            button = QPushButton(text)
            button.setFixedWidth(26)
            button.setToolTip(tip)
            button.clicked.connect(slot)
            layer_row.addWidget(button)
        layer_row.addStretch(1)
        tree_outer.addLayout(layer_row)

        layer_details = panels.LayerDetails()
        layer_details.changed.connect(self._mark_changed)
        tree_fields = QHBoxLayout()
        tree_fields.setSpacing(3)
        for text, widget in (("Crown closure %", layer_details.crown),
                             ("Cover pattern", layer_details.pattern),
                             ("Vertical complexity", layer_details.complexity)):
            tree_fields.addWidget(_small_label(text))
            tree_fields.addWidget(widget)
            tree_fields.addSpacing(10)
        tree_fields.addStretch(1)
        tree_outer.addLayout(tree_fields)
        classification_layout.addWidget(tree_box)

        # ---- species | 1st & 2nd species | mensurational ----
        species_box = panels.SpeciesComposition()
        species_box.changed.connect(self._mark_changed)
        species_detail = panels.SpeciesDetail()
        species_detail.changed.connect(self._mark_changed)
        mensurational = panels.Mensurational()
        mensurational.changed.connect(self._mark_changed)
        mensurational.density.editingFinished.connect(self._auto_basal)

        species_column = QWidget()
        species_column_layout = QVBoxLayout(species_column)
        species_column_layout.setContentsMargins(0, 0, 0, 0)
        species_column_layout.setSpacing(3)
        species_column_layout.addWidget(species_box)
        source_row = QHBoxLayout()
        source_row.addWidget(_small_label("Species data source"))
        source_row.addWidget(layer_details.species_source)
        source_row.addStretch(1)
        species_column_layout.addLayout(source_row)
        species_column_layout.addStretch(1)

        detail_column = QWidget()
        detail_column_layout = QVBoxLayout(detail_column)
        detail_column_layout.setContentsMargins(0, 0, 0, 0)
        detail_column_layout.setSpacing(3)
        detail_column_layout.addWidget(species_detail)
        reference_row = QHBoxLayout()
        reference_row.addWidget(_small_label("Reference year"))
        reference_row.addWidget(layer_details.reference_year)
        reference_row.addStretch(1)
        detail_column_layout.addLayout(reference_row)
        detail_column_layout.addStretch(1)

        mensurational_column = QWidget()
        mensurational_column_layout = QVBoxLayout(mensurational_column)
        mensurational_column_layout.setContentsMargins(0, 0, 0, 0)
        mensurational_column_layout.setSpacing(3)
        mensurational_column_layout.addWidget(mensurational)
        snags_row = QHBoxLayout()
        self.snags_display = QLabel("")
        self.snags_display.setFixedWidth(64)
        self.snags_display.setStyleSheet("border: 1px solid #bbb; background: #f4f4f4;")
        snags_row.addWidget(self.snags_display)
        snags_row.addWidget(_small_label("Snags"))
        snags_row.addWidget(layer_details.snags)
        snags_row.addStretch(1)
        mensurational_column_layout.addLayout(snags_row)
        mensurational_column_layout.addStretch(1)

        species_grid = QGridLayout()
        species_grid.setContentsMargins(0, 0, 0, 0)
        species_grid.setHorizontalSpacing(3)
        species_grid.addWidget(species_column, 0, 0)
        species_grid.addWidget(detail_column, 0, 1)
        species_grid.addWidget(mensurational_column, 0, 2)
        species_grid.setColumnStretch(0, 3)
        species_grid.setColumnStretch(1, 3)
        species_grid.setColumnStretch(2, 2)
        classification_layout.addLayout(species_grid)

        # ---- shrub | herb | bryoid + non-veg levels | non vegetated ----
        shrub_box = QGroupBox("Shrub")
        shrub_grid = _tight_grid(shrub_box)
        for index, (name, text) in enumerate((
            ("SHRUB_HEIGHT", "Height"),
            ("SHRUB_CROWN_CLOSURE", "Crown %"),
            ("COVER_PATTERN_CODE", "Pattern"),
        ), 1):
            shrub_grid.addWidget(_small_label(text), index, 0)
            shrub_grid.addWidget(self._make_field(name, text, "VEGETATION_COVER_POLYGON_EST", "vcpe"),
                                 index, 1)
        shrub_grid.setColumnStretch(2, 1)

        herb_box = QGroupBox("Herb")
        herb_grid = _tight_grid(herb_box)
        for index, (name, text) in enumerate((
            ("HERB_COVER_TYPE_CODE", "Type"),
            ("HERB_COVER_PCT", "Cover %"),
            ("HERB_COVER_PATTERN_CODE", "Pattern"),
        ), 1):
            herb_grid.addWidget(_small_label(text), index, 0)
            herb_grid.addWidget(self._make_field(name, text, "VEGETATION_COVER_POLYGON_EST", "vcpe"),
                                index, 1)
        herb_grid.setColumnStretch(2, 1)

        bryoid_box = QGroupBox("Bryoid")
        bryoid_grid = _tight_grid(bryoid_box)
        bryoid_grid.addWidget(_small_label("Cover %"), 1, 0)
        bryoid_grid.addWidget(self._make_field(
            "BRYOID_COVER_PCT", "Cover %", "VEGETATION_COVER_POLYGON_EST", "vcpe"), 1, 1)
        bryoid_grid.setColumnStretch(2, 1)

        nvce_panel = panels.NonVegetated()
        nvce_panel.changed.connect(self._mark_changed)
        nvce_panel.level_changed.connect(self._nv_level_changed)
        level_box = QWidget()
        level_row = QHBoxLayout(level_box)
        level_row.setContentsMargins(0, 0, 0, 0)
        level_row.setSpacing(3)
        for widget in nvce_panel.level_widgets()[:4]:
            level_row.addWidget(widget)
        level_row.addStretch(1)
        command_row = QHBoxLayout()
        command_row.setContentsMargins(0, 0, 0, 0)
        command_row.setSpacing(3)
        command_row.addWidget(nvce_panel.add_button)
        command_row.addWidget(nvce_panel.remove_button)
        command_row.addStretch(1)

        veg_grid = QGridLayout()
        veg_grid.setContentsMargins(0, 0, 0, 0)
        veg_grid.setHorizontalSpacing(3)
        veg_grid.setVerticalSpacing(3)
        veg_grid.addWidget(shrub_box, 0, 0)
        veg_grid.addWidget(herb_box, 0, 1)
        bryoid_column = QWidget()
        bryoid_column_layout = QVBoxLayout(bryoid_column)
        bryoid_column_layout.setContentsMargins(0, 0, 0, 0)
        bryoid_column_layout.setSpacing(2)
        bryoid_column_layout.addWidget(bryoid_box)
        bryoid_column_layout.addWidget(level_box)
        bryoid_column_layout.addLayout(command_row)
        bryoid_column_layout.addStretch(1)
        veg_grid.addWidget(bryoid_column, 0, 2)
        veg_grid.addWidget(nvce_panel, 0, 3)
        for column in range(4):
            veg_grid.setColumnStretch(column, 1)
        classification_layout.addLayout(veg_grid)

        # ---- disturbance: DCM and a day/month/year split disturbance grid ----
        dcm_box = QGroupBox("DCM")
        dcm_grid = _tight_grid(dcm_box)
        dcm_grid.addWidget(_small_label("DCM"), 0, 0)
        dcm_grid.addWidget(self._make_field(
            "DATA_CAPTURE_METHOD_CODE", "DCM", "FOREST_COVER_OBJECT", "fco"), 0, 1)
        dcm_grid.setColumnStretch(2, 1)
        disturbance_box = QGroupBox("Disturbance")
        disturbance_grid = _tight_grid(disturbance_box)
        start_parts = self._date_parts("DISTURBANCE_START_YEAR")
        end_parts = self._date_parts("DISTURBANCE_END_YEAR")
        cells = (
            ("Type", self._make_field("DISTURBANCE_TYPE_CODE", "Type",
                                      "FOREST_COVER_OBJECT", "fco")),
            ("Dist code", self._make_field("DISTURBANCE_CODE", "Dist code",
                                           "FOREST_COVER_OBJECT", "fco")),
            ("Start day", start_parts[0]), ("Start month", start_parts[1]),
            ("Start year", start_parts[2]),
            ("End day", end_parts[0]), ("End month", end_parts[1]),
            ("End year", end_parts[2]),
        )
        for column, (text, widget) in enumerate(cells):
            disturbance_grid.addWidget(_small_label(text), 0, column)
            disturbance_grid.addWidget(widget, 1, column)
        disturbance_grid.setColumnStretch(8, 1)
        classification_layout.addWidget(dcm_box)
        classification_layout.addWidget(disturbance_box)

        # ---- BCLCS levels: read-only display ----
        bclcs_box = QWidget()
        bclcs_outer = QVBoxLayout(bclcs_box)
        bclcs_outer.setContentsMargins(0, 0, 0, 0)
        bclcs_outer.setSpacing(1)
        bclcs_title = QLabel("BCLCS Levels")
        bclcs_title.setStyleSheet("font-weight: bold;")
        bclcs_outer.addWidget(bclcs_title)
        bclcs_grid = QGridLayout()
        bclcs_grid.setContentsMargins(0, 0, 0, 0)
        bclcs_grid.setHorizontalSpacing(2)
        bclcs_outer.addLayout(bclcs_grid)
        self.bclcs_display = []
        for i in range(1, 6):
            edit = QLineEdit()
            edit.setReadOnly(True)
            edit.setFixedWidth(38)
            self.bclcs_display.append(edit)
            bclcs_grid.addWidget(QLabel(str(i)), 0, (i - 1) * 2)
            bclcs_grid.addWidget(edit, 0, (i - 1) * 2 + 1)
        bclcs_grid.setColumnStretch(10, 1)
        classification_layout.addWidget(bclcs_box)

        # ---- navigation: level -> layer -> polygon ----
        nav_row = QHBoxLayout()
        nav_row.setSpacing(3)
        first_button = QPushButton("<<<")
        first_button.setFixedWidth(40)
        first_button.setToolTip("First polygon with a classification")
        first_button.clicked.connect(lambda: self._goto_edge(-1))
        previous_entry = QPushButton("<")
        previous_entry.setFixedWidth(26)
        previous_entry.setToolTip("Previous level (species row), else previous layer, else previous polygon")
        previous_entry.clicked.connect(lambda: self._move_cursor(-1))
        self.entry_display = QLabel("")
        self.entry_display.setAlignment(Qt.AlignCenter)
        self.entry_display.setMinimumWidth(280)
        self.entry_display.setStyleSheet(
            "border: 1px solid #999; padding: 1px;")
        next_entry = QPushButton(">")
        next_entry.setFixedWidth(26)
        next_entry.setToolTip("Next level (species row), else next layer, else next polygon")
        next_entry.clicked.connect(lambda: self._move_cursor(1))
        last_button = QPushButton(">>")
        last_button.setFixedWidth(34)
        last_button.setToolTip("Last polygon with a classification")
        last_button.clicked.connect(lambda: self._goto_edge(1))
        nav_row.addWidget(first_button)
        nav_row.addWidget(previous_entry)
        nav_row.addWidget(self.entry_display, 1)
        nav_row.addWidget(next_entry)
        nav_row.addWidget(last_button)
        classification_layout.addLayout(nav_row)
        classification_layout.addStretch(1)

        self.species_panel = species_box
        self.layer_details = layer_details
        self.mensurational_panel = mensurational
        self.species_detail = species_detail
        self.lcc_panel = lcc_panel
        self.nvce_panel = nvce_panel

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(classification)
        self.classification_dock = QDockWidget("Classification", self)
        self.classification_dock.setWidget(scroll)
        self.classification_dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetFloatable)
        self.addDockWidget(Qt.RightDockWidgetArea, self.classification_dock)

        self.warnings = QTextEdit()
        self.warnings.setReadOnly(True)
        self.warning_dock = QDockWidget("Warnings", self)
        self.warning_dock.setWidget(self.warnings)
        self.warning_dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetFloatable)
        self.addDockWidget(Qt.RightDockWidgetArea, self.warning_dock)
        self.warning_dock.hide()
        self.tabifyDockWidget(self.classification_dock, self.warning_dock)
        self.statusBar().showMessage("New map or open an existing _VRIMS.mdb")
        self._install_navigation()

    def _date_parts(self, name: str) -> tuple[QLineEdit, QLineEdit, QLineEdit]:
        """Day, month and year boxes for a date field.

        The original single date field (``name``) stays the stored value, so
        load and save are unchanged. The boxes are written into it only when all
        three are filled, so a half-typed date can never erase the stored value.
        """
        day = QLineEdit()
        month = QLineEdit()
        year = QLineEdit()
        day.setValidator(QIntValidator(1, 31, day))
        month.setValidator(QIntValidator(1, 12, month))
        year.setValidator(QIntValidator(1800, 2200, year))
        day.setMaxLength(2)
        month.setMaxLength(2)
        year.setMaxLength(4)
        for box, width in ((day, 30), (month, 30), (year, 44)):
            box.setFixedWidth(width)
        master = self._make_field(name, name, "FOREST_COVER_OBJECT", "fco")
        master.hide()
        self._date_boxes = getattr(self, "_date_boxes", {})
        self._date_boxes[name] = (day, month, year)
        master.textChanged.connect(lambda text, n=name: self._date_master_changed(n, text))
        for box in (day, month, year):
            box.textChanged.connect(lambda _t, n=name: self._date_boxes_changed(n))
        return day, month, year

    def _date_master_changed(self, name: str, text: str) -> None:
        if getattr(self, "_syncing_dates", False):
            return
        from vri_validator.model import year_of
        import re as _re
        boxes = self._date_boxes.get(name)
        if not boxes:
            return
        self._syncing_dates = True
        try:
            match = _re.match(r"\s*(\d{1,2})/(\d{1,2})/(\d{2,4})", text or "")
            iso = _re.match(r"\s*(\d{4})-(\d{2})-(\d{2})", text or "")
            if match:
                month, day = int(match.group(1)), int(match.group(2))
                year = year_of(text)
            elif iso:
                year, month, day = int(iso.group(1)), int(iso.group(2)), int(iso.group(3))
            else:
                for box in boxes:
                    box.clear()
                return
            boxes[0].setText(str(day))
            boxes[1].setText(str(month))
            boxes[2].setText(str(year) if year else "")
        finally:
            self._syncing_dates = False

    def _date_boxes_changed(self, name: str) -> None:
        if getattr(self, "_syncing_dates", False):
            return
        day, month, year = self._date_boxes[name]
        master = self.widgets.get(f"fco.{name}")
        if master is None or not (day.text() and month.text() and year.text()):
            return
        yyyy = int(year.text())
        composed = f"{int(month.text()):02d}/{int(day.text()):02d}/{yyyy % 100:02d} 00:00:00"
        if master.text() != composed:
            self._syncing_dates = True
            try:
                master.setText(composed)
            finally:
                self._syncing_dates = False
            self._mark_changed()

    def _make_field(self, name: str, label: str, table: str, prefix: str) -> QWidget:
        code_table = FIELD_CODES.get((table, name))
        widget: QLineEdit
        if code_table and CODES.codes(code_table):
            widget = panels.code_edit(table, name)
        else:
            widget = QLineEdit()
            if name in {"POLYGON_AREA"}:
                widget.setReadOnly(True)
            elif name == "POLYGON_NUMBER":
                widget.setValidator(QIntValidator(0, 9999, widget))
                widget.setMaxLength(4)
            elif name == "REFERENCE_YEAR":
                widget.setValidator(QIntValidator(1800, 2200, widget))
                widget.setMaxLength(4)
            elif name == "OPENING_ID":
                widget.setValidator(QIntValidator(0, 2147483647, widget))
                widget.setMaxLength(10)
            elif name == "SHRUB_HEIGHT":
                widget.setValidator(QDoubleValidator(0.1, 9.9, 1, widget))
                widget.setMaxLength(4)
                widget.setFixedWidth(52)
            elif name in {"SHRUB_CROWN_CLOSURE", "HERB_COVER_PCT", "BRYOID_COVER_PCT"}:
                widget.setValidator(QIntValidator(0, 95, widget))
                widget.setMaxLength(2)
                widget.setFixedWidth(48)
            elif name == "VRI_DEAD_STEMS_PER_HA":
                widget.setValidator(QIntValidator(0, 5000, widget))
                widget.setMaxLength(4)
            elif name in {"OPENING_NUMBER", "TSA_NUMBER", "TFL_NUMBER"}:
                widget.setMaxLength(20)
            else:
                widget.setMaxLength(30)
            widget.setFixedWidth(FIELD_WIDTHS.get(name, 120))
        # Typing a polygon number is navigation, not an edit (see _poly_number_enter);
        # a rename only happens through _save, which asks first.
        if not (prefix == "fco" and name == "POLYGON_NUMBER"):
            widget.textChanged.connect(self._mark_changed)
        self.widgets[f"{prefix}.{name}"] = widget
        return widget

    def _toolbar(self) -> None:
        toolbar = self.addToolBar("Main")
        toolbar.setMovable(False)
        style = self.style()
        actions = [
            ("New", style.standardIcon(QStyle.SP_FileIcon), self._new),
            ("Open", style.standardIcon(QStyle.SP_DirOpenIcon), self._open),
            ("Save", style.standardIcon(QStyle.SP_DialogSaveButton), self._save),
            ("Print", style.standardIcon(QStyle.SP_FileDialogStart), self._validate),
            ("Cut", style.standardIcon(QStyle.SP_TrashIcon), self._cut_polygon),
            ("Copy", style.standardIcon(QStyle.SP_FileDialogDetailedView), self._copy_polygon),
            ("Paste", style.standardIcon(QStyle.SP_FileDialogBack), self._paste_polygon),
            ("Warnings", style.standardIcon(QStyle.SP_MessageBoxInformation), self._toggle_warnings),
            ("Find", style.standardIcon(QStyle.SP_FileDialogContentsView), self._find_polygon),
        ]
        for label, icon, slot in actions:
            action = QAction(label, self)
            if icon is not None:
                action.setIcon(icon)
            action.triggered.connect(slot)
            toolbar.addAction(action)
        toolbar.addSeparator()

    def _menu(self) -> None:
        project_menu = self.menuBar().addMenu("&Project")
        self._action(project_menu, "&New VRI Project", self._new)
        self._action(project_menu, "&Open VRI project", self._open)
        project_menu.addSeparator()
        project_menu.addSeparator()
        self._action(project_menu, "Set Current Defaults", self._set_current_defaults)

        file_menu = self.menuBar().addMenu("&File")
        self._action(file_menu, "&New", self._new, "Ctrl+N")
        self._action(file_menu, "&Open", self._open, "Ctrl+O")
        self._action(file_menu, "&Save", self._save, "Ctrl+S")
        self._action(file_menu, "Save &As", self._save_as)
        self._action(file_menu, "Save All", self._save)
        self._action(file_menu, "Save CSV", self._save_csv)
        self._action(file_menu, "Export to GeoPackage...", self._export_gpkg)
        file_menu.addSeparator()
        self._action(file_menu, "Import Spatial Data", self._import_geometry)
        self._action(file_menu, "Import Results", self._import_results)
        self._action(file_menu, "BACKUP", self._backup_current)

        edit_menu = self.menuBar().addMenu("&Edit")
        self._action(edit_menu, "Undo", self._undo, "Ctrl+Z")
        self._action(edit_menu, "Cut", self._cut_polygon, "Ctrl+X")
        self._action(edit_menu, "Copy", self._copy_polygon, "Ctrl+C")
        self._action(edit_menu, "Paste", self._paste_polygon, "Ctrl+V")
        self._action(edit_menu, "Copy Information", self._copy_information)
        self._action(edit_menu, "Interpreter Information", self._interpreter_info)
        self._action(edit_menu, "Search Fields", self._search_fields)
        default_mode_menu = edit_menu.addMenu("Default mode")
        self._action(default_mode_menu, "Overwrite existing values",
                    lambda: self._set_default_mode("overwrite"))
        self._action(default_mode_menu, "Only write defaults in empty fields",
                    lambda: self._set_default_mode("empty"))
        edit_menu.addSeparator()
        self._action(edit_menu, "Diagnostics", self._validate)
        self._action(edit_menu, "Statistics report", self._statistics)

        polygon_menu = self.menuBar().addMenu("&Polygon")
        self._action(polygon_menu, "Find", self._find_polygon, "Ctrl+F")
        self._action(polygon_menu, "Polygon +1", lambda: self._navigate_polygon(1))
        self._action(polygon_menu, "Polygon -1", lambda: self._navigate_polygon(-1))
        self._action(polygon_menu, "New polygon count", self._statistics)
        self._action(polygon_menu, "Renumber", self._renumber)
        self._action(polygon_menu, "Check order", self._check_order)
        self._action(polygon_menu, "Auto Numbering", self._auto_number)
        self._action(polygon_menu, "Recalculate polygons", self._recalculate)
        self._action(polygon_menu, "Tie File", self._import_results)
        self.basal_auto_action = QAction("Basal area calculator", self)
        self.basal_auto_action.setCheckable(True)
        self.basal_auto_action.setChecked(False)
        self.basal_auto_action.triggered.connect(self._toggle_basal_auto)
        polygon_menu.addAction(self.basal_auto_action)

        labels_menu = self.menuBar().addMenu("&Labels")
        self._action(labels_menu, "Update labels", self._recalculate)

        tools_menu = self.menuBar().addMenu("&Tools")
        self._action(tools_menu, "Add log dates", self._add_log_dates)
        self._action(tools_menu, "Test for Dup polys", self._check_duplicates)
        self._action(tools_menu, "Calculate Site Index", self._recalculate)
        self._action(tools_menu, "Fix Site Index", self._fix_site_index)
        self._action(tools_menu, "Load PolyMap", self._import_geometry)
        import_polygons_menu = tools_menu.addMenu("Import Polygons")
        self._action(import_polygons_menu, "ARC polygons", self._import_geometry)
        self._action(import_polygons_menu, "DGN polygons", self._import_geometry)
        export_polygons_menu = tools_menu.addMenu("Export polygons")
        self._action(export_polygons_menu, "Polygon shapefile with labels...", self._export_polygons)
        self._action(export_polygons_menu, "Point shapefile with labels...", self._export_points)
        self._action(tools_menu, "Compact MDB", self._check_structure)
        self._action(tools_menu, "Compact & Repair MDB", self._check_structure)
        self._action(tools_menu, "Rename MDB file", self._rename_mdb)
        tools_menu.addSeparator()
        for text, slot in (
            ("Import geometry…", self._import_geometry),
            ("Import RESULTS…", self._import_results),
            ("Recalculate derived fields", self._recalculate),
            ("Validate and open report", self._validate),
            ("Validate range (polygons x to y)...", self._validate_range),
        ):
            self._action(tools_menu, text, slot)
        self._action(tools_menu, "Export Validation Report", self._export_validation_report)
        tools_menu.addAction(self.basal_auto_action)
        rule_menu = tools_menu.addMenu("Dead-layer rule")
        rule_group = QActionGroup(self)
        rule_group.setExclusive(True)
        for key, text in (("stems100", "Snags >= 100 stems/ha (default)"),
                          ("pct30", "Snags >= 30% of live density")):
            action = QAction(text, self)
            action.setCheckable(True)
            action.setChecked(key == self.dead_layer_rule)
            action.triggered.connect(lambda _checked=False, k=key: self._set_dead_layer_rule(k))
            rule_group.addAction(action)
            rule_menu.addAction(action)

        help_menu = self.menuBar().addMenu("&Help")
        self._action(help_menu, "About MDB Editor", self._about)
        self._action(help_menu, "User Guide", self._user_guide)

    def _about(self) -> None:
        QMessageBox.about(
            self, "About MDB Editor",
            "MDB Editor 2026 for Linux\n\n"
            "Native editor for BC VRI/VRIMS personal geodatabases.\n"
            "Create/open MDBs, classify polygons, import spatial geometry, "
            "tie RESULTS by opening ID or geometry, recalculate derived fields, "
            "and validate records. Writes use backups.")

    def _user_guide(self) -> None:
        QMessageBox.information(
            self, "User Guide",
            "Basic workflow:\n"
            "1. The start window has no map. File > New or File > Open opens a map in its\n"
            "   own window; several maps can be open and edited at the same time.\n"
            "   Each window saves and closes on its own.\n"
            "2. Select a polygon and edit General, Ecology, layers, species, "
            "land cover, and non-vegetative fields.\n"
            "3. Use Add/Delete polygon as needed.\n"
            "4. Tools > Import geometry to load polygon shapefiles or line/point data.\n"
            "5. Tools > Import RESULTS to apply or tie RESULT attributes.\n"
            "6. Tools > Recalculate derived fields.\n"
            "7. Tools > Validate and open report (or validate a polygon range).\n"
            "   Keyboard: Enter moves through the fields in groups (ecology, land cover\n"
            "   until 100%, tree data, species until 100%, age/height, basal area and\n"
            "   density, shrub, herb, bryoid, non-vegetated, DCM, disturbance). Site index\n"
            "   is visited after the first age when that age is 29 or less and the site\n"
            "   index is blank. Arrow keys move to the nearest field in that direction.\n"
            "   Poly number: Enter jumps to an existing polygon, or offers to create a new\n"
            "   one (filled with the default template where it has values).\n"
            "   Tools > Fix Site Index: sets each live layer's site index from its leading\n"
            "   species, age and height using the Sindex v1.54 curves (source code C).\n"
            "   Layers whose source is another estimate (E, A, S...) are kept as they are.\n"
            "   Tools > Basal area calculator (checkable): when density is entered and\n"
            "   basal area is empty, an estimate is filled in (leading species, age,\n"
            "   height, density, crown closure if entered). Accept or change it.\n"
            "8. Project > Set Current Defaults captures the current polygon as a default\n"
            "   template; Edit > Default mode chooses overwrite vs empty-only; the\n"
            "   Defaults button applies it.\n"
            "9. Polygon > Renumber / Auto Numbering / Check order are for special maps\n"
            "   (e.g. split RESULTS maps with oversized polygon IDs); not needed for\n"
            "   normal map work.\n"
            "10. Exporting to an Esri File Geodatabase (.gdb): this app cannot write\n"
            "    .gdb (requires the proprietary Esri SDK). Export a shapefile with\n"
            "    Tools > Export polygons > Shapefile with labels, then in ArcMap use\n"
            "    ArcToolbox > To Geodatabase > Feature Class to Geodatabase (or\n"
            "    ogr2ogr -f FileGDB) to load it; or export to GeoPackage via\n"
            "    File > Export to GeoPackage for a fully open, QGIS-ready format.\n"
            "All writes create backups.")


    def _action(self, menu: Any, text: str, slot: Any, shortcut: str = "") -> QAction:
        action = QAction(text, self)
        if shortcut:
            action.setShortcut(shortcut)
        action.triggered.connect(slot)
        menu.addAction(action)
        return action

    def _save_as(self) -> None:
        """Save the current edits, then copy the map to a new file.

        The open map stays the same, so later edits still go to the original.
        """
        if self.path is None:
            QMessageBox.warning(self, "Save As", "Open a map first.")
            return
        target, _ = QFileDialog.getSaveFileName(
            self, "Save copy as", str(self.path), "Access databases (*.mdb)")
        if not target:
            return
        target_path = Path(target)
        if target_path.suffix.lower() != ".mdb":
            target_path = target_path.with_suffix(".mdb")
        if target_path.resolve() == self.path.resolve():
            QMessageBox.warning(self, "Save As", "Choose a different file name.")
            return
        if not self._save():
            return
        import shutil
        try:
            shutil.copy2(self.path, target_path)
        except OSError as exc:
            QMessageBox.critical(self, "Save As failed", str(exc))
            return
        self.statusBar().showMessage(f"Copied map to {target_path.name}")

    def _copy_information(self) -> None:
        """Put a text summary of the current polygon on the system clipboard."""
        if self.current_fid is None:
            return
        record = self.rows.get(self.current_fid, {})
        fco = record.get("fco", {})
        lines = [
            f"Polygon {fco.get('POLYGON_NUMBER', '')}",
            f"Opening ID {fco.get('OPENING_ID', '')}  "
            f"Opening number {fco.get('OPENING_NUMBER', '')}",
            f"Inventory standard {fco.get('INVENTORY_STANDARD_CODE', '')}",
            f"Layers {len(self.layer_rows)}",
        ]
        for layer in self.layer_rows:
            lid = _int(layer.get("TREE_COVER_LAYER_ESTIMATED_ID"))
            species = self.species_cache.get(lid) or self.species_original.get(lid, [])
            codes = " ".join(
                f"{row.get('TREE_SPECIES_CODE', '')}:{row.get('SPECIES_PCT', '')}"
                for row in species)
            lines.append(
                f"  Layer {layer.get('LAYER_LEVEL_CODE', '')}: "
                f"crown {layer.get('CROWN_CLOSURE_PCT', '')} "
                f"basal {layer.get('BASAL_AREA', '')}  {codes}")
        QApplication.clipboard().setText("\n".join(lines))
        self.statusBar().showMessage("Polygon information copied")

    def _statistics(self) -> None:
        """Counts and areas for the open map, from the rows already in memory."""
        total = len(self.rows)
        classified = len(self.classified_fids)
        layer_total = 0
        dead = 0
        if self.path is not None:
            known = set(self.rows.keys())
            for layer in db.read_rows(self.path, "TREE_COVER_LAYER_ESTIMATED"):
                if _int(layer.get("FOREST_COVER_OBJECT_ID")) not in known:
                    continue
                layer_total += 1
                if str(layer.get("LAYER_LEVEL_CODE", "")).upper() == "D":
                    dead += 1

        def area_of(fids: Any) -> float:
            value = 0.0
            for fid in fids:
                try:
                    value += float(self.rows[fid]["fco"].get("POLYGON_AREA", "") or 0)
                except (KeyError, ValueError):
                    pass
            return value

        QMessageBox.information(
            self, "Statistics",
            f"Polygons: {total:,}\n"
            f"Classified: {classified:,}\n"
            f"Unclassified: {total - classified:,}\n\n"
            f"Tree layers: {layer_total - dead:,}\n"
            f"Dead layers: {dead:,}\n\n"
            f"Area (all polygons): {area_of(self.rows):,.1f} m2\n"
            f"Area (classified): {area_of(self.classified_fids):,.1f} m2")

    def _check_duplicates(self) -> None:
        """Report polygon numbers that appear on more than one polygon."""
        seen: dict[str, int] = {}
        for fid in self.polygon_order:
            number = (self.rows[fid]["fco"].get("POLYGON_NUMBER", "") or "").strip()
            if number:
                seen[number] = seen.get(number, 0) + 1
        duplicates = sorted(number for number, count in seen.items() if count > 1)
        if not duplicates:
            QMessageBox.information(self, "Duplicate polygons", "No duplicate polygon numbers.")
            return
        QMessageBox.warning(
            self, "Duplicate polygons",
            f"{len(duplicates)} polygon number(s) are used more than once:\n\n"
            + "\n".join(f"{number}: {seen[number]} polygons" for number in duplicates[:50]))

    def _generate_lcc_codes(self) -> None:
        """Derive TC/TM/TB for every polygon and write it into the LCC rows.

        Only the first land-cover component is touched, and only when it is
        empty or already a tree class (TC/TM/TB), so user-edited non-tree
        classes (ST, HE, ...) are never overwritten.
        """
        if self.path is None:
            QMessageBox.warning(self, "Generate LCC codes", "Open a map first.")
            return
        if not self._save():
            return
        from vri_validator.model import load_dataset
        from vri_validator.codes import CodeBook
        from vri_validator.species import species_types
        from vri_validator.derive import treed_class
        dataset = load_dataset(str(self.path))
        types = species_types(CodeBook())
        from . import db
        TREE_CLASSES = {"TC", "TM", "TB"}
        edits: list[str] = []
        touched = 0
        for poly in dataset.polygons:
            derived = treed_class(poly, types.get)
            if derived is None:
                continue
            expected = derived[0]
            fid = poly.fid
            if fid is None:
                continue
            # LCC: first component only
            lcc_rows = [r for r in db.read_rows(self.path, "LAND_COVER_COMPONENT_EST")
                        if _int(r.get("FOREST_COVER_OBJECT_ID")) == fid]
            lcc_rows.sort(key=lambda r: _int(r.get("LAND_COVER_ORDER"), 99))
            if lcc_rows:
                first = lcc_rows[0]
                key = _int(first.get("LAND_COVER_COMPONENT_EST_ID"))
                current = (first.get("LAND_COVER_CLASS_CODE") or "").strip().upper()
                if (not current or current in TREE_CLASSES) and current != expected:
                    edits.append(db.edit_line(
                        "U", "LAND_COVER_COMPONENT_EST", "LAND_COVER_COMPONENT_EST_ID",
                        key, {"LAND_COVER_CLASS_CODE": expected}))
                    touched += 1
            # BCLCS: only when the polygon is treed
            vcpe = poly.vcpe or {}
            if str(vcpe.get("BCLCS_LEVEL2_CODE", "")).upper() == "T":
                current4 = (vcpe.get("BCLCS_LEVEL4_CODE") or "").strip().upper()
                if (not current4 or current4 in TREE_CLASSES) and current4 != expected:
                    edits.append(db.edit_line(
                        "U", "VEGETATION_COVER_POLYGON_EST", "FOREST_COVER_OBJECT_ID",
                        fid, {"BCLCS_LEVEL4_CODE": expected}))
        if not edits:
            QMessageBox.information(self, "Generate LCC codes",
                                    "No polygon needed a tree class.")
            return
        if QMessageBox.question(
            self, "Generate LCC codes",
            f"Update {touched} polygon(s)? A backup will be created.",
        ) != QMessageBox.Yes:
            return
        try:
            backup, count = db.save(self.path, edits)
        except Exception as exc:
            QMessageBox.critical(self, "Generate LCC codes failed", str(exc))
            return
        self._load(self.path)
        text = f"Updated {count} row(s)."
        if backup is not None:
            text += f"\nBackup: {backup.name}"
        QMessageBox.information(self, "Generate LCC codes", text)

    def _nv_level_changed(self, level: int) -> None:
        """Keep the navigation cursor in sync with the non-veg level buttons."""
        self.cursor_level = level
        self._apply_level_mode()
        self._update_cursor_display()

    def _apply_level_mode(self) -> None:
        """On extra non-veg levels (2, 3) blank and disable everything except
        the non-vegetated group, matching the Windows form-filler behaviour."""
        extra = self.cursor_level > 0
        nv = self.nvce_panel
        if extra:
            if self._level0_fields is None:
                self._level0_fields = {name: w.text() for name, w in self.widgets.items()}
                for name, widget in self.widgets.items():
                    widget.blockSignals(True)
                    widget.setText("")
                    widget.blockSignals(False)
                    widget.setEnabled(False)
                for panel in (self.species_panel, self.layer_details,
                              self.mensurational_panel, self.species_detail,
                              self.lcc_panel):
                    panel.setEnabled(False)
                self.layer_combo.setEnabled(False)
        else:
            if self._level0_fields is not None:
                for name, widget in self.widgets.items():
                    widget.blockSignals(True)
                    widget.setText(self._level0_fields.get(name, ""))
                    widget.blockSignals(False)
                    widget.setEnabled(True)
                for panel in (self.species_panel, self.layer_details,
                              self.mensurational_panel, self.species_detail,
                              self.lcc_panel):
                    panel.setEnabled(True)
                self.layer_combo.setEnabled(True)
                nv.add_button.setEnabled(len(nv.rows) < 3)
                self._level0_fields = None
                # reload the active layer so panels show their values again
                self._load_active_layer()
                self._update_displays()

    def _clear_level_mode_on_load(self) -> None:
        self._level0_fields = None

    def _cut_polygon(self) -> None:
        """Copy the current polygon classification, then delete the polygon."""
        if self.current_fid is None:
            return
        self._copy_polygon()
        if QMessageBox.question(
            self, "Cut polygon",
            "Delete the current polygon after copying its classification?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        ) != QMessageBox.Yes:
            return
        self._delete_polygon()

    def _interpreter_info(self) -> None:
        if self.current_fid is None:
            QMessageBox.warning(self, "Interpreter information", "Open a polygon first.")
            return
        record = self.rows.get(self.current_fid, {})
        fco = record.get("fco", {})
        vcpe = record.get("vcpe", {})
        lines = [
            f"Polygon: {fco.get('POLYGON_NUMBER', '')}",
            f"Interpreter: {fco.get('INTERPRETER', '') or vcpe.get('INTERPRETER', '')}",
            f"Project: {fco.get('PROJECT', '') or vcpe.get('PROJECT', '')}",
            f"TSA: {fco.get('TSA_NUMBER', '')}   TFL: {fco.get('TFL_NUMBER', '')}",
            f"Inventory standard: {fco.get('INVENTORY_STANDARD_CODE', '')}",
            f"Map: {self.path.name if self.path else ''}",
        ]
        QMessageBox.information(self, "Interpreter information", "\n".join(lines))

    def _search_fields(self) -> None:
        if not self.rows:
            QMessageBox.warning(self, "Search", "Open a map first.")
            return
        text, accepted = QInputDialog.getText(self, "Search fields", "Text to find:")
        if not accepted or not text.strip():
            return
        needle = text.strip().lower()
        matches: list[str] = []
        for fid in self.polygon_order:
            record = self.rows[fid]
            for prefix in ("fco", "vcpe"):
                for field, value in record.get(prefix, {}).items():
                    if needle in str(value or "").lower():
                        matches.append(
                            f"{record['fco'].get('POLYGON_NUMBER', fid)} "
                            f"({prefix}.{field}={value})")
                        break
                else:
                    continue
                break
        if not matches:
            QMessageBox.information(self, "Search", "No matching polygons.")
            return
        choice, ok = QInputDialog.getItem(
            self, "Search results", f"{len(matches)} match(es):",
            matches[:200], 0, False)
        if ok and choice:
            number = choice.split()[0]
            for fid in self.polygon_order:
                if (self.rows[fid]["fco"].get("POLYGON_NUMBER", "") or "").strip() == number:
                    self._load_polygon(fid)
                    return

    def _save_csv(self) -> None:
        if self.path is None or not self.rows:
            QMessageBox.warning(self, "Save CSV", "Open a map first.")
            return
        target, _ = QFileDialog.getSaveFileName(
            self, "Save CSV", str(self.path.with_suffix(".csv")), "CSV files (*.csv)")
        if not target:
            return
        import csv
        fields = ["POLYGON_NUMBER", "OPENING_ID", "OPENING_NUMBER",
                  "INVENTORY_STANDARD_CODE", "POLYGON_AREA", "TSA_NUMBER", "TFL_NUMBER",
                  "BEC_ZONE_CODE", "DISTURBANCE_CODE", "DISTURBANCE_TYPE_CODE",
                  "DISTURBANCE_START_YEAR", "DISTURBANCE_END_YEAR"]
        try:
            with open(target, "w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(fields)
                for fid in self.polygon_order:
                    fco = self.rows[fid].get("fco", {})
                    writer.writerow([fco.get(field, "") for field in fields])
        except OSError as exc:
            QMessageBox.critical(self, "Save CSV failed", str(exc))
            return
        self.statusBar().showMessage(f"Saved CSV: {Path(target).name}")

    def _rename_mdb(self) -> None:
        if self.path is None:
            QMessageBox.warning(self, "Rename MDB", "Open a map first.")
            return
        name, accepted = QInputDialog.getText(
            self, "Rename MDB file", "New file name (without extension):",
            text=self.path.stem)
        if not accepted or not name.strip():
            return
        new_path = self.path.with_name(name.strip() + self.path.suffix)
        if new_path == self.path:
            return
        if new_path.exists():
            QMessageBox.warning(self, "Rename MDB", f"{new_path.name} already exists.")
            return
        if not self._save():
            return
        import shutil
        try:
            shutil.move(str(self.path), str(new_path))
        except OSError as exc:
            QMessageBox.critical(self, "Rename failed", str(exc))
            return
        self.path = new_path
        self._load(self.path)
        self.statusBar().showMessage(f"Renamed to {new_path.name}")

    def _check_order(self) -> None:
        if not self.rows:
            QMessageBox.warning(self, "Check order", "Open a map first.")
            return
        numbers = [self.rows[fid]["fco"].get("POLYGON_NUMBER", "") for fid in self.polygon_order]
        problems: list[str] = []
        seen: set[str] = set()
        for index, number in enumerate(numbers):
            if number in seen:
                problems.append(f"Duplicate polygon number {number}.")
            seen.add(number)
            if index > 0:
                try:
                    if int(number) <= int(numbers[index - 1]):
                        problems.append(
                            f"Polygon {number} is not greater than {numbers[index - 1]}.")
                except ValueError:
                    pass
        if not problems:
            QMessageBox.information(self, "Check order", "Polygon numbers are in order.")
            return
        QMessageBox.warning(self, "Check order", "\n".join(problems[:50]))

    def _renumber(self) -> None:
        if self.path is None or not self.rows:
            QMessageBox.warning(self, "Renumber", "Open a map first.")
            return
        start, accepted = QInputDialog.getInt(
            self, "Renumber", "Starting number:", 1, 1, 999999, 1)
        if not accepted:
            return
        if QMessageBox.question(
            self, "Renumber",
            f"Renumber all {len(self.rows)} polygons starting at {start}?",
        ) != QMessageBox.Yes:
            return
        if not self._save():
            return
        from . import db
        edits: list[str] = []
        for offset, fid in enumerate(self.polygon_order):
            edits.append(db.edit_line(
                "U", "FOREST_COVER_OBJECT", "FOREST_COVER_OBJECT_ID", fid,
                {"POLYGON_NUMBER": str(start + offset)}))
        try:
            backup, count = db.save(self.path, edits)
        except Exception as exc:
            QMessageBox.critical(self, "Renumber failed", str(exc))
            return
        self._load(self.path)
        text = f"Renumbered {len(self.rows)} polygons."
        if backup is not None:
            text += f"\nBackup: {backup.name}"
        QMessageBox.information(self, "Renumber", text)

    def _auto_number(self) -> None:
        self._renumber()

    def _validate_range(self) -> None:
        """Validate the map and show findings for polygons X..Y in the warnings window."""
        if self.path is None:
            QMessageBox.warning(self, "Validate range", "Open a map first.")
            return
        if not self._save():
            return
        start, ok1 = QInputDialog.getInt(
            self, "Validate range", "From polygon number:", 1, 1, 999999, 1)
        if not ok1:
            return
        end, ok2 = QInputDialog.getInt(
            self, "Validate range", "To polygon number:", start, start, 999999, 1)
        if not ok2:
            return
        if end < start:
            start, end = end, start
        try:
            from vri_validator.service import validate_database
            result = validate_database(self.path, out_dir=self.path.parent / "reports")
        except Exception as exc:
            QMessageBox.critical(self, "Validation failed", str(exc))
            return
        lines = []
        for finding in result.findings.items:
            poly_no = None
            try:
                poly_no = int(finding.polygon_number)
            except (TypeError, ValueError):
                pass
            if poly_no is None or poly_no < start or poly_no > end:
                continue
            lines.append(f"[{finding.severity.upper()}] poly {finding.polygon_number} "
                         f"{finding.code}: {finding.message}")
        if lines:
            self.warnings.setPlainText("\n".join(lines))
        else:
            self.warnings.setPlainText(
                f"No warnings for polygons {start} to {end}.")
        self.warning_dock.show()
        self.warning_dock.raise_()
        counts = result.findings.counts()
        self.statusBar().showMessage(
            f"Validated {start}-{end}: {len(lines)} finding(s) in range "
            f"(map total errors {counts['error']}, warnings {counts['warning']}).")

    def _defaults_path(self) -> Path:
        return Path.home() / ".config" / "vri_editor" / "defaults.json"

    def _load_defaults(self) -> dict[str, Any] | None:
        path = self._defaults_path()
        if not path.is_file():
            return None
        try:
            import json
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    def _save_defaults(self, data: dict[str, Any]) -> None:
        path = self._defaults_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        import json
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _set_default_mode(self, mode: str) -> None:
        self.default_mode = mode
        self.statusBar().showMessage(
            f"Default mode: {'overwrite existing values' if mode == 'overwrite' else 'only empty fields'}")

    def _set_current_defaults(self) -> None:
        if self.current_fid is None:
            QMessageBox.warning(self, "Set Current Defaults", "Open a polygon first.")
            return
        self._store_species()
        record = self.rows.get(self.current_fid, {})
        data = {
            "fco": dict(record.get("fco", {})),
            "vcpe": dict(record.get("vcpe", {})),
            "layers": [dict(r) for r in self.layer_rows],
            "species": {str(k): [dict(r) for r in v]
                        for k, v in self.species_cache.items()},
            "lcc": [dict(r) for r in self.lcc_rows],
            "nvce": [dict(r) for r in self.nvce_rows],
        }
        # strip identity fields so defaults apply to any polygon
        for prefix in ("fco", "vcpe"):
            for key in ("FOREST_COVER_OBJECT_ID", "OBJECTID", "POLYGON_NUMBER",
                        "OPENING_ID", "OPENING_NUMBER"):
                data[prefix].pop(key, None)
        if QMessageBox.question(
            self, "Set Current Defaults",
            "Save the current polygon classification as the default template?",
        ) != QMessageBox.Yes:
            return
        self._save_defaults(data)
        self.statusBar().showMessage("Default template saved.")

    def _apply_defaults(self) -> None:
        """Apply the saved default template to the current polygon."""
        if self.current_fid is None:
            return
        data = self._load_defaults()
        if not data:
            # fall back to the built-in minimal default
            data = {"fco": {"INVENTORY_STANDARD_CODE": "V"}, "vcpe": {}}
        changed: list[str] = []
        overwrite = self.default_mode == "overwrite"
        source = data.get("fco", {})
        for name, widget in self.widgets.items():
            prefix, field = name.split(".", 1)
            src = data.get(prefix, {})
            if field not in src:
                continue
            value = str(src.get(field, "") or "")
            if not value:
                continue
            if (not overwrite) and widget.text().strip():
                continue
            widget.setText(value)
            changed.append(field)
        if changed:
            self.dirty = True
            self.statusBar().showMessage(
                "Applied defaults: " + ", ".join(changed[:8])
                + ("..." if len(changed) > 8 else ""))
        else:
            self.statusBar().showMessage("Nothing to default")

    def _export_polygons(self) -> None:
        if self.path is None:
            QMessageBox.warning(self, "Export polygons", "Open a map first.")
            return
        target, _ = QFileDialog.getSaveFileName(
            self, "Export polygons", str(self.path.with_suffix(".shp")),
            "Shapefiles (*.shp)")
        if not target:
            return
        try:
            from . import spatial
            out_path, count = spatial.export_polygons(self.path, target)
        except Exception as exc:
            QMessageBox.critical(self, "Export failed", str(exc))
            return
        self.statusBar().showMessage(f"Exported {count} polygon(s) to {Path(out_path).name}")

    def _check_structure(self) -> None:
        """Verify the MDB has a healthy VRIMS structure and report faults."""
        if self.path is None:
            QMessageBox.warning(self, "Check structure", "Open a map first.")
            return
        from . import db
        from vri_validator.model import TABLES
        available = set(db.read_rows(self.path, "MSysObjects") and [] or [])
        try:
            import subprocess
            tables = set()
            # use mdb-tables if available
            completed = subprocess.run(
                ["mdb-tables", "-1", str(self.path)], capture_output=True, text=True)
            if completed.returncode == 0:
                tables = set(completed.stdout.split())
        except Exception:
            tables = set()
        required = set(TABLES)
        missing = sorted(required - tables) if tables else []
        # FK checks via db.read_rows
        fco_ids = {int(r["FOREST_COVER_OBJECT_ID"]) for r in db.read_rows(self.path, "FOREST_COVER_OBJECT")
                   if r.get("FOREST_COVER_OBJECT_ID")}
        issues: list[str] = []
        for table in ("TREE_COVER_LAYER_ESTIMATED", "LAND_COVER_COMPONENT_EST",
                      "NON_VEGETATIVE_COVER_EST"):
            for row in db.read_rows(self.path, table):
                fid = row.get("FOREST_COVER_OBJECT_ID")
                if fid and int(fid) not in fco_ids:
                    issues.append(f"{table}: orphaned row for FCO {fid}")
        # duplicate FCO ids
        from collections import Counter
        counts = Counter(r.get("FOREST_COVER_OBJECT_ID") for r in db.read_rows(self.path, "FOREST_COVER_OBJECT"))
        for fid, n in counts.items():
            if n > 1:
                issues.append(f"FOREST_COVER_OBJECT: duplicate FCO id {fid} ({n} rows)")
        # missing required tables
        if missing:
            issues.append("Missing tables: " + ", ".join(missing))
        # geometry index check
        try:
            idx = db.read_rows(self.path, "FOREST_COVER_OBJECT_GEOMETRY_Index")
            if not idx:
                issues.append("FOREST_COVER_OBJECT_GEOMETRY_Index is empty (no spatial index).")
        except Exception:
            issues.append("FOREST_COVER_OBJECT_GEOMETRY_Index table missing.")
        if not issues:
            QMessageBox.information(self, "Check structure",
                                    "Structure OK: no missing tables, orphaned rows, or duplicate IDs found.")
        else:
            QMessageBox.warning(self, "Check structure",
                                "Structure issues found:\n\n" + "\n".join(issues[:50])
                                + ("\n..." if len(issues) > 50 else "")
                                + "\n\nTrue compact/repair requires Microsoft Access; "
                                  "this check reports faults only.")
        self.statusBar().showMessage(f"Structure check: {len(issues)} issue(s).")

    def _add_log_dates(self) -> None:
        if self.path is None:
            QMessageBox.warning(self, "Add log dates", "Open a VRI map first.")
            return
        start = Path.home() / "Forest_VRI_validator" / "RESULTS_MDB"
        if not start.is_dir():
            start = self.path.parent
        res_path, _ = QFileDialog.getOpenFileName(
            self, "Choose RESULTS database", str(start), "Access databases (*.mdb *.accdb)")
        if not res_path:
            return
        overwrite = QMessageBox.question(
            self, "Add log dates",
            "Overwrite existing disturbance dates on VRI polygons?") == QMessageBox.Yes
        if not self._save():
            return
        from . import results
        try:
            applied, skipped, updated = results.import_log_dates(
                self.path, res_path, overwrite=overwrite)
        except Exception as exc:
            QMessageBox.critical(self, "Add log dates failed", str(exc))
            return
        self._load(self.path)
        QMessageBox.information(
            self, "Add log dates",
            f"Updated {updated} polygon(s).\n"
            f"Applied: {len(applied)}  Skipped: {len(skipped)}")

    def _export_gpkg(self) -> None:
        if self.path is None:
            QMessageBox.warning(self, "Export GeoPackage", "Open a map first.")
            return
        target, _ = QFileDialog.getSaveFileName(
            self, "Export GeoPackage", str(self.path.with_suffix(".gpkg")),
            "GeoPackage (*.gpkg)")
        if not target:
            return
        try:
            from . import spatial
            out_path, count = spatial.export_to_gpkg(self.path, target)
        except Exception as exc:
            QMessageBox.critical(self, "Export failed", str(exc))
            return
        self.statusBar().showMessage(f"Exported {count} table(s) to {Path(out_path).name}")

    def _export_points(self) -> None:
        if self.path is None:
            QMessageBox.warning(self, "Export points", "Open a map first.")
            return
        target, _ = QFileDialog.getSaveFileName(
            self, "Export points", str(self.path.with_suffix(".shp")),
            "Shapefiles (*.shp)")
        if not target:
            return
        try:
            from . import spatial
            out_path, count = spatial.export_points(self.path, target)
        except Exception as exc:
            QMessageBox.critical(self, "Export failed", str(exc))
            return
        self.statusBar().showMessage(f"Exported {count} point(s) to {Path(out_path).name}")

    def _set_dead_layer_rule(self, rule: str) -> None:
        self.dead_layer_rule = rule
        self._update_warnings()
        self.statusBar().showMessage(f"Dead-layer rule: {rule}")

    def _toggle_basal_auto(self) -> None:
        """Turn the basal area estimate on or off (Tools > Basal area calculator)."""
        self.basal_auto_enabled = self.basal_auto_action.isChecked()
        self.statusBar().showMessage(
            "Basal area calculator on: empty basal area is estimated when density is entered"
            if self.basal_auto_enabled else "Basal area calculator off")

    def _auto_basal(self) -> None:
        """When density is finished and basal area is empty, pre-fill an estimate.

        Uses the leading species, its age and height, the layer density and,
        when entered, the layer crown closure. The estimate is only written into
        an empty basal area field; the user can accept it or overwrite it.
        Dead layers are skipped (their density is snags, not live stems).
        """
        from . import basal
        if not self.basal_auto_enabled or self.current_fid is None or self.loading:
            return
        panel = self.mensurational_panel
        if panel.basal.text().strip() or panel.density_target == "snags":
            return
        layer = self._active_layer()
        if layer is not None and str(layer.get("LAYER_LEVEL_CODE", "")).upper() == "D":
            return
        species = self.species_panel.codes[0].text().strip()
        age = self.species_detail.ages[0].text().strip()
        height = self.species_detail.heights[0].text().strip()
        density = panel.density.text().strip()
        crown_text = self.layer_details.crown.text().strip()
        crown = float(crown_text) if crown_text.isdigit() else None
        value = basal.estimate(species, age, height, density, crown)
        if value is None:
            return
        panel.basal.setText(f"{value:.1f}")
        self.statusBar().showMessage(
            f"Basal area estimated at {value:.1f} m2/ha: accept it or change it")

    def _fix_site_index(self) -> None:
        """Recompute each live layer's site index from its leading species, age and height.

        Uses the Ministry Sindex v1.54 curves (vri_editor/siteindex.py). Layers with
        no curve or out-of-range inputs are left unchanged. Sets the source code to
        C (SI from Site Index Curve) on the layers it changes.
        """
        if self.path is None:
            QMessageBox.warning(self, "Fix Site Index", "Open a map first.")
            return
        if not self._save():
            return
        from . import db, siteindex
        layers = db.read_rows(self.path, "TREE_COVER_LAYER_ESTIMATED")
        species = db.read_rows(self.path, "TREE_SPECIES_ESTIMATED")
        by_layer: dict[int, list[dict[str, str]]] = {}
        for row in species:
            by_layer.setdefault(_int(row.get("TREE_COVER_LAYER_ESTIMATED_ID")), []).append(row)
        edits: list[str] = []
        same = skipped = kept_other = duplicate_rows = 0
        id_counts: dict[int, int] = {}
        for layer in layers:
            key = _int(layer.get("TREE_COVER_LAYER_ESTIMATED_ID"))
            id_counts[key] = id_counts.get(key, 0) + 1
        duplicated = {k for k, n in id_counts.items() if n > 1}
        written: set[int] = set()
        for layer in layers:
            if str(layer.get("LAYER_LEVEL_CODE", "")).upper() == "D":
                skipped += 1
                continue
            rows = sorted(by_layer.get(_int(layer.get("TREE_COVER_LAYER_ESTIMATED_ID")), []),
                          key=lambda r: -float(r.get("SPECIES_PCT") or 0))
            if not rows:
                skipped += 1
                continue
            key = _int(layer.get("TREE_COVER_LAYER_ESTIMATED_ID"))
            if key in duplicated:
                # duplicated layer rows cannot be addressed safely by ID; report instead
                duplicate_rows += 1
                continue
            if key in written:
                continue
            lead = rows[0]
            value = siteindex.site_index(lead.get("TREE_SPECIES_CODE", ""),
                                         lead.get("AGE", ""), lead.get("HEIGHT", ""))
            if value is None:
                skipped += 1
                continue
            whole = int(round(value))
            current = (layer.get("ESTIMATED_SITE_INDEX") or "").strip()
            source = (layer.get("ESTIMATED_SINDEX_SOURCE_CODE") or "").strip().upper()
            if source not in ("", "C"):
                # a district, adjacent-stand or other estimate is kept as entered
                kept_other += 1
                continue
            if current == str(whole) and source == "C":
                same += 1
                continue
            # ESTIMATED_SITE_INDEX is an integer column in VRIMS (whole metres)
            written.add(key)
            edits.append(db.edit_line(
                "U", "TREE_COVER_LAYER_ESTIMATED", "TREE_COVER_LAYER_ESTIMATED_ID",
                key,
                {"ESTIMATED_SITE_INDEX": str(int(round(value))), "ESTIMATED_SINDEX_SOURCE_CODE": "C"}))
        if not edits:
            QMessageBox.information(
                self, "Fix Site Index",
                f"Nothing to change. Already matching: {same}. Kept (other source): "
                f"{kept_other}. Skipped: {skipped}. Duplicated layer rows: {duplicate_rows}.")
            return
        if QMessageBox.question(
            self, "Fix Site Index",
            f"Set site index on {len(edits)} layer(s) from the Sindex v1.54 curves?\n"
            f"Already matching: {same}. Kept (other source code): {kept_other}.\n"
            f"Skipped (no curve, dead layer or out of range): {skipped}.\n"
            f"Not changed, duplicated layer rows (fix first): {duplicate_rows}.\n"
            "A backup will be created.",
        ) != QMessageBox.Yes:
            return
        try:
            backup, count = db.save(self.path, edits)
        except Exception as exc:
            QMessageBox.critical(self, "Fix Site Index failed", str(exc))
            self._load(self.path)
            return
        fid = self.current_fid
        self._load(self.path)
        if fid is not None:
            self._select_fid(fid)
        text = f"Updated {count} row(s)."
        if backup is not None:
            text += f"\nBackup: {backup.name}"
        QMessageBox.information(self, "Fix Site Index", text)

    # ---- keyboard navigation (Enter groups, arrow keys) -------------------------

    def _install_navigation(self) -> None:
        """Route Enter and arrow keys of the filler fields through this window."""
        self._entry_list = [w for w in self.classification_dock.widget().findChildren(QLineEdit)
                            if not w.isReadOnly()]
        QApplication.instance().installEventFilter(self)

    def eventFilter(self, obj, event):  # noqa: N802 (Qt name)
        from PyQt5.QtCore import QEvent
        if event.type() != QEvent.KeyPress or not isinstance(obj, QLineEdit):
            return super().eventFilter(obj, event)
        if obj not in getattr(self, "_entry_list", []) or not self.isVisible():
            return super().eventFilter(obj, event)
        key = event.key()
        if key in (Qt.Key_Return, Qt.Key_Enter):
            if obj is self.widgets.get("fco.POLYGON_NUMBER"):
                self._poly_number_enter()
            else:
                self._nav_enter(obj)
            return True
        if key == Qt.Key_Up:
            self._nav_arrow(obj, 0, -1)
            return True
        if key == Qt.Key_Down:
            self._nav_arrow(obj, 0, 1)
            return True
        if key == Qt.Key_Left and obj.cursorPosition() == 0:
            self._nav_arrow(obj, -1, 0)
            return True
        if key == Qt.Key_Right and obj.cursorPosition() == len(obj.text()):
            self._nav_arrow(obj, 1, 0)
            return True
        return super().eventFilter(obj, event)

    def _focus_widget(self, widget) -> None:
        widget.setFocus()
        if hasattr(widget, "selectAll"):
            widget.selectAll()

    def _nav_sequence(self) -> list:
        """Fillable fields in Enter order, with the conditional steps resolved now."""
        W = self.widgets
        seq: list = []

        def add(widget):
            if widget is not None and widget.isEnabled() and not widget.isReadOnly() \
                    and not widget.isHidden() and widget not in seq:
                seq.append(widget)

        add(W.get("fco.OPENING_ID"))
        add(W.get("fco.OPENING_NUMBER"))
        add(W.get("fco.FREE_TO_GROW_IND"))
        for name in ("SURFACE_EXPRESSION_CODE", "MODIFYING_PROCESS_CODE",
                     "SITE_POSITION_MESO_CODE", "ALPINE_DESIGNATION_CODE",
                     "SOIL_NUTRIENT_REGIME_CODE", "DATA_SOURCE_ECOSYS_CLASS_CODE"):
            add(W.get("vcpe." + name))
        # land cover components: a row is visited only while the percentages sum below 100
        lcc = self.lcc_panel
        total = 0
        for i in range(len(lcc.types)):
            if i > 0 and total >= 100:
                break
            add(lcc.types[i]); add(lcc.percents[i]); add(lcc.smr[i])
            total += _int(lcc.percents[i].text())
        # tree specific data of the active layer
        details = self.layer_details
        add(details.crown); add(details.pattern); add(details.complexity)
        # species composition: rows are visited while the percentages sum below 100
        species = self.species_panel
        total = 0
        for i in range(len(species.codes)):
            if i > 0 and total >= 100:
                break
            add(species.codes[i]); add(species.percents[i])
            total += _int(species.percents[i].text())
        detail = self.species_detail
        add(detail.ages[0])
        age_text = detail.ages[0].text().strip()
        if age_text and _int(age_text) <= 29 and not self.site_index.text().strip():
            add(self.site_index)
        add(detail.heights[0]); add(detail.age_sources[0]); add(detail.height_sources[0])
        if species.codes[1].text().strip():
            add(detail.ages[1]); add(detail.heights[1])
        mens = self.mensurational_panel
        add(mens.basal); add(mens.basal_source); add(mens.density); add(mens.density_source)
        add(details.species_source); add(details.reference_year); add(details.snags)
        # shrub, herb, bryoid, non-vegetated, DCM, disturbance
        add(W.get("vcpe.SHRUB_HEIGHT"))
        if W.get("vcpe.SHRUB_HEIGHT") and W["vcpe.SHRUB_HEIGHT"].text().strip():
            add(W.get("vcpe.SHRUB_CROWN_CLOSURE")); add(W.get("vcpe.COVER_PATTERN_CODE"))
        add(W.get("vcpe.HERB_COVER_TYPE_CODE"))
        if W.get("vcpe.HERB_COVER_TYPE_CODE") and W["vcpe.HERB_COVER_TYPE_CODE"].text().strip():
            add(W.get("vcpe.HERB_COVER_PCT")); add(W.get("vcpe.HERB_COVER_PATTERN_CODE"))
        add(W.get("vcpe.BRYOID_COVER_PCT"))
        nv = self.nvce_panel
        add(nv.cover); add(nv.percent); add(nv.pattern)
        add(W.get("fco.DATA_CAPTURE_METHOD_CODE"))
        add(W.get("fco.DISTURBANCE_TYPE_CODE")); add(W.get("fco.DISTURBANCE_CODE"))
        for name in ("DISTURBANCE_START_YEAR", "DISTURBANCE_END_YEAR"):
            for box in self._date_boxes.get(name, ()):
                add(box)
        return seq

    def _nav_enter(self, widget) -> None:
        seq = self._nav_sequence()
        if widget in seq:
            index = seq.index(widget)
            if index + 1 < len(seq):
                self._focus_widget(seq[index + 1])
            else:
                # last field of the order: wrap back to the poly number
                self._focus_widget(self.widgets["fco.POLYGON_NUMBER"])
            return
        # not in the guided order (e.g. a field whose group is now empty): plain Tab order
        widget.window().focusNextChild()

    def _nav_arrow(self, widget, dx: int, dy: int) -> None:
        """Move to the nearest visible field lying in the pressed direction."""
        def centre(w):
            c = w.mapToGlobal(w.rect().center())
            return c.x(), c.y()
        px, py = centre(widget)
        best = None
        for other in self._entry_list:
            if other is widget or other.isHidden() or not other.isEnabled():
                continue
            ox, oy = centre(other)
            main = (ox - px) * dx + (oy - py) * dy
            cross = abs((ox - px) * dy) + abs((oy - py) * dx)
            if main <= 2:
                continue
            score = main + 2 * cross
            if best is None or score < best[0]:
                best = (score, other)
        # Open ID goes down to Surface expression (the first ecology field)
        if widget is self.widgets.get("fco.OPENING_ID") and (dx, dy) == (0, 1):
            best = (0, self.widgets["vcpe.SURFACE_EXPRESSION_CODE"])
        if best is not None:
            self._focus_widget(best[1])

    def _poly_number_enter(self) -> None:
        """Enter on the poly number: jump to that polygon, or offer to create it."""
        field = self.widgets["fco.POLYGON_NUMBER"]
        typed = field.text().strip()
        current = self.rows.get(self.current_fid, {}).get("fco", {}).get("POLYGON_NUMBER", "")
        # The box always goes back to the current number first, so the typed text
        # can never reach a save as a rename of the polygon being left.
        field.blockSignals(True)
        field.setText(current)
        field.blockSignals(False)
        if not typed or typed == current:
            self._focus_widget(self.widgets["fco.OPENING_ID"])
            return
        target = None
        for fid, record in self.rows.items():
            if (record.get("fco", {}).get("POLYGON_NUMBER", "") or "").strip() == typed:
                target = fid
                break
        if target is not None:
            self._load_polygon(target)
            self._focus_widget(self.widgets["fco.OPENING_ID"])
            return
        if QMessageBox.question(
            self, "Polygon number",
            f"Polygon {typed} does not exist in this map.\n"
            "Create a new polygon with this number?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        ) != QMessageBox.Yes:
            return
        if self.dirty and not self._save():
            return
        from . import db
        try:
            fid = db.add_polygon(self.path, typed)
        except Exception as exc:
            QMessageBox.critical(self, "Create polygon failed", str(exc))
            return
        self._load(self.path)
        self._select_fid(fid)
        self._apply_defaults()
        self._focus_widget(self.widgets["fco.OPENING_ID"])

    def _toggle_warnings(self) -> None:
        self.warning_dock.setVisible(not self.warning_dock.isVisible())

    def _navigate_polygon(self, delta: int) -> None:
        if not self.polygon_order:
            return
        if self.current_fid in self.polygon_order:
            index = self.polygon_order.index(self.current_fid)
        else:
            index = 0
        index = max(0, min(len(self.polygon_order) - 1, index + delta))
        self._load_polygon(self.polygon_order[index])

    def _update_warnings(self) -> None:
        if self.path is None or self.current_fid is None:
            return
        try:
            dataset = load_dataset(str(self.path))
            codes = CodeBook()
            species_max = load_species_max()
            context = RuleContext(
                dataset=dataset,
                codes=codes,
                species_types=species_types(codes),
                species_max=species_max,
            )
            findings = run_rules(context)
        except Exception as exc:
            self.warnings.setPlainText(f"Validation error: {exc}")
            return
        lines = []
        from . import deadlayer
        for finding in findings.items:
            if finding.polygon_id != self.current_fid:
                continue
            if finding.code == deadlayer.CODE:
                continue  # replaced by the rule selected in Tools > Dead-layer rule
            lines.append(f"[{finding.severity.upper()}] {finding.code}: {finding.message}")
            if finding.table or finding.field:
                lines.append(f"    {finding.table}.{finding.field} = {finding.value}")
        record = self.rows.get(self.current_fid, {})
        message = deadlayer.dead_layer_message(
            record.get("vcpe", {}), self.layer_rows, self.dead_layer_rule)
        if message:
            lines.append(f"[ERROR] {deadlayer.CODE}: {message}")
        if lines:
            self.warnings.setPlainText("\n".join(lines))
        else:
            self.warnings.setPlainText("No warnings for this polygon.")

    def _backup_current(self) -> None:
        if self.path is None:
            QMessageBox.warning(self, "Backup", "Open a map first.")
            return
        if not self._save():
            return
        from . import db
        backup = db.backup_path(self.path)
        try:
            import shutil
            shutil.copy2(self.path, backup)
        except Exception as exc:
            QMessageBox.critical(self, "Backup failed", str(exc))
            return
        self.statusBar().showMessage(f"Backup created: {backup.name}")

    def _update_displays(self) -> None:
        if self.current_fid is None or self.path is None:
            return
        record = self.rows.get(self.current_fid, {})
        fco = record.get("fco", {})
        vcpe = record.get("vcpe", {})
        self.geometry_area.setText(str(fco.get("GEOMETRY_Area", "") or "0"))
        self.geometry_length.setText(str(fco.get("GEOMETRY_Length", "") or "0"))
        if hasattr(self, "percent_left"):
            try:
                tree_cc = sum(_int(r.get("CROWN_CLOSURE_PCT", 0)) for r in self.layer_rows)
                shrub_cc = _int(vcpe.get("SHRUB_CROWN_CLOSURE", 0))
                herb = _int(vcpe.get("HERB_COVER_PCT", 0))
                bryoid = _int(vcpe.get("BRYOID_COVER_PCT", 0))
                nonveg = sum(_int(r.get("NON_VEG_COVER_PCT", 0)) for r in self.nvce_rows)
                self.percent_left.setText(str(100 - tree_cc - shrub_cc - herb - bryoid - nonveg))
            except Exception:
                self.percent_left.setText("")
        if hasattr(self, "mensurational_data"):
            self.mensurational_data.setText(str(getattr(self, "current_label", {}).get("MENSURATIONAL_DATA", "") or ""))
        if hasattr(self, "bclcs_display"):
            for i, field in enumerate(("BCLCS_LEVEL1_CODE", "BCLCS_LEVEL2_CODE",
                                     "BCLCS_LEVEL3_CODE", "BCLCS_LEVEL4_CODE",
                                     "BCLCS_LEVEL5_CODE")):
                self.bclcs_display[i].setText(str(vcpe.get(field, "") or ""))
        if hasattr(self, "site_species"):
            layer = self._active_layer() or {}
            self.site_species.setText(str(layer.get("TREE_SPECIES_CODE", "") or ""))
            self.inv_std_display.setText(str(fco.get("INVENTORY_STANDARD_CODE", "") or ""))

    def _new(self) -> None:
        path = ask_new_map(self)
        if path is not None:
            open_map_window(path)

    def _open(self) -> None:
        path = ask_open_map(self)
        if path is not None:
            open_map_window(path)

    def closeEvent(self, event) -> None:  # noqa: N802
        if self.path is not None and self.dirty:
            answer = QMessageBox.question(
                self, "Close map",
                f"Save the changes to {self.path.name} before closing?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel, QMessageBox.Save)
            if answer == QMessageBox.Cancel:
                event.ignore()
                return
            if answer == QMessageBox.Save and not self._save():
                event.ignore()
                return
        if self in _OPEN_MAP_WINDOWS:
            _OPEN_MAP_WINDOWS.remove(self)
        event.accept()

    def _load(self, path: Path) -> None:
        path = Path(path)
        try:
            fco = db.read_rows(path, "FOREST_COVER_OBJECT")
            vcpe = db.read_rows(path, "VEGETATION_COVER_POLYGON_EST")
        except Exception as exc:
            QMessageBox.critical(self, "Open failed", str(exc))
            return
        self.path = path
        self.rows = {}
        vcpe_by_fid = {row.get("FOREST_COVER_OBJECT_ID", ""): row for row in vcpe}
        for row in fco:
            fid = _int(row.get("FOREST_COVER_OBJECT_ID"))
            self.rows[fid] = {"fco": row, "vcpe": vcpe_by_fid.get(str(fid), {})}
        self.polygon_order = sorted(
            self.rows, key=lambda fid: self._polygon_sort_key(fid))
        self._build_classified_index()
        self._load_polygon(self.polygon_order[0] if self.polygon_order else None)
        self.setWindowTitle(f"VRI Editor — {path.name}")
        self.statusBar().showMessage(f"{len(self.rows):,} polygons — {path}")

    def _polygon_sort_key(self, fid: int) -> tuple[int, float, int]:
        number = (self.rows[fid]["fco"].get("POLYGON_NUMBER", "") or "").strip()
        try:
            return (0, float(number), fid)
        except ValueError:
            return (1, 0.0, fid)

    def _build_classified_index(self) -> None:
        """Index the polygons that already carry a classification."""
        classified: set[int] = set()
        if self.path is None:
            self.classified_fids = classified
            return
        try:
            for table in ("TREE_COVER_LAYER_ESTIMATED", "LAND_COVER_COMPONENT_EST",
                          "NON_VEGETATIVE_COVER_EST"):
                for row in db.read_rows(self.path, table):
                    classified.add(_int(row.get("FOREST_COVER_OBJECT_ID")))
        except Exception:
            pass
        self.classified_fids = classified

    def _flush_pending(self) -> None:
        """Write pending polygon level values into the polygon being left."""
        if self.current_fid is None:
            return
        vcpe = self.rows.get(self.current_fid, {}).get("vcpe")
        if vcpe is None:
            return
        if self.pending_reference_year is not None:
            vcpe["REFERENCE_YEAR"] = self.pending_reference_year
        if self.pending_snags is not None:
            vcpe["VRI_DEAD_STEMS_PER_HA"] = self.pending_snags

    def _goto_classified(self, delta: int, land_on: int = 0) -> None:
        """Jump to the previous or next polygon that has a classification.

        ``land_on`` picks the entry to select on arrival: 0 is the first level,
        -1 the last level of the polygon.
        """
        if not self.polygon_order:
            return
        if self.current_fid in self.polygon_order:
            index = self.polygon_order.index(self.current_fid)
        else:
            index = -1 if delta > 0 else 0
        step = 1 if delta > 0 else -1
        index += step
        while 0 <= index < len(self.polygon_order):
            fid = self.polygon_order[index]
            if fid in self.classified_fids:
                self._load_polygon(fid)
                entries = self._entries()
                if entries:
                    self.cursor_layer, self.cursor_level = entries[land_on]
                    self._sync_layer_selection()
                    self._focus_level()
                self._update_cursor_display()
                return
            index += step
        self.statusBar().showMessage("No more polygons with a classification")

    def _load_polygon(self, fid: int | None) -> None:
        if fid is None or fid not in self.rows:
            return
        if fid != self.current_fid:
            if self.dirty and self.current_fid is not None:
                answer = QMessageBox.question(
                    self, "Unsaved changes",
                    f"Save the changes to polygon "
                    f"{self.rows.get(self.current_fid, {}).get('fco', {}).get('POLYGON_NUMBER', '')} "
                    "before moving on?",
                    QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
                if answer == QMessageBox.Cancel:
                    return
                if answer == QMessageBox.Save:
                    self._save()
                    if self.dirty:
                        return
            self._flush_pending()
        self.current_fid = fid
        record = self.rows[fid]
        self.loading = True
        try:
            for name, widget in self.widgets.items():
                prefix, field = name.split(".", 1)
                value = record.get(prefix, {}).get(field, "")
                widget.setText(value)
        finally:
            self.loading = False
        try:
            tcl = [r for r in db.read_rows(self.path, "TREE_COVER_LAYER_ESTIMATED")
                   if _int(r.get("FOREST_COVER_OBJECT_ID")) == fid]
            tse = db.read_rows(self.path, "TREE_SPECIES_ESTIMATED")
            lcc = [r for r in db.read_rows(self.path, "LAND_COVER_COMPONENT_EST")
                   if _int(r.get("FOREST_COVER_OBJECT_ID")) == fid]
            nvce = [r for r in db.read_rows(self.path, "NON_VEGETATIVE_COVER_EST")
                    if _int(r.get("FOREST_COVER_OBJECT_ID")) == fid]
            labels = [r for r in db.read_rows(self.path, "Polygon_Label")
                      if _int(r.get("FOREST_COVER_OBJECT_ID")) == fid]
            self.current_label = labels[0] if labels else {}
        except Exception as exc:
            QMessageBox.critical(self, "Read failed", str(exc))
            return
        tcl.sort(key=lambda r: _int(r.get("LAYER_ORDER"), 99))
        self.original_children = {
            "TREE_COVER_LAYER_ESTIMATED": tcl,
            "LAND_COVER_COMPONENT_EST": lcc,
            "NON_VEGETATIVE_COVER_EST": nvce,
        }
        self.layer_rows = [dict(r) for r in tcl]
        self.lcc_rows = [dict(r) for r in lcc]
        self.nvce_rows = [dict(r) for r in nvce]
        layer_ids = {_int(r.get("TREE_COVER_LAYER_ESTIMATED_ID")) for r in tcl}
        self.species_original = {}
        self.species_cache = {}
        for row in tse:
            lid = _int(row.get("TREE_COVER_LAYER_ESTIMATED_ID"))
            if lid in layer_ids:
                self.species_original.setdefault(lid, []).append(row)
        self.dirty = False
        self.cursor_layer = 0
        self.cursor_level = 0
        self.active_layer_index = 0
        self.loading = False
        self.pending_snags = None
        self.pending_reference_year = None
        self.pending_snags: str | None = None
        self.pending_reference_year: str | None = None
        self.map_label.setText(
            f"{self.path.name} — polygon {record.get('fco', {}).get('POLYGON_NUMBER', '')}"
            f"  ({len(self.classified_fids):,} classified of {len(self.rows):,})")
        self.geometry_name.setText(self.path.stem)
        self.loading = True
        try:
            self.lcc_panel.load(self.lcc_rows)
            self.nvce_panel.load(self.nvce_rows)
            self.cursor_level = 0
            self.nvce_panel.current = 0
            self._level0_fields = None
        finally:
            self.loading = False
        self._refresh_layer_combo()
        self._update_displays()
        self._update_cursor_display()
        self._update_warnings()

    def _assign_child_ids(self, rows: list[dict[str, Any]], table: str,
                          id_field: str, parent_field: str,
                          parent_value: Any) -> None:
        """Give new child rows a negative id, an objectid and a parent."""
        if not rows:
            return
        existing = db.read_rows(self.path, table)
        ids = [_int(row.get(id_field)) for row in existing]
        objects = [_int(row.get("OBJECTID")) for row in existing]
        for row in rows:
            ids.append(_int(row.get(id_field)))
            objects.append(_int(row.get("OBJECTID")))
        next_id = min(ids) - 1
        next_objectid = max(objects) + 1
        for row in rows:
            if not _int(row.get(id_field)):
                row[id_field] = next_id
                next_id -= 1
            if not _int(row.get("OBJECTID")):
                row["OBJECTID"] = next_objectid
                next_objectid += 1
            row[parent_field] = parent_value

    def _entries(self) -> list[tuple[int, int]]:
        """All (layer, non-veg level) positions available in the current polygon.

        A level is a non-vegetated level (1..3), not a species row: every
        species row belongs to the same level and layer. Levels are only
        added to the first tree layer, as the design sheet requires.
        """
        entries: list[tuple[int, int]] = []
        level_count = max(1, len(self.nvce_panel.rows) if hasattr(self, "nvce_panel") else len(self.nvce_rows))
        layer_count = len(self.layer_rows) or 1
        for layer_index in range(layer_count):
            levels = level_count if layer_index == 0 else 1
            for level in range(levels):
                entries.append((layer_index, level))
        return entries

    def _update_cursor_display(self) -> None:
        entries = self._entries()
        if not entries:
            self.entry_display.setText(
                f"Polygon {self.current_fid or 0} of {len(self.rows)}   no layer")
            return
        self.cursor_layer = max(0, min(len(self.layer_rows) - 1, self.cursor_layer))
        layer_index = min(self.cursor_layer, len(entries) - 1)
        level = min(self.cursor_level, max(0, len(entries[layer_index]) if False else 0))
        if layer_index < len(self.layer_rows):
            layer = self.layer_rows[layer_index]
        else:
            layer = {}
        layer_label = str(layer_index + 1)
        level = self.cursor_level + 1
        if self.nvce_rows:
            level = max(1, min(level, len(self.nvce_rows)))
        number = ""
        if self.current_fid is not None:
            number = self.rows.get(self.current_fid, {}).get("fco", {}).get(
                "POLYGON_NUMBER", "")
        self.entry_display.setText(
            f"Polygon {number or self.current_fid} of {len(self.rows)}"
            f"   Layer {layer_label}"
            f"   Level {level}")

    def _move_cursor(self, delta: int) -> None:
        """Step one level (species row) at a time: level, then layer, then polygon."""
        entries = self._entries()
        if not entries:
            self._goto_classified(delta, land_on=0 if delta > 0 else -1)
            return
        current = (self.cursor_layer, self.cursor_level)
        index = entries.index(current) if current in entries else (
            0 if delta > 0 else len(entries) - 1)
        target = index + delta
        if target < 0 or target >= len(entries):
            # run off the end of this polygon: continue on the neighbouring polygon
            self._goto_classified(delta, land_on=-1 if delta < 0 else 0)
            return
        self.cursor_layer, self.cursor_level = entries[target]
        self._sync_layer_selection()
        self._focus_level()
        self._update_cursor_display()

    def _focus_level(self) -> None:
        """Sync the non-vegetated panel to the level under the cursor."""
        nv = self.nvce_panel
        if 0 <= self.cursor_level < len(nv.rows) or not nv.rows:
            nv.current = max(0, min(max(0, len(nv.rows) - 1), self.cursor_level))
            nv._show()
        self._apply_level_mode()
        self._update_cursor_display()

    def _sync_layer_selection(self) -> None:
        if self.layer_combo.count() and 0 <= self.cursor_layer < self.layer_combo.count():
            self.layer_combo.setCurrentIndex(self.cursor_layer)

    def _goto_edge(self, direction: int) -> None:
        """Jump to the first or last polygon that has a classification."""
        available = [fid for fid in self.polygon_order if fid in self.classified_fids]
        if not available:
            self.statusBar().showMessage("No polygons with a classification")
            return
        fid = available[0] if direction < 0 else available[-1]
        self._load_polygon(fid)
        self.cursor_layer = 0
        self.cursor_level = 0
        self.active_layer_index = 0
        self.loading = False
        self.pending_snags: str | None = None
        self.pending_reference_year: str | None = None
        self._update_cursor_display()

    def _focus_species(self) -> None:
        """Put the cursor on the first species of the active layer."""
        self.cursor_layer = max(0, self.layer_combo.currentIndex())
        self.cursor_level = 0
        self._update_cursor_display()
        self.species_panel.setFocus()

    DATE_FORMATS = (
        "%m/%d/%Y %H:%M:%S", "%m/%d/%Y", "%m/%d/%y %H:%M:%S", "%m/%d/%y",
        "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d",
        "%d/%m/%Y %H:%M:%S", "%d/%m/%Y", "%d/%m/%y", "%Y/%m/%d",
    )

    def _normalise_date(self, text: str) -> str:
        """Return the value in a format the writer always understands.

        A date that cannot be parsed is returned unchanged so the caller can
        refuse the save instead of silently erasing the stored value.
        """
        from datetime import datetime
        value = (text or "").strip()
        if not value:
            return ""
        for fmt in self.DATE_FORMATS:
            try:
                parsed = datetime.strptime(value, fmt)
            except ValueError:
                continue
            return parsed.strftime("%Y-%m-%dT%H:%M:%S")
        return value

    def _is_known_date(self, value: str) -> bool:
        from datetime import datetime
        text = (value or "").strip()
        if not text:
            return True
        for fmt in self.DATE_FORMATS:
            try:
                datetime.strptime(text, fmt)
            except ValueError:
                continue
            return True
        return False

    def _copy_polygon(self) -> None:
        """Copy the current polygon classification to the internal clipboard."""
        if self.current_fid is None or self.path is None:
            return
        self._store_species()
        record = self.rows.get(self.current_fid, {})
        self.clipboard = {
            "fco": dict(record.get("fco", {})),
            "vcpe": dict(record.get("vcpe", {})),
            "layers": [dict(r) for r in self.layer_rows],
            "species": {lid: [dict(r) for r in rows]
                        for lid, rows in self.species_cache.items()},
            "lcc": [dict(r) for r in self.lcc_rows],
            "nvce": [dict(r) for r in self.nvce_rows],
        }
        self.statusBar().showMessage(
            f"Copied polygon {record.get('fco', {}).get('POLYGON_NUMBER', '')} "
            "— use Edit > Paste on another polygon")

    def _paste_polygon(self) -> None:
        if self.clipboard is None or self.current_fid is None:
            return
        clipboard = self.clipboard
        for name, widget in self.widgets.items():
            prefix, field = name.split(".", 1)
            if field == "POLYGON_NUMBER":
                continue  # the target keeps its own polygon number
            source = clipboard.get(prefix, {})
            if field in source:
                widget.setText(str(source.get(field, "") or ""))
        self.layer_rows = [dict(r) for r in clipboard.get("layers", [])]
        for row in self.layer_rows:
            row["FOREST_COVER_OBJECT_ID"] = self.current_fid
        self.species_cache = {lid: [dict(r) for r in rows]
                              for lid, rows in clipboard.get("species", {}).items()}
        self.lcc_rows = [dict(r) for r in clipboard.get("lcc", [])]
        self.nvce_rows = [dict(r) for r in clipboard.get("nvce", [])]
        self._refresh_layer_combo()
        self.lcc_panel.load(self.lcc_rows)
        self.nvce_panel.load(self.nvce_rows)
        self.dirty = True
        self.statusBar().showMessage("Pasted classification — press Save to store it")

    def _find_polygon(self) -> None:
        if not self.polygon_order:
            return
        text, accepted = QInputDialog.getText(
            self, "Find polygon", "Polygon number or opening ID:")
        if not accepted or not text.strip():
            return
        needle = text.strip().lower()
        for fid in self.polygon_order:
            record = self.rows[fid]
            if (record["fco"].get("POLYGON_NUMBER", "") or "").strip().lower() == needle:
                self._load_polygon(fid)
                return
            if (record["fco"].get("OPENING_ID", "") or "").strip().lower() == needle:
                self._load_polygon(fid)
                return
        QMessageBox.information(self, "Find polygon", f"No polygon matches {text!r}.")

    def _undo(self) -> None:
        """Restore the database from the backup taken by the previous save."""
        if self.last_backup is None or not Path(self.last_backup).is_file():
            self.statusBar().showMessage("Nothing to undo")
            return
        if self.path is None:
            return
        if QMessageBox.question(
            self, "Undo", "Restore the database from the previous backup?"
        ) != QMessageBox.Yes:
            return
        import shutil
        restore = Path(self.last_backup)
        try:
            shutil.copy2(self.path, db.backup_path(self.path))
            shutil.copy2(restore, self.path)
        except Exception as exc:
            QMessageBox.critical(self, "Undo failed", str(exc))
            return
        self.last_backup = None
        self._load(self.path)
        self.statusBar().showMessage(f"Restored {restore.name}")

    def _toggle_grid(self) -> None:
        self.show_grid = not self.show_grid
        self.geometry_map.setStyleSheet(
            "border: 1px solid #999; color: #666;"
            + ("background-color: #eef3f7;" if self.show_grid else ""))
        self.statusBar().showMessage(
            "Grid shown" if self.show_grid else "Grid hidden")

    def _mark_changed(self) -> None:
        if self.loading:
            return
        self.dirty = True

    def _active_layer(self) -> dict[str, Any] | None:
        if not self.layer_rows:
            return None
        if 0 <= self.active_layer_index < len(self.layer_rows):
            return self.layer_rows[self.active_layer_index]
        return self.layer_rows[0]

    def _refresh_layer_combo(self) -> None:
        current = self.active_layer_index
        self.layer_combo.blockSignals(True)
        self.layer_combo.clear()
        for index, row in enumerate(self.layer_rows):
            order = row.get("LAYER_ORDER", "") or str(index + 1)
            level = row.get("LAYER_LEVEL_CODE", "") or ""
            species = row.get("TREE_SPECIES_CODE", "") or ""
            label = f"{order}"
            if level:
                label += f" ({level})"
            if species:
                label += f" {species}"
            self.layer_combo.addItem(label, index)
        index = current if 0 <= current < len(self.layer_rows) else 0
        self.layer_combo.setCurrentIndex(index if self.layer_combo.count() else -1)
        self.layer_combo.blockSignals(False)
        self.active_layer_index = index
        self.layer_count.setText(f"{self.layer_combo.count() or 0} of {len(self.layer_rows)}")
        self._load_active_layer()

    def _load_active_layer(self) -> None:
        layer = self._active_layer()
        vcpe = self.rows.get(self.current_fid or -1, {}).get("vcpe", {})
        reference_year = str(vcpe.get("REFERENCE_YEAR", "") or "")
        snags = str(vcpe.get("VRI_DEAD_STEMS_PER_HA", "") or "")
        dead = bool(layer) and str(layer.get("LAYER_LEVEL_CODE", "")).upper() == "D"
        self.loading = True
        try:
            self.layer_details.load(layer or {}, reference_year, snags)
            self.snags_display.setText(snags or "")
            if dead:
                # a dead layer carries the snags of the living layer as its density
                self.mensurational_panel.density_target = "snags"
                self.mensurational_panel.load(layer or {}, density=snags)
            else:
                self.mensurational_panel.density_target = "layer"
                self.mensurational_panel.load(layer or {})
            self.species_detail.load(self._active_species())
            self.species_panel.load(self._active_species())
            self.site_index.setText(str((layer or {}).get("ESTIMATED_SITE_INDEX", "") or ""))
            self.site_source.setText(str((layer or {}).get("ESTIMATED_SINDEX_SOURCE_CODE", "") or ""))
        finally:
            self.loading = False
        self._update_layer_editability()

    def _first_living_index(self) -> int:
        for index, layer in enumerate(self.layer_rows):
            if str(layer.get("LAYER_LEVEL_CODE", "")).upper() != "D":
                return index
        return -1

    def _update_layer_editability(self) -> None:
        """Apply the layer rules: dead layers have fewer editable fields and
        the reference year and snags belong to the first living layer."""
        layer = self._active_layer()
        alive = bool(layer) and str(layer.get("LAYER_LEVEL_CODE", "")).upper() != "D"
        first_living = self._first_living_index()
        on_first = self.active_layer_index == first_living
        details = self.layer_details
        for widget in (details.crown, details.pattern, details.complexity,
                       details.species_source):
            widget.setEnabled(alive)
        details.reference_year.setEnabled(alive and on_first)
        details.snags.setEnabled(alive and on_first)
        self.mensurational_panel.basal.setEnabled(True)
        self.mensurational_panel.basal_source.setEnabled(True)
        self.mensurational_panel.density.setEnabled(True)
        self.mensurational_panel.density_source.setEnabled(True)

    def _active_species(self) -> list[dict[str, Any]]:
        layer = self._active_layer()
        if layer is None:
            return []
        lid = _int(layer.get("TREE_COVER_LAYER_ESTIMATED_ID"))
        rows = self.species_cache.get(lid)
        if rows is None:
            rows = self.species_original.get(lid, [])
        return [dict(row) for row in rows]

    def _store_layer(self) -> None:
        """Copy the tree-specific and mensurational panels back into the layer row."""
        layer = self._active_layer()
        if layer is None:
            return
        identity = ("TREE_COVER_LAYER_ESTIMATED_ID", "OBJECTID",
                    "FOREST_COVER_OBJECT_ID")
        details = self.layer_details.values()
        mensurational = self.mensurational_panel.values()
        for field in ("CROWN_CLOSURE_PCT", "COVER_PATTERN_CODE",
                      "VERTICAL_COMPLEXITY_CODE", "DATA_SOURCE_INTERPRETED_CODE"):
            layer[field] = details.get(field, layer.get(field, ""))
        for field in ("BASAL_AREA", "DATA_SOURCE_BASAL_AREA_CODE",
                      "DATA_SRC_VRI_LIVE_STEM_HA_CODE"):
            layer[field] = mensurational.get(field, layer.get(field, ""))
        if self.site_index.text().strip() or self.site_source.text().strip():
            layer["ESTIMATED_SITE_INDEX"] = self.site_index.text().strip()
            layer["ESTIMATED_SINDEX_SOURCE_CODE"] = self.site_source.text().strip()
        if self.mensurational_panel.density_target == "snags":
            # a dead layer carries the snags of the living layer as its density
            density = self.mensurational_panel.density.text().strip()
            layer["VRI_LIVE_STEMS_PER_HA"] = density
            self.pending_snags = density
        else:
            layer["VRI_LIVE_STEMS_PER_HA"] = mensurational.get(
                "VRI_LIVE_STEMS_PER_HA", layer.get("VRI_LIVE_STEMS_PER_HA", ""))
        if self.layer_details.snags.isEnabled():
            self.pending_snags = self.layer_details.snags.text().strip()
        if self.layer_details.reference_year.isEnabled():
            self.pending_reference_year = self.layer_details.reference_year.text().strip()

    def _store_species(self) -> None:
        self._store_layer()
        layer = self._active_layer()
        if layer is None:
            return
        lid = _int(layer.get("TREE_COVER_LAYER_ESTIMATED_ID"))
        rows = self.species_panel.values()
        detail = self.species_detail.values()
        for index, row in enumerate(rows):
            if index < len(detail):
                for field in ("AGE", "HEIGHT", "DATA_SOURCE_AGE_CODE",
                              "DATA_SOURCE_HEIGHT_CODE"):
                    if detail[index].get(field):
                        row[field] = detail[index][field]
            row["TREE_COVER_LAYER_ESTIMATED_ID"] = lid
        self.species_cache[lid] = rows

    def _layer_changed(self, index: int = -1) -> None:
        if self.current_fid is None:
            return
        # flush the layer that is being left before switching
        self._store_species()
        if index >= 0:
            self.active_layer_index = index
        self._load_active_layer()
        self.cursor_layer = self.active_layer_index
        self._update_displays()
        self._update_cursor_display()

    def _add_layer(self, level: str = "1") -> None:
        if self.current_fid is None:
            return
        self._store_species()
        stored = db.read_rows(self.path, "TREE_COVER_LAYER_ESTIMATED")
        ids = [_int(row.get("TREE_COVER_LAYER_ESTIMATED_ID")) for row in stored]
        ids += [_int(row.get("TREE_COVER_LAYER_ESTIMATED_ID")) for row in self.layer_rows]
        new_id = min(ids) - 1
        objectids = [_int(row.get("OBJECTID")) for row in stored]
        objectids += [_int(row.get("OBJECTID")) for row in self.layer_rows]
        objectid = max(objectids) + 1
        # a new layer is a fresh filler screen: same polygon, empty fields
        row = {
            "TREE_COVER_LAYER_ESTIMATED_ID": new_id,
            "OBJECTID": objectid,
            "LAYER_ORDER": str(len(self.layer_rows) + 1),
            "LAYER_LEVEL_CODE": level,
            "FOREST_COVER_OBJECT_ID": self.current_fid,
        }
        self.layer_rows.append(row)
        self._refresh_layer_combo()
        # switching flushes the layer we leave, then loads the new one
        self.layer_combo.setCurrentIndex(len(self.layer_rows) - 1)
        self.dirty = True

    def _delete_layer(self) -> None:
        if self.current_fid is None or not self.layer_rows:
            return
        self._store_species()
        index = self.active_layer_index
        if index < 0 or index >= len(self.layer_rows):
            return
        removed = self.layer_rows.pop(index)
        lid = _int(removed.get("TREE_COVER_LAYER_ESTIMATED_ID"))
        self.species_cache.pop(lid, None)
        self.active_layer_index = min(index, len(self.layer_rows) - 1) if self.layer_rows else 0
        self._refresh_layer_combo()
        self.dirty = True

    def _add_species_layer(self) -> None:
        """Add a tree layer and put the cursor on its species composition."""
        self._add_layer("1")
        self._focus_species()

    def _add_dead_layer(self) -> None:
        """Add a dead tree layer (level D)."""
        self._add_layer("D")

    def _toggle_dead_layer(self) -> None:
        layer = self._active_layer()
        if layer is None:
            return
        layer["LAYER_LEVEL_CODE"] = "D" if layer.get("LAYER_LEVEL_CODE") != "D" else "1"
        self._refresh_layer_combo()
        self.dirty = True

    def _add_polygon(self) -> None:
        if self.path is None:
            QMessageBox.warning(self, "Add polygon", "Open a map first.")
            return
        try:
            fid = db.add_polygon(self.path)
        except Exception as exc:
            QMessageBox.critical(self, "Add polygon failed", str(exc))
            return
        self._load(self.path)
        self._select_fid(fid)

    def _delete_polygon(self) -> None:
        if self.path is None or self.current_fid is None:
            return
        if len(self.rows) <= 1:
            QMessageBox.warning(self, "Delete polygon", "A map must keep at least one polygon.")
            return
        record = self.rows[self.current_fid]["fco"]
        number = record.get("POLYGON_NUMBER", str(self.current_fid))
        if QMessageBox.question(
            self, "Delete polygon",
            f"Delete polygon {number} and all of its child rows?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        ) != QMessageBox.Yes:
            return
        try:
            db.delete_polygon(self.path, self.current_fid)
        except Exception as exc:
            QMessageBox.critical(self, "Delete polygon failed", str(exc))
            return
        self._load(self.path)

    def _collect_table_edits(self, table: str, id_field: str, object_field: str,
                             original: list[dict[str, str]],
                             current: list[dict[str, Any]],
                             parent_field: str | None = None) -> list[str]:
        orig = {_int(row.get(id_field)): row for row in original}
        cur = {_int(row.get(id_field)): row for row in current}
        edits: list[str] = []
        for key in sorted(set(orig) - set(cur)):
            edits.append(db.delete_line(table, id_field, key))
        for key in sorted(set(cur) - set(orig)):
            row = dict(cur[key])
            row[id_field] = key
            edits.append(db.edit_line("I", table, "", "", row))
        for key in sorted(set(cur) & set(orig)):
            row = dict(cur[key])
            row.pop(id_field, None)
            old = orig[key]
            changed: dict[str, Any] = {}
            for field, value in row.items():
                if str(value).strip() != str(old.get(field, "")).strip():
                    changed[field] = value
            if parent_field:
                value = cur[key].get(parent_field, "")
                if str(value).strip() != str(old.get(parent_field, "")).strip():
                    changed[parent_field] = value
            if changed:
                edits.append(db.edit_line("U", table, id_field, key, changed))
        return edits

    def _save(self) -> bool:
        if self.path is None or self.current_fid is None:
            return False
        extra = self.cursor_level > 0
        if not extra:
            self._store_species()
        fco: dict[str, Any] = {}
        vcpe: dict[str, Any] = {}
        for name, widget in self.widgets.items():
            prefix, field = name.split(".", 1)
            if extra and self._level0_fields is not None:
                value = self._level0_fields.get(name, "")
            else:
                value = widget.text()
            (fco if prefix == "fco" else vcpe)[field] = value.strip()
        if not fco.get("POLYGON_NUMBER"):
            QMessageBox.warning(self, "Save", "Polygon number cannot be empty.")
            return False
        stored = (self.rows.get(self.current_fid, {}).get("fco", {})
                  .get("POLYGON_NUMBER", "") or "").strip()
        new_number = fco["POLYGON_NUMBER"].strip()
        other = db.poly_number_conflict(self.rows, self.current_fid, new_number)
        if other is not None:
            QMessageBox.warning(
                self, "Save",
                f"Polygon number {new_number} is already used by another polygon "
                f"(FOREST_COVER_OBJECT_ID {other}). Nothing was saved.")
            return False
        if stored and new_number != stored:
            if QMessageBox.question(
                self, "Rename polygon",
                f"Rename polygon {stored} to {new_number}?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
            ) != QMessageBox.Yes:
                number_field = self.widgets["fco.POLYGON_NUMBER"]
                number_field.blockSignals(True)
                number_field.setText(stored)
                number_field.blockSignals(False)
                return False
        if self.pending_reference_year is not None:
            vcpe["REFERENCE_YEAR"] = self.pending_reference_year
        if self.pending_snags is not None:
            vcpe["VRI_DEAD_STEMS_PER_HA"] = self.pending_snags
        bad_dates = []
        for name, value in list(fco.items()) + list(vcpe.items()):
            if not name.endswith("_YEAR") or "_START" not in name and "_END" not in name:
                continue
            normalised = self._normalise_date(value)
            if normalised and normalised == value.strip() and not self._is_known_date(value):
                bad_dates.append(f"{name}={value!r}")
            else:
                (fco if name in fco else vcpe)[name] = normalised
        if bad_dates:
            QMessageBox.warning(
                self, "Unrecognised date",
                "These dates were not understood and were not saved:\n"
                + "\n".join(bad_dates))
            return False
        edits = [
            db.edit_line("U", "FOREST_COVER_OBJECT", "FOREST_COVER_OBJECT_ID",
                         self.current_fid, fco),
            db.edit_line("U", "VEGETATION_COVER_POLYGON_EST", "FOREST_COVER_OBJECT_ID",
                         self.current_fid, vcpe),
        ]
        self._assign_child_ids(self.layer_rows, "TREE_COVER_LAYER_ESTIMATED",
                               "TREE_COVER_LAYER_ESTIMATED_ID",
                               "FOREST_COVER_OBJECT_ID", self.current_fid)
        lcc_rows = self.lcc_panel.values()
        self._assign_child_ids(lcc_rows, "LAND_COVER_COMPONENT_EST",
                               "LAND_COVER_COMPONENT_EST_ID",
                               "FOREST_COVER_OBJECT_ID", self.current_fid)
        nvce_errors = self.nvce_panel.validate()
        if nvce_errors:
            answer = QMessageBox.warning(
                self, "Non vegetated",
                "Non-vegetated validation errors:\n\n" + "\n".join(nvce_errors)
                + "\n\nSave anyway?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if answer != QMessageBox.Yes:
                return False
        nvce_rows = self.nvce_panel.values()
        self._assign_child_ids(nvce_rows, "NON_VEGETATIVE_COVER_EST",
                               "NON_VEGETATIVE_COVER_EST_ID",
                               "FOREST_COVER_OBJECT_ID", self.current_fid)
        edits += self._collect_table_edits(
            "TREE_COVER_LAYER_ESTIMATED", "TREE_COVER_LAYER_ESTIMATED_ID", "OBJECTID",
            self.original_children.get("TREE_COVER_LAYER_ESTIMATED", []),
            self.layer_rows, "FOREST_COVER_OBJECT_ID")
        edits += self._collect_table_edits(
            "LAND_COVER_COMPONENT_EST", "LAND_COVER_COMPONENT_EST_ID", "OBJECTID",
            self.original_children.get("LAND_COVER_COMPONENT_EST", []),
            lcc_rows, "FOREST_COVER_OBJECT_ID")
        edits += self._collect_table_edits(
            "NON_VEGETATIVE_COVER_EST", "NON_VEGETATIVE_COVER_EST_ID", "OBJECTID",
            self.original_children.get("NON_VEGETATIVE_COVER_EST", []),
            nvce_rows, "FOREST_COVER_OBJECT_ID")
        layer_ids = {_int(row.get("TREE_COVER_LAYER_ESTIMATED_ID")) for row in self.layer_rows}
        for lid in sorted(set(self.species_original) | set(self.species_cache)):
            if lid not in layer_ids:
                for row in self.species_original.get(lid, []):
                    edits.append(db.delete_line(
                        "TREE_SPECIES_ESTIMATED", "TREE_SPECIES_ESTIMATED_ID",
                        _int(row.get("TREE_SPECIES_ESTIMATED_ID"))))
                continue
            current = self.species_cache.get(lid, self.species_original.get(lid, []))
            self._assign_child_ids(current, "TREE_SPECIES_ESTIMATED",
                                   "TREE_SPECIES_ESTIMATED_ID",
                                   "TREE_COVER_LAYER_ESTIMATED_ID", lid)
            edits += self._collect_table_edits(
                "TREE_SPECIES_ESTIMATED", "TREE_SPECIES_ESTIMATED_ID", "OBJECTID",
                self.species_original.get(lid, []), current,
                "TREE_COVER_LAYER_ESTIMATED_ID")
        try:
            backup, count = db.save(self.path, edits)
        except Exception as exc:
            QMessageBox.critical(self, "Save failed", str(exc))
            return False
        self.rows[self.current_fid]["fco"].update(fco)
        self.rows[self.current_fid]["vcpe"].update(vcpe)
        self.dirty = False
        self.last_backup = backup
        self._build_classified_index()
        self.statusBar().showMessage(
            f"Saved {count} row(s)" + (f"; backup {backup.name}" if backup else ""))
        self._update_warnings()
        return True

    def _select_fid(self, fid: int) -> None:
        self._load_polygon(fid)

    def _import_geometry(self) -> None:
        if self.path is None:
            QMessageBox.warning(self, "Geometry", "Open a VRI map first.")
            return
        if not self._save():
            return
        dialog = GeometryImportDialog(self)
        if dialog.exec_() != QDialog.Accepted:
            return
        from . import spatial
        user = self.rows[self.current_fid]["fco"].get("INTERPRETER", "") if self.current_fid else ""
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            if dialog.polygon_mode.isChecked():
                backup, updated, summary = spatial.import_geometry(
                    self.path, dialog.poly_path.text().strip(),
                    id_field=dialog.id_field.text().strip() or "POLYGON_ID",
                    create_missing=dialog.create_missing.isChecked(), user=user)
            else:
                backup, updated, summary = spatial.import_geometry(
                    self.path, dialog.line_path.text().strip(),
                    point_path=dialog.point_path.text().strip(),
                    point_id_field=dialog.point_id_field.text().strip() or "POLYGON_ID",
                    create_missing=dialog.create_missing.isChecked(), user=user)
        except Exception as exc:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Geometry import failed", str(exc))
            return
        finally:
            QApplication.restoreOverrideCursor()
        fid = self.current_fid
        self._load(self.path)
        if fid is not None:
            self._select_fid(fid)
        backup_text = f"\nBackup: {backup}" if backup else ""
        QMessageBox.information(self, "Geometry import", f"{summary}.{backup_text}")

    def _import_results(self) -> None:
        if self.path is None or self.current_fid is None:
            QMessageBox.warning(self, "RESULTS", "Open a VRI map first.")
            return
        if not self._save():
            return
        start = Path.home() / "Forest_VRI_validator" / "RESULTS_MDB"
        if not start.is_dir():
            start = self.path.parent
        res_path, _ = QFileDialog.getOpenFileName(
            self, "Choose RESULTS database", str(start), "Access databases (*.mdb *.accdb)")
        if not res_path:
            return
        dialog = ResultsDialog(Path(res_path), self)
        if not dialog.rows:
            return
        if dialog.exec_() != QDialog.Accepted:
            return
        from . import results
        user = self.rows[self.current_fid]["fco"].get("INTERPRETER", "")
        fid = self.current_fid
        if dialog.mode == "unique":
            QApplication.setOverrideCursor(Qt.WaitCursor)
            try:
                applied, skipped, updated = results.tie_unique(
                    self.path, res_path,
                    replace_children=dialog.replace.isChecked(), user=user)
            except Exception as exc:
                QApplication.restoreOverrideCursor()
                QMessageBox.critical(self, "RESULTS tie failed", str(exc))
                return
            finally:
                QApplication.restoreOverrideCursor()
        elif dialog.mode == "geometry":
            QApplication.setOverrideCursor(Qt.WaitCursor)
            try:
                applied, skipped, updated = results.tie_by_geometry(
                    self.path, res_path,
                    replace_children=dialog.replace.isChecked(), user=user,
                    allow_duplicates=dialog.allow_duplicates.isChecked())
            except Exception as exc:
                QApplication.restoreOverrideCursor()
                QMessageBox.critical(self, "RESULTS tie failed", str(exc))
                return
            finally:
                QApplication.restoreOverrideCursor()
            self._load(self.path)
            self._select_fid(fid)
            detail = "\n".join(applied[:8])
            if len(applied) > 8:
                detail += f"\n… and {len(applied) - 8} more"
            skipped_text = "\n".join(skipped[:8])
            if len(skipped) > 8:
                skipped_text += f"\n… and {len(skipped) - 8} more"
            QMessageBox.information(
                self, "RESULTS tie",
                f"Applied {len(applied)} unique opening(s), updated {updated} row(s)."
                f"\nSkipped {len(skipped)}.\n\n{detail}"
                + (f"\n\nSkipped:\n{skipped_text}" if skipped else ""))
            return
        row = dialog.selected()
        if row is None:
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            backup, updated, summary = results.apply_to_polygon(
                self.path, self.current_fid, res_path,
                row["map_id"], row["polygon_id"],
                replace_children=dialog.replace.isChecked(), user=user)
        except Exception as exc:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "RESULTS import failed", str(exc))
            return
        finally:
            QApplication.restoreOverrideCursor()
        self._load(self.path)
        self._select_fid(fid)
        backup_text = f"\nBackup: {backup}" if backup else ""
        QMessageBox.information(
            self, "RESULTS import",
            f"Applied {summary}.\nUpdated {updated} row(s).{backup_text}")

    def _recalculate(self) -> None:
        """Recalculate derived fields (BCLCS, layer rank, LCC order), as the validator does.

        Shows how many rows would change per category first; writes only after the
        user confirms, and always after making a backup.
        """
        if self.path is None or not self._save():
            return
        from vri_validator.codes import CodeBook, DEFAULT_CODES
        from vri_validator.derive import derive_updates
        from vri_validator.model import load_dataset
        from vri_validator.species import species_type, species_types
        from vri_validator.writeback import apply_updates
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            codes = CodeBook(DEFAULT_CODES)
            types = species_types(codes)
            dataset = load_dataset(str(self.path))
            updates = derive_updates(dataset, lambda code: species_type(types, code),
                                     only_changed=True)
        except Exception as exc:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Recalculation failed", str(exc))
            return
        finally:
            QApplication.restoreOverrideCursor()
        if updates.total == 0:
            QMessageBox.information(self, "Recalculation", "Derived fields are already up to date.")
            return
        text = (f"Derived rows that would change:\n"
                f"  BCLCS levels (polygons): {len(updates.vcpe)}\n"
                f"  Layer rank: {len(updates.tcl)}\n"
                f"  LCC order: {len(updates.lcc)}\n")
        if updates.skipped:
            text += f"\nSkipped (not V or I standard): {len(updates.skipped)}\n"
        text += "\nA backup of the map is made first. Apply these changes?"
        if QMessageBox.question(self, "Recalculate derived fields", text) != QMessageBox.Yes:
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            backup, count = apply_updates(self.path, updates)
        except Exception as exc:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Recalculation failed", str(exc))
            return
        finally:
            QApplication.restoreOverrideCursor()
        fid = self.current_fid
        self._load(self.path)
        if fid is not None:
            self._select_fid(fid)
        backup_text = f"\nBackup: {backup.name}" if backup else ""
        QMessageBox.information(self, "Recalculation", f"Updated {count} derived row(s).{backup_text}")

    def _export_validation_report(self) -> None:
        """Write the validation report as a text file named veg_check_<MAP>_<YYYYMMDDHHMM>.txt.

        <MAP> is the map name in the 092N025 form (from 092n025_VRIMS.mdb). The file goes
        into the map's reports folder. Nothing in the map is changed.
        """
        if self.path is None or not self._save():
            return
        from datetime import datetime
        from vri_validator.report import counts_by_code, sorted_findings
        from vri_validator.service import validate_database
        out_dir = self.path.parent / "reports"
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            result = validate_database(self.path, out_dir=out_dir, formats="csv")
        except Exception as exc:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Export Validation Report", str(exc))
            return
        finally:
            QApplication.restoreOverrideCursor()
        map_name = self.path.stem.split("_")[0].upper()
        stamp = datetime.now().strftime("%Y%m%d%H%M")
        target = out_dir / f"veg_check_{map_name}_{stamp}.txt"
        counts = result.findings.counts()
        lines = [
            f"VRI validation report: {map_name}",
            f"Map file: {self.path.name}",
            f"Created: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            f"Errors: {counts['error']}",
            f"Warnings: {counts['warning']}",
            f"Info: {counts['info']}",
            "",
            "Rules (most frequent first):",
        ]
        for code, severity, n in counts_by_code(result.findings):
            lines.append(f"  {code:<16} {severity:<8} {n}")
        lines += ["", "Findings:"]
        for f in sorted_findings(result.findings):
            where = f"polygon {f.polygon_number}" if f.polygon_number else "map"
            field = f" [{f.table}.{f.field}]" if f.table or f.field else ""
            lines.append(f"{f.severity.upper():<8} {f.code:<16} {where}{field}: "
                         f"{f.message.replace(chr(10), ' ')}")
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
            target.write_text("\n".join(lines) + "\n", encoding="utf-8")
        except OSError as exc:
            QMessageBox.critical(self, "Export Validation Report", str(exc))
            return
        self.statusBar().showMessage(f"Validation report written: {target}")
        QMessageBox.information(self, "Export Validation Report",
                                f"Written:\n{target}\n\n{len(result.findings.items)} finding(s).")

    def _validate(self) -> None:
        """Validate the map with the validator's options, then show the summary."""
        if self.path is None:
            return
        dialog = ValidateOptionsDialog(self, self.path.parent / "reports")
        if dialog.exec_() != QDialog.Accepted:
            return
        opts = dialog.values()
        if not self._save():
            return
        if opts["recalculate"]:
            self._recalculate()  # shows the change counts and asks before writing
        from vri_validator.service import validate_database
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            result = validate_database(self.path, out_dir=opts["out"],
                                       formats=opts["format"], title=opts["title"])
        except Exception as exc:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Validation failed", str(exc))
            return
        finally:
            QApplication.restoreOverrideCursor()
        ValidationSummaryDialog(self, self.path, result, opts["out"]).exec_()

def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args and args[0] == "--validate":
        # command-line validation: identical options and exit codes to vri-validate
        from vri_validator.cli import main as validate_main
        return validate_main(args[1:])
    app = QApplication(args)
    app.setApplicationName("VRI Editor")
    if "--smoke" in args:
        path = Path(args[args.index("--smoke") + 1])
        window = EditorWindow()
        window._load(path)
        print(f"smoke: {path} polygons={len(window.rows)} current={window.current_fid}")
        return 0
    start = StartWindow()
    start.show()
    if args:
        open_map_window(Path(args[0]))
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
