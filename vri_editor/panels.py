"""Compact classification panels laid out to match the VEG_Cap form design.

Every panel is a QGroupBox whose grid mirrors the rows and columns of the
design sheet (MDB_poly_clasiffication.ods). Labels sit left of their fields
and fields are only as wide as their longest real value.
"""

from __future__ import annotations

from typing import Any

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QDoubleValidator, QIntValidator, QValidator
from PyQt5.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)

from vri_validator.codes import FIELD_CODES, CodeBook

CODES = CodeBook()

# percentage ranges per the design sheet
SPECIES_PCT_RANGE = ((20, 100), (0, 50), (0, 30), (0, 25), (0, 20), (0, 18))
NON_VEG_MAX_LEVELS = 3


class CodeEdit(QLineEdit):
    """Small text box that only accepts codes from the VRIMS code list.

    The description of the current code is shown as a tooltip, matching the
    compact form-filler design where codes are typed rather than picked.
    """

    def __init__(self, code_table: str, value: str = "",
                 parent: QWidget | None = None) -> None:
        super().__init__(value, parent)
        self.code_table = code_table
        self.codes = CODES.codes(code_table)
        longest = max((len(key) for key in self.codes), default=4)
        self.setFixedWidth(max(40, longest * 8 + 14))
        self.textChanged.connect(self._update_tip)
        self._update_tip()

    def _update_tip(self) -> None:
        code = self.text().strip()
        desc = self.codes.get(code, "")
        self.setToolTip(f"{code}: {desc}" if desc else self.code_table)

    def validate(self, text: str, pos: int) -> tuple[Any, str, int]:
        if not text:
            return (QValidator.Intermediate, text, pos)
        if text in self.codes:
            return (QValidator.Acceptable, text, pos)
        return (QValidator.Invalid, text, pos)


def code_edit(table: str, column: str, value: str = "") -> QLineEdit:
    code_table = FIELD_CODES.get((table, column))
    if not code_table or not CODES.codes(code_table):
        return QLineEdit(value)
    return CodeEdit(code_table, value)


def _int_edit(value: str = "", low: int = 0, high: int = 9999) -> QLineEdit:
    edit = QLineEdit(value)
    edit.setValidator(QIntValidator(low, high, edit))
    edit.setMaxLength(len(str(high)))
    edit.setFixedWidth(len(str(high)) * 8 + 12)
    return edit


def _float_edit(value: str = "", low: float = 0.0, high: float = 99.9,
                decimals: int = 1) -> QLineEdit:
    edit = QLineEdit(value)
    edit.setValidator(QDoubleValidator(low, high, decimals, edit))
    edit.setMaxLength(len(str(int(high))) + decimals + 1)
    edit.setFixedWidth((len(str(int(high))) + decimals + 1) * 8 + 12)
    return edit


def _label(text: str, align: Qt.Alignment = Qt.AlignLeft | Qt.AlignVCenter) -> QLabel:
    label = QLabel(text)
    label.setAlignment(align)
    return label


def _grid(parent: QWidget | None = None) -> QGridLayout:
    grid = QGridLayout(parent) if parent is not None else QGridLayout()
    grid.setContentsMargins(4, 2, 4, 2)
    grid.setHorizontalSpacing(3)
    grid.setVerticalSpacing(1)
    return grid


class SpeciesComposition(QGroupBox):
    """Six species rows: number, species code, coverage %, and the % sign."""

    changed = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Species composition", parent)
        self.rows: list[dict[str, Any]] = []
        grid = _grid(self)
        self.codes: list[QLineEdit] = []
        self.percents: list[QLineEdit] = []
        for i in range(6):
            low, high = SPECIES_PCT_RANGE[i]
            code = code_edit("TREE_SPECIES_ESTIMATED", "TREE_SPECIES_CODE")
            percent = _int_edit("", low, high)
            grid.addWidget(_label(str(i + 1), Qt.AlignCenter), i, 0)
            grid.addWidget(code, i, 1)
            grid.addWidget(percent, i, 2)
            grid.addWidget(_label("%"), i, 3)
            code.textChanged.connect(self.changed.emit)
            percent.textChanged.connect(self.changed.emit)
            self.codes.append(code)
            self.percents.append(percent)
        grid.setColumnStretch(4, 1)

    def load(self, rows: list[dict[str, str]]) -> None:
        self.rows = [dict(row) for row in rows]
        for i in range(6):
            row = self.rows[i] if i < len(self.rows) else {}
            self.codes[i].setText(str(row.get("TREE_SPECIES_CODE", "") or ""))
            self.percents[i].setText(str(row.get("SPECIES_PCT", "") or ""))

    def values(self) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for i in range(6):
            row = dict(self.rows[i]) if i < len(self.rows) else {}
            code = self.codes[i].text().strip()
            percent = self.percents[i].text().strip()
            if not code and not percent:
                continue
            if not row.get("SPECIES_ORDER"):
                row["SPECIES_ORDER"] = str(i + 1)
            row["TREE_SPECIES_CODE"] = code
            row["SPECIES_PCT"] = percent
            result.append(row)
        return result


class LayerDetails(QWidget):
    """Tree specific data of the active layer.

    The widgets are placed by the classification dock, so this class only owns
    the fields: crown closure, cover pattern, vertical complexity, species data
    source, reference year and snags.
    """

    changed = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.row: dict[str, Any] = {}
        self.crown = _int_edit("", 0, 100)
        self.pattern = code_edit("TREE_COVER_LAYER_ESTIMATED", "COVER_PATTERN_CODE")
        self.complexity = code_edit("TREE_COVER_LAYER_ESTIMATED", "VERTICAL_COMPLEXITY_CODE")
        self.species_source = code_edit(
            "TREE_COVER_LAYER_ESTIMATED", "DATA_SOURCE_INTERPRETED_CODE")
        self.reference_year = _int_edit("", 1800, 2200)
        self.snags = _int_edit("", 0, 5000)
        for widget in (self.crown, self.pattern, self.complexity, self.species_source,
                       self.reference_year, self.snags):
            widget.textChanged.connect(self.changed.emit)

    def load(self, row: dict[str, str], reference_year: str = "",
             snags: str = "") -> None:
        self.row = dict(row)
        self.reference_year.setText(reference_year)
        self.snags.setText(snags)
        self.crown.setText(str(row.get("CROWN_CLOSURE_PCT", "") or ""))
        self.pattern.setText(str(row.get("COVER_PATTERN_CODE", "") or ""))
        self.complexity.setText(str(row.get("VERTICAL_COMPLEXITY_CODE", "") or ""))
        self.species_source.setText(str(row.get("DATA_SOURCE_INTERPRETED_CODE", "") or ""))

    def values(self) -> dict[str, Any]:
        row = dict(self.row)
        row["CROWN_CLOSURE_PCT"] = self.crown.text().strip()
        row["COVER_PATTERN_CODE"] = self.pattern.text().strip()
        row["VERTICAL_COMPLEXITY_CODE"] = self.complexity.text().strip()
        row["DATA_SOURCE_INTERPRETED_CODE"] = self.species_source.text().strip()
        return row


class Mensurational(QGroupBox):
    """Five rows, two columns: title, basal area, its source, density, its source."""

    changed = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Mensurational data", parent)
        self.row: dict[str, Any] = {}
        grid = _grid(self)
        self.basal = _float_edit("", 0.0, 200.0, 1)
        self.basal_source = code_edit("TREE_COVER_LAYER_ESTIMATED", "DATA_SOURCE_BASAL_AREA_CODE")
        self.density = _int_edit("", 0, 80000)
        self.density_source = code_edit("TREE_COVER_LAYER_ESTIMATED", "DATA_SRC_VRI_LIVE_STEM_HA_CODE")
        self.density_target = "layer"
        for widget in (self.basal, self.basal_source, self.density, self.density_source):
            widget.textChanged.connect(self.changed.emit)
        grid.addWidget(_label("Basal area"), 0, 0)
        grid.addWidget(self.basal, 0, 1)
        grid.addWidget(_label("Data source"), 1, 0)
        grid.addWidget(self.basal_source, 1, 1)
        grid.addWidget(_label("Density"), 2, 0)
        grid.addWidget(self.density, 2, 1)
        grid.addWidget(_label("Data source"), 3, 0)
        grid.addWidget(self.density_source, 3, 1)
        grid.setColumnStretch(2, 1)

    def load(self, row: dict[str, str], density: str | None = None) -> None:
        self.row = dict(row)
        self.basal.setText(str(row.get("BASAL_AREA", "") or ""))
        value = row.get("VRI_LIVE_STEMS_PER_HA", "") if density is None else density
        self.density.setText(str(value or ""))
        self.basal_source.setText(str(row.get("DATA_SOURCE_BASAL_AREA_CODE", "") or ""))
        self.density_source.setText(str(row.get("DATA_SRC_VRI_LIVE_STEM_HA_CODE", "") or ""))

    def values(self) -> dict[str, Any]:
        row = dict(self.row)
        row["BASAL_AREA"] = self.basal.text().strip()
        row["VRI_LIVE_STEMS_PER_HA"] = self.density.text().strip()
        row["DATA_SOURCE_BASAL_AREA_CODE"] = self.basal_source.text().strip()
        row["DATA_SRC_VRI_LIVE_STEM_HA_CODE"] = self.density_source.text().strip()
        return row


class SpeciesDetail(QGroupBox):
    """Four rows, four columns: age and height for the first and second species."""

    changed = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("1st & 2nd species", parent)
        self.rows: list[dict[str, Any]] = []
        grid = _grid(self)
        self.ages: list[QLineEdit] = []
        self.heights: list[QLineEdit] = []
        self.age_sources: list[QLineEdit] = []
        self.height_sources: list[QLineEdit] = []
        self.second_source_labels: list[QLabel] = []
        for i in range(2):
            age = _int_edit("", 1, 999)
            height = _float_edit("", 0.1, 99.9, 1)
            age_source = code_edit("TREE_SPECIES_ESTIMATED", "DATA_SOURCE_AGE_CODE")
            height_source = code_edit("TREE_SPECIES_ESTIMATED", "DATA_SOURCE_HEIGHT_CODE")
            grid.addWidget(_label(f"{i + 1}) Age"), 2 * i, 0)
            grid.addWidget(age, 2 * i, 1)
            grid.addWidget(_label("Hgt (m)"), 2 * i, 2)
            grid.addWidget(height, 2 * i, 3)
            src_label_a = _label("Data source")
            src_label_h = _label("Data source")
            grid.addWidget(src_label_a, 2 * i + 1, 0)
            grid.addWidget(age_source, 2 * i + 1, 1)
            grid.addWidget(src_label_h, 2 * i + 1, 2)
            grid.addWidget(height_source, 2 * i + 1, 3)
            if i == 1:
                self.second_source_labels = [src_label_a, src_label_h]
            for widget in (age, height, age_source, height_source):
                widget.textChanged.connect(self.changed.emit)
            self.ages.append(age)
            self.heights.append(height)
            self.age_sources.append(age_source)
            self.height_sources.append(height_source)
        grid.setColumnStretch(4, 1)
        # the second species' data sources are not entered on the filler screen
        # (values already stored are kept and still written back unchanged)
        for widget in (self.age_sources[1], self.height_sources[1]):
            widget.hide()
        for label in self.second_source_labels:
            label.hide()

    def load(self, rows: list[dict[str, str]]) -> None:
        self.rows = [dict(row) for row in rows]
        for i in range(2):
            row = self.rows[i] if i < len(self.rows) else {}
            self.ages[i].setText(str(row.get("AGE", "") or ""))
            self.heights[i].setText(str(row.get("HEIGHT", "") or ""))
            self.age_sources[i].setText(str(row.get("DATA_SOURCE_AGE_CODE", "") or ""))
            self.height_sources[i].setText(str(row.get("DATA_SOURCE_HEIGHT_CODE", "") or ""))

    def values(self) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for i in range(2):
            row = dict(self.rows[i]) if i < len(self.rows) else {}
            row["AGE"] = self.ages[i].text().strip()
            row["HEIGHT"] = self.heights[i].text().strip()
            row["DATA_SOURCE_AGE_CODE"] = self.age_sources[i].text().strip()
            row["DATA_SOURCE_HEIGHT_CODE"] = self.height_sources[i].text().strip()
            result.append(row)
        return result


class LandCoverComponents(QGroupBox):
    """Four rows: component number, cover type, percent and soil moisture regime."""

    changed = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Land cover components", parent)
        self.rows: list[dict[str, Any]] = []
        grid = _grid(self)
        self.types: list[QLineEdit] = []
        self.percents: list[QLineEdit] = []
        self.smr: list[QLineEdit] = []
        for i in range(4):
            cover = code_edit("LAND_COVER_COMPONENT_EST", "LAND_COVER_CLASS_CODE")
            percent = _int_edit("", 0, 100)
            moisture = code_edit("LAND_COVER_COMPONENT_EST", "SOIL_MOISTURE_REGIME_CODE")
            grid.addWidget(_label(str(i + 1), Qt.AlignCenter), i, 0)
            grid.addWidget(cover, i, 1)
            grid.addWidget(_label("%"), i, 2)
            grid.addWidget(percent, i, 3)
            grid.addWidget(_label("SMR"), i, 4)
            grid.addWidget(moisture, i, 5)
            for widget in (cover, percent, moisture):
                widget.textChanged.connect(self.changed.emit)
            self.types.append(cover)
            self.percents.append(percent)
            self.smr.append(moisture)
        grid.setColumnStretch(6, 1)

    def load(self, rows: list[dict[str, str]]) -> None:
        self.rows = [dict(row) for row in rows]
        for i in range(4):
            row = self.rows[i] if i < len(self.rows) else {}
            self.types[i].setText(str(row.get("LAND_COVER_CLASS_CODE", "") or ""))
            self.smr[i].setText(str(row.get("SOIL_MOISTURE_REGIME_CODE", "") or ""))
            self.percents[i].setText(str(row.get("COVERAGE_PCT", "") or ""))

    def values(self) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for i in range(4):
            row = dict(self.rows[i]) if i < len(self.rows) else {}
            cover = self.types[i].text().strip()
            percent = self.percents[i].text().strip()
            moisture = self.smr[i].text().strip()
            if not cover and not percent:
                continue
            row["LAND_COVER_ORDER"] = str(i + 1)
            row["LAND_COVER_LEVEL_CODE"] = str(i + 1)
            row["LAND_COVER_CLASS_CODE"] = cover
            row["COVERAGE_PCT"] = percent
            row["SOIL_MOISTURE_REGIME_CODE"] = moisture
            result.append(row)
        return result


class NonVegetated(QGroupBox):
    """One non-vegetated level at a time, with up to three levels per polygon.

    The level controls (label, "<", "1 of N", ">", Add, Delete) are placed by
    the dock under the Bryoid box, as on the design sheet.
    """

    changed = pyqtSignal()
    level_changed = pyqtSignal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Non vegetated", parent)
        self.rows: list[dict[str, Any]] = []
        self.current = 0
        self._loading = False
        grid = _grid(self)
        self.cover = code_edit("NON_VEGETATIVE_COVER_EST", "NON_VEG_COVER_TYPE_CODE")
        # 0-100: a glacier/snow polygon is 100% non-vegetated
        self.percent = _int_edit("", 0, 100)
        self.pattern = code_edit("NON_VEGETATIVE_COVER_EST", "COVER_PATTERN_CODE")
        grid.addWidget(_label("Cover type"), 0, 0)
        grid.addWidget(self.cover, 0, 1)
        grid.addWidget(_label("Cover %"), 1, 0)
        grid.addWidget(self.percent, 1, 1)
        grid.addWidget(_label("Pattern"), 2, 0)
        grid.addWidget(self.pattern, 2, 1)
        grid.setColumnStretch(2, 1)
        for widget in (self.cover, self.percent, self.pattern):
            widget.textChanged.connect(self._edited)
            widget.editingFinished.connect(self._validate_popup)

        # level controls, placed by the dock
        self.level_label = _label("Level")
        self.prev_button = QPushButton("<")
        self.prev_button.setFixedWidth(22)
        self.level_display = QLineEdit("0 of 0")
        self.level_display.setReadOnly(True)
        self.level_display.setAlignment(Qt.AlignCenter)
        self.level_display.setFixedWidth(64)
        self.next_button = QPushButton(">")
        self.next_button.setFixedWidth(22)
        self.add_button = QPushButton("Add")
        self.remove_button = QPushButton("Delete")
        self.prev_button.clicked.connect(lambda: self.go(-1))
        self.next_button.clicked.connect(lambda: self.go(1))
        self.add_button.clicked.connect(self.add_row)
        self.remove_button.clicked.connect(self.remove_row)
        self.add_button.setToolTip("Add a non-vegetated level (max 3)")
        self.remove_button.setToolTip("Delete the displayed non-vegetated level")

    def level_widgets(self) -> list[QWidget]:
        return [self.level_label, self.prev_button, self.level_display,
                self.next_button, self.add_button, self.remove_button]

    def _edited(self) -> None:
        if not self._loading:
            self._store_current()
            self._refresh_buttons()
            self.changed.emit()

    def _refresh_buttons(self) -> None:
        count = len(self.rows)
        self.prev_button.setEnabled(count > 1 and self.current > 0)
        self.next_button.setEnabled(count > 1 and self.current < count - 1)
        can_add = count < NON_VEG_MAX_LEVELS
        if can_add:
            if count == 1:
                can_add = self._level_filled(0)
            elif count == 2:
                can_add = (self.current == 1 and self._level_filled(1))
            else:
                can_add = False
        self.add_button.setEnabled(can_add)
        self.remove_button.setEnabled(count > 0 and self.current > 0)

    def _store_current(self) -> None:
        if not self.rows:
            return
        row = dict(self.rows[self.current])
        row["NON_VEG_COVER_TYPE_CODE"] = self.cover.text().strip()
        row["NON_VEG_COVER_PCT"] = self.percent.text().strip()
        row["COVER_PATTERN_CODE"] = self.pattern.text().strip()
        self.rows[self.current] = row

    def _level_filled(self, index: int) -> bool:
        if index >= len(self.rows):
            return False
        row = self.rows[index]
        # also consider current edits if this is the active level
        if index == self.current:
            return bool(self.cover.text().strip())
        return bool((row.get("NON_VEG_COVER_TYPE_CODE") or "").strip())

    def validate(self) -> list[str]:
        """Return a list of validation errors for the non-veg levels."""
        self._store_current()
        errors: list[str] = []
        types = []
        pcts = []
        for index, row in enumerate(self.rows):
            types.append((row.get("NON_VEG_COVER_TYPE_CODE") or "").strip())
            try:
                pcts.append(int((row.get("NON_VEG_COVER_PCT") or "0").strip() or 0))
            except ValueError:
                pcts.append(0)
        # duplicate type codes
        seen = set()
        for index, code in enumerate(types):
            if code and code in seen:
                errors.append(f"Level {index + 1}: duplicate non-veg type {code}.")
            seen.add(code)
        # cover % must be non-increasing
        for index in range(1, len(pcts)):
            if pcts[index] > pcts[index - 1] and pcts[index] > 0 and pcts[index - 1] > 0:
                errors.append(
                    f"Level {index + 1}: cover % ({pcts[index]}) "
                    f"must not exceed level {index} ({pcts[index - 1]}).")
        return errors

    _last_error: str = ""

    def _validate_popup(self) -> None:
        errors = self.validate()
        message = "\n".join(errors)
        if message and message != self._last_error:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(None, "Non vegetated", message)
        self._last_error = message

    def _show(self) -> None:
        self._loading = True
        try:
            enabled = bool(self.rows)
            for widget in (self.cover, self.percent, self.pattern):
                widget.setEnabled(enabled)
            row = self.rows[self.current] if enabled else {}
            self.cover.setText(str(row.get("NON_VEG_COVER_TYPE_CODE", "") or ""))
            self.percent.setText(str(row.get("NON_VEG_COVER_PCT", "") or ""))
            self.pattern.setText(str(row.get("COVER_PATTERN_CODE", "") or ""))
        finally:
            self._loading = False
        count = len(self.rows)
        self.level_display.setText(f"{self.current + 1 if count else 0} of {count}")
        self._refresh_buttons()

    def go(self, delta: int) -> None:
        if not self.rows:
            return
        self._store_current()
        self.current = max(0, min(len(self.rows) - 1, self.current + delta))
        self._show()
        self.level_changed.emit(self.current)

    def add_row(self) -> None:
        from PyQt5.QtWidgets import QMessageBox
        if len(self.rows) >= NON_VEG_MAX_LEVELS:
            QMessageBox.information(None, "Non vegetated",
                                    "Maximum of 3 non-vegetated levels.")
            return
        # level 1 must be filled before adding level 2
        if len(self.rows) == 1:
            if not self._level_filled(0):
                QMessageBox.warning(None, "Non vegetated",
                                    "Fill level 1 before adding level 2.")
                return
        # level 2 must be filled before adding level 3, and only from level 2
        if len(self.rows) == 2:
            if self.current != 1:
                QMessageBox.warning(None, "Non vegetated",
                                    "Add level 3 only from level 2.")
                return
            if not self._level_filled(1):
                QMessageBox.warning(None, "Non vegetated",
                                    "Fill level 2 before adding level 3.")
                return
        self._store_current()
        self.rows.append({})
        self.current = len(self.rows) - 1
        self._show()
        self.level_changed.emit(self.current)
        self.changed.emit()

    def remove_row(self) -> None:
        if not self.rows:
            return
        from PyQt5.QtWidgets import QMessageBox
        if self.current == 0:
            QMessageBox.warning(None, "Non vegetated",
                                "The first non-vegetated level cannot be deleted.")
            return
        if self.current != len(self.rows) - 1:
            QMessageBox.warning(None, "Non vegetated",
                                "Delete the last level first.")
            return
        del self.rows[self.current]
        self.current = max(0, min(self.current, len(self.rows) - 1))
        self._show()
        self.level_changed.emit(self.current)
        self.changed.emit()

    def load(self, rows: list[dict[str, str]]) -> None:
        self.rows = [dict(row) for row in rows][:NON_VEG_MAX_LEVELS]
        self.current = 0
        self._show()

    def values(self) -> list[dict[str, Any]]:
        self._store_current()
        result: list[dict[str, Any]] = []
        for index, row in enumerate(self.rows):
            updated = dict(row)
            updated["NON_VEG_ORDER"] = str(index + 1)
            updated["LAYER_LEVEL_CODE"] = str(index + 1)
            result.append(updated)
        return result
