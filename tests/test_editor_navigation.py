"""Regression tests for polygon-number navigation, rename and delete safety in the VRI editor.

A polygon number typed to navigate must never be saved as a rename, a duplicate
polygon number must never be written, and Delete / Cut must default to No.
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import Qt  # noqa: E402
from PyQt5.QtTest import QTest  # noqa: E402
from PyQt5.QtWidgets import QApplication, QMessageBox  # noqa: E402

from vri_editor import app as editor_app  # noqa: E402
from vri_editor import db  # noqa: E402

_APP = QApplication.instance() or QApplication([])


def _numbers(path: Path) -> list[str]:
    return sorted((r["POLYGON_NUMBER"].strip() for r in db.read_rows(path, "FOREST_COVER_OBJECT")),
                  key=lambda s: int(s))


class ConflictHelperTests(unittest.TestCase):
    def test_dict_rows(self):
        rows = {1: {"fco": {"POLYGON_NUMBER": "1"}}, 2: {"fco": {"POLYGON_NUMBER": "2"}}}
        self.assertEqual(db.poly_number_conflict(rows, 2, "1"), 1)
        self.assertIsNone(db.poly_number_conflict(rows, 2, "2"))  # same polygon is not a conflict
        self.assertIsNone(db.poly_number_conflict(rows, 2, "9"))

    def test_list_rows_and_blank(self):
        rows = [{"FOREST_COVER_OBJECT_ID": "7", "POLYGON_NUMBER": "42"}]
        self.assertEqual(db.poly_number_conflict(rows, 3, " 42 "), 7)
        self.assertIsNone(db.poly_number_conflict(rows, 3, ""))


class EditorNavigationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.path = db.new_project(self.tmp / "t.mdb", project="T", interpreter="TEST",
                                   map_name="092N025")
        db.add_polygon(self.path, "2")
        db.add_polygon(self.path, "3")
        self.before = _numbers(self.path)
        self.window = editor_app.EditorWindow()
        self.window.show()
        self.window._load(self.path)
        self.fid_of = {rec["fco"]["POLYGON_NUMBER"]: fid for fid, rec in self.window.rows.items()}
        self.window._load_polygon(self.fid_of["2"])
        self.prompts = []
        # no dialog may block the test: unexpected prompts are recorded and answered No
        self.unexpected = []
        patchers = [patch.object(QMessageBox, "question", side_effect=self._unexpected_dialog(QMessageBox.No)),
                    patch.object(QMessageBox, "warning", side_effect=self._unexpected_dialog(QMessageBox.Ok)),
                    patch.object(QMessageBox, "information", side_effect=self._unexpected_dialog(QMessageBox.Ok)),
                    patch.object(QMessageBox, "critical", side_effect=self._unexpected_dialog(QMessageBox.Ok))]
        for patcher in patchers:
            patcher.start()
            self.addCleanup(patcher.stop)

    def _unexpected_dialog(self, answer):
        def record(*args, **kwargs):
            self.unexpected.append(args[1] if len(args) > 1 else "")
            return answer
        return record

    def tearDown(self):
        self.window.close()
        shutil.rmtree(self.tmp, ignore_errors=True)
        self.assertEqual(self.unexpected, [], "unexpected dialog(s) raised")

    def _answer(self, button):
        def fake(*args, **kwargs):
            self.prompts.append(args[1] if len(args) > 1 else "")
            return button
        return patch.object(QMessageBox, "question", side_effect=fake)

    def _type_number(self, text):
        field = self.window.widgets["fco.POLYGON_NUMBER"]
        field.setFocus()
        _APP.processEvents()
        field.selectAll()
        QTest.keyClicks(field, text)
        _APP.processEvents()
        return field

    def _current_number(self):
        return self.window.rows[self.window.current_fid]["fco"]["POLYGON_NUMBER"]

    def test_typing_a_number_does_not_mark_changed(self):
        self._type_number("3")
        self.assertFalse(self.window.dirty)

    def test_enter_on_existing_number_navigates_without_prompt_or_write(self):
        with self._answer(QMessageBox.Save) as question:
            field = self._type_number("3")
            QTest.keyClick(field, Qt.Key_Return)
            _APP.processEvents()
        self.assertEqual(self._current_number(), "3")
        self.assertEqual(question.call_count, 0)
        self.assertEqual(_numbers(self.path), self.before)

    def test_enter_then_save_answer_cannot_rename_the_polygon_left(self):
        # the bug: typed "3" on polygon 2, then Save at the prompt renamed polygon 2 to 3
        with self._answer(QMessageBox.Save):
            field = self._type_number("9")
            QTest.keyClick(field, Qt.Key_Return)
            _APP.processEvents()
        self.assertEqual(_numbers(self.path), self.before)
        self.assertEqual(self.window.widgets["fco.POLYGON_NUMBER"].text(), self._current_number())

    def test_unknown_number_declined_keeps_current_polygon(self):
        with self._answer(QMessageBox.No):
            field = self._type_number("77")
            QTest.keyClick(field, Qt.Key_Return)
            _APP.processEvents()
        self.assertEqual(self._current_number(), "2")
        self.assertEqual(_numbers(self.path), self.before)

    def test_save_refuses_a_duplicate_number(self):
        field = self.window.widgets["fco.POLYGON_NUMBER"]
        field.setText("3")
        with self._answer(QMessageBox.Yes), \
                patch.object(QMessageBox, "warning") as warning:
            self.assertFalse(self.window._save())
        self.assertTrue(warning.called)
        self.assertIn("already used", warning.call_args[0][2])
        self.assertEqual(_numbers(self.path), self.before)

    def test_rename_declined_restores_the_stored_number(self):
        field = self.window.widgets["fco.POLYGON_NUMBER"]
        field.setText("50")
        with self._answer(QMessageBox.No):
            self.assertFalse(self.window._save())
        self.assertEqual(field.text(), "2")
        self.assertEqual(_numbers(self.path), self.before)

    def test_rename_confirmed_is_written(self):
        field = self.window.widgets["fco.POLYGON_NUMBER"]
        field.setText("50")
        with self._answer(QMessageBox.Yes):
            self.assertTrue(self.window._save())
        self.assertIn("50", _numbers(self.path))
        self.assertNotIn("2", _numbers(self.path))

    def test_delete_confirmation_defaults_to_no(self):
        with patch.object(QMessageBox, "question", return_value=QMessageBox.No) as question, \
                patch.object(db, "delete_polygon") as delete:
            self.window._delete_polygon()
        self.assertEqual(question.call_args[0][4], QMessageBox.No)
        delete.assert_not_called()
        self.assertEqual(_numbers(self.path), self.before)

    def test_cut_confirmation_defaults_to_no(self):
        with patch.object(QMessageBox, "question", return_value=QMessageBox.No) as question, \
                patch.object(db, "delete_polygon") as delete:
            self.window._cut_polygon()
        self.assertEqual(question.call_args[0][4], QMessageBox.No)
        delete.assert_not_called()
        self.assertEqual(_numbers(self.path), self.before)


if __name__ == "__main__":
    unittest.main()
