"""Tkinter desktop interface for the VRI validator."""

from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import __version__
from .report import counts_by_code
from .service import ValidationResult, recalculate_database, validate_database

APP_NAME = "VRI Validator"
ICON_PATH = Path(__file__).resolve().parent / "data" / "vri-validator.png"


def _open_path(path: Path) -> None:
    if sys.platform.startswith("win"):
        os.startfile(str(path))  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)], stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
    else:
        subprocess.Popen(["xdg-open", str(path)], stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)


class App:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.result: ValidationResult | None = None
        self.worker: threading.Thread | None = None
        self.messages: queue.Queue[tuple[str, object]] = queue.Queue()
        self.icon: tk.PhotoImage | None = None
        self.header_icon: tk.PhotoImage | None = None

        root.title(f"{APP_NAME} {__version__}")
        root.geometry("940x700")
        root.minsize(780, 600)
        root.option_add("*tearOff", False)
        self._set_icon()
        self._build()
        self._bind_keys()
        self._poll()

    def _set_icon(self) -> None:
        try:
            self.icon = tk.PhotoImage(file=str(ICON_PATH))
            self.root.iconphoto(True, self.icon)
            factor = max(1, self.icon.width() // 64)
            self.header_icon = self.icon.subsample(factor, factor)
        except tk.TclError:
            self.icon = None
            self.header_icon = None

    def _build(self) -> None:
        outer = ttk.Frame(self.root, padding=16)
        outer.pack(fill="both", expand=True)

        header = ttk.Frame(outer)
        header.pack(fill="x")
        if self.header_icon is not None:
            ttk.Label(header, image=self.header_icon).pack(side="left", padx=(0, 14))
        titles = ttk.Frame(header)
        titles.pack(side="left", fill="x", expand=True)
        ttk.Label(titles, text=APP_NAME, font=("TkDefaultFont", 17, "bold")).pack(anchor="w")
        ttk.Label(
            titles,
            text="Validation and recalculation for BC VRI / VRIMS personal geodatabases",
            foreground="#5b6670",
        ).pack(anchor="w", pady=(2, 0))

        form = ttk.LabelFrame(outer, text="Input and output", padding=12)
        form.pack(fill="x", pady=(16, 10))
        form.columnconfigure(1, weight=1)

        self.db_var = tk.StringVar()
        ttk.Label(form, text="Database (.mdb)").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Entry(form, textvariable=self.db_var).grid(
            row=0, column=1, sticky="ew", padx=8, pady=4)
        ttk.Button(form, text="Browse…", command=self._browse_db).grid(
            row=0, column=2, pady=4)

        self.out_var = tk.StringVar(value=str(Path.home() / "VRI_reports"))
        ttk.Label(form, text="Output folder").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(form, textvariable=self.out_var).grid(
            row=1, column=1, sticky="ew", padx=8, pady=4)
        ttk.Button(form, text="Browse…", command=self._browse_out).grid(
            row=1, column=2, pady=4)

        self.format_var = tk.StringVar(value="Both (CSV + HTML)")
        ttk.Label(form, text="Report format").grid(row=2, column=0, sticky="w", pady=4)
        fmt = ttk.Combobox(
            form,
            textvariable=self.format_var,
            state="readonly",
            values=("Both (CSV + HTML)", "CSV only", "HTML only"),
            width=22,
        )
        fmt.grid(row=2, column=1, sticky="w", padx=8, pady=4)

        self.title_var = tk.StringVar()
        ttk.Label(form, text="Report title").grid(row=3, column=0, sticky="w", pady=4)
        ttk.Entry(form, textvariable=self.title_var).grid(
            row=3, column=1, sticky="ew", padx=8, pady=4)
        ttk.Label(form, text="optional", foreground="#77828c").grid(
            row=3, column=2, sticky="w", pady=4)

        self.open_when_done = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            form, text="Open the HTML report when validation finishes",
            variable=self.open_when_done,
        ).grid(row=4, column=1, columnspan=2, sticky="w", padx=8, pady=(6, 0))

        self.recalc_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            form, text="Recalculate BCLCS, layer rank and LCC order (backup first)",
            variable=self.recalc_var,
        ).grid(row=5, column=1, columnspan=2, sticky="w", padx=8, pady=(6, 0))

        actions = ttk.Frame(outer)
        actions.pack(fill="x", pady=(0, 8))
        self.run_btn = ttk.Button(actions, text="Validate", command=self._start)
        self.run_btn.pack(side="left")
        self.open_btn = ttk.Button(actions, text="Open report", command=self._open_report)
        self.open_btn.pack(side="left", padx=(8, 0))
        self.open_btn.configure(state="disabled")
        self.folder_btn = ttk.Button(
            actions, text="Open report folder", command=self._open_report_folder)
        self.folder_btn.pack(side="left", padx=(8, 0))
        self.folder_btn.configure(state="disabled")

        self.progress = ttk.Progressbar(outer, mode="indeterminate")
        self.progress.pack(fill="x", pady=(4, 5))
        self.status = ttk.Label(outer, text="Choose a .mdb file to begin.",
                                foreground="#5b6670")
        self.status.pack(anchor="w", pady=(0, 10))

        cards = ttk.Frame(outer)
        cards.pack(fill="x", pady=(0, 10))
        self.card_values: dict[str, ttk.Label] = {}
        for key, label in (("polygons", "Polygons"), ("error", "Errors"),
                           ("warning", "Warnings"), ("info", "Info")):
            card = ttk.LabelFrame(cards, text=label, padding=8)
            card.pack(side="left", fill="x", expand=True, padx=(0, 8))
            value = ttk.Label(card, text="—", font=("TkDefaultFont", 18, "bold"))
            value.pack(anchor="w")
            self.card_values[key] = value

        rules_frame = ttk.LabelFrame(outer, text="Top rules", padding=8)
        rules_frame.pack(fill="both", expand=True)
        rules_frame.columnconfigure(0, weight=1)
        rules_frame.rowconfigure(0, weight=1)
        self.rule_tree = ttk.Treeview(
            rules_frame,
            columns=("code", "severity", "count"),
            show="headings",
            height=8,
        )
        self.rule_tree.heading("code", text="Rule")
        self.rule_tree.heading("severity", text="Severity")
        self.rule_tree.heading("count", text="Count")
        self.rule_tree.column("code", width=180, anchor="w")
        self.rule_tree.column("severity", width=110, anchor="w")
        self.rule_tree.column("count", width=90, anchor="e")
        self.rule_tree.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(rules_frame, orient="vertical", command=self.rule_tree.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.rule_tree.configure(yscrollcommand=scroll.set)

        self.paths_var = tk.StringVar()
        ttk.Label(
            outer, textvariable=self.paths_var, foreground="#5b6670",
            justify="left", wraplength=880,
        ).pack(fill="x", pady=(10, 0))

    def _bind_keys(self) -> None:
        self.root.bind("<Control-o>", lambda _event: self._browse_db())
        self.root.bind("<Control-Return>", lambda _event: self._start())
        self.root.bind("<Control-q>", lambda _event: self.root.destroy())

    def _browse_db(self) -> None:
        path = filedialog.askopenfilename(
            title="Choose a VRIMS personal geodatabase",
            filetypes=(("Access databases", "*.mdb"), ("All files", "*.*")),
        )
        if path:
            self.db_var.set(path)
            if not self.title_var.get().strip():
                self.title_var.set(f"VRI validation: {Path(path).name}")

    def _browse_out(self) -> None:
        path = filedialog.askdirectory(title="Choose a report folder")
        if path:
            self.out_var.set(path)

    def _start(self) -> None:
        if self.worker is not None and self.worker.is_alive():
            return
        raw_db = self.db_var.get().strip()
        if not raw_db:
            messagebox.showwarning(APP_NAME, "Choose a VRIMS .mdb file first.")
            return
        db_path = Path(raw_db).expanduser()
        if not db_path.is_file():
            messagebox.showerror(APP_NAME, f"Database not found:\n{db_path}")
            return
        out_dir = Path(self.out_var.get().strip() or (Path.home() / "VRI_reports")).expanduser()
        self.out_var.set(str(out_dir))
        fmt = {
            "Both (CSV + HTML)": "both",
            "CSV only": "csv",
            "HTML only": "html",
        }[self.format_var.get()]
        title = self.title_var.get().strip()
        recalculate = self.recalc_var.get()
        if recalculate and not messagebox.askyesno(
                APP_NAME,
                "Recalculate BCLCS, FOREST_COVER_RANK_CODE and LAND_COVER_ORDER "
                f"in:\n{db_path}\n\nA timestamped backup will be written first. "
                "Continue?"):
            return

        self.result = None
        self._clear_results()
        self.run_btn.configure(state="disabled")
        self.open_btn.configure(state="disabled")
        self.folder_btn.configure(state="disabled")
        self.progress.start(12)
        self.status.configure(
            text=(f"Recalculating {db_path.name}…" if recalculate
                  else f"Validating {db_path.name}…"))
        self.worker = threading.Thread(
            target=self._run_worker,
            args=(db_path, out_dir, fmt, title, recalculate),
            daemon=True,
        )
        self.worker.start()

    def _run_worker(self, db_path: Path, out_dir: Path, fmt: str, title: str,
                    recalculate: bool) -> None:
        try:
            if recalculate:
                recalc = recalculate_database(db_path)
                if recalc.updated:
                    self.messages.put((
                        "info",
                        f"Recalculated {recalc.updated:,} values; backup: {recalc.backup}",
                    ))
                else:
                    self.messages.put(("info", "Derived fields already current."))
            result = validate_database(
                db_path,
                out_dir=out_dir,
                formats=fmt,
                title=title,
            )
        except Exception as exc:  # noqa: BLE001 - shown in the GUI
            self.messages.put(("error", exc))
        else:
            self.messages.put(("done", result))

    def _poll(self) -> None:
        try:
            while True:
                kind, payload = self.messages.get_nowait()
                if kind == "done":
                    self._finish(payload)  # type: ignore[arg-type]
                elif kind == "info":
                    self.status.configure(text=str(payload))
                else:
                    self._fail(payload)  # type: ignore[arg-type]
        except queue.Empty:
            pass
        self.root.after(100, self._poll)

    def _finish(self, result: ValidationResult) -> None:
        self.result = result
        counts = result.findings.counts()
        self.progress.stop()
        self.run_btn.configure(state="normal")
        self.open_btn.configure(state="normal")
        self.folder_btn.configure(state="normal")
        self.card_values["polygons"].configure(text=f"{len(result.dataset.polygons):,}")
        self.card_values["error"].configure(text=f"{counts['error']:,}")
        self.card_values["warning"].configure(text=f"{counts['warning']:,}")
        self.card_values["info"].configure(text=f"{counts['info']:,}")
        for item in self.rule_tree.get_children():
            self.rule_tree.delete(item)
        for code, severity, n in counts_by_code(result.findings)[:20]:
            self.rule_tree.insert("", "end", values=(code, severity, f"{n:,}"))
        self.paths_var.set(
            "Reports: " + "  |  ".join(str(path) for path in result.report_paths)
            if result.report_paths else "No report files were written."
        )
        self.status.configure(
            text=f"Validation complete — {len(result.findings):,} findings.")
        if result.report_paths and self.open_when_done.get():
            self._open_report()

    def _fail(self, exc: object) -> None:
        self.progress.stop()
        self.run_btn.configure(state="normal")
        self.status.configure(text="Operation failed.")
        messagebox.showerror(APP_NAME, str(exc))

    def _clear_results(self) -> None:
        for value in self.card_values.values():
            value.configure(text="—")
        for item in self.rule_tree.get_children():
            self.rule_tree.delete(item)
        self.paths_var.set("")

    def _open_report(self) -> None:
        if self.result is None or not self.result.report_paths:
            return
        html_report = next(
            (path for path in self.result.report_paths if path.suffix.lower() == ".html"),
            None,
        )
        target = html_report or self.result.report_paths[0]
        try:
            opened = webbrowser.open(target.resolve().as_uri())
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(APP_NAME, f"Could not open the report:\n{exc}")
            return
        if not opened:
            messagebox.showinfo(APP_NAME, f"Report written to:\n{target}")

    def _open_report_folder(self) -> None:
        if self.result is None or not self.result.report_paths:
            return
        folder = self.result.report_paths[0].parent
        try:
            _open_path(folder)
        except OSError as exc:
            messagebox.showerror(APP_NAME, f"Could not open the folder:\n{exc}")


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if "--version" in args:
        print(f"vri-validate-gui {__version__}")
        return 0
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        print(f"error: cannot start the GUI: {exc}", file=sys.stderr)
        return 2
    App(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
