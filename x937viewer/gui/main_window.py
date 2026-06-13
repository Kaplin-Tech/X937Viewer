"""Main window: toolbar, check list, image pane, metadata pane."""

from __future__ import annotations

import sys

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QSplitter, QTableView, QLineEdit, QFileDialog,
    QMessageBox, QToolBar, QLabel, QAbstractItemView, QHeaderView, QStyle,
)

from ..parser import parse_file, X937File, X937Error
from ..json_export import write_json
from .check_list import ItemTableModel, ItemFilterProxy, format_amount
from .detail_pane import DetailPane
from .image_view import ImagePane


class ParseWorker(QThread):
    done = Signal(object)
    failed = Signal(str)

    def __init__(self, path: str, parent=None):
        super().__init__(parent)
        self.path = path

    def run(self):
        try:
            self.done.emit(parse_file(self.path))
        except (X937Error, OSError) as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # noqa: BLE001 - viewer should not crash
            self.failed.emit(f"unexpected error: {exc!r}")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("X937 Viewer")
        self.resize(1280, 760)
        self.file: X937File | None = None
        self._worker = None

        # --- models / views
        self.model = ItemTableModel(self)
        self.proxy = ItemFilterProxy(self)
        self.proxy.setSourceModel(self.model)

        self.table = QTableView()
        self.table.setModel(self.proxy)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setSortingEnabled(True)
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.selectionModel().currentRowChanged.connect(self._on_select)

        self.image_pane = ImagePane()
        self.details = DetailPane()

        split = QSplitter(Qt.Horizontal)
        split.addWidget(self.table)
        split.addWidget(self.image_pane)
        split.addWidget(self.details)
        split.setStretchFactor(0, 2)
        split.setStretchFactor(1, 4)
        split.setStretchFactor(2, 2)
        split.setSizes([380, 560, 320])
        self.setCentralWidget(split)

        # --- toolbar
        tb = QToolBar("Main")
        tb.setMovable(False)
        self.addToolBar(tb)

        style = self.style()
        act_open = QAction(style.standardIcon(QStyle.SP_DialogOpenButton), "Open…", self)
        act_open.setShortcut(QKeySequence.Open)
        act_open.triggered.connect(self.open_dialog)
        tb.addAction(act_open)

        self.act_export = QAction(style.standardIcon(QStyle.SP_DialogSaveButton),
                                  "Export JSON…", self)
        self.act_export.setShortcut("Ctrl+E")
        self.act_export.setEnabled(False)
        self.act_export.triggered.connect(self.export_json)
        tb.addAction(self.act_export)

        tb.addSeparator()
        tb.addWidget(QLabel(" Search: "))
        self.search = QLineEdit()
        self.search.setPlaceholderText("amount (12.34) or account / routing / sequence…")
        self.search.setClearButtonEnabled(True)
        self.search.setMaximumWidth(360)
        self.search.textChanged.connect(self.proxy.set_search)
        tb.addWidget(self.search)

        self.status_label = QLabel("Open an X9.37 file to begin")
        self.statusBar().addWidget(self.status_label, 1)
        self.warn_label = QLabel("")
        self.statusBar().addPermanentWidget(self.warn_label)

    # ------------------------------------------------------------------ file io
    def open_dialog(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open X9.37 file", "",
            "Image Cash Letter files (*.x937 *.icl *.x9 *.dat);;All files (*)")
        if path:
            self.load(path)

    def load(self, path: str):
        self.status_label.setText(f"Parsing {path}…")
        self._worker = ParseWorker(path, self)
        self._worker.done.connect(self._loaded)
        self._worker.failed.connect(self._load_failed)
        self._worker.start()

    def _loaded(self, f: X937File):
        self.file = f
        self.model.set_file(f)
        self.proxy.sort(-1)
        self.act_export.setEnabled(True)

        fh = f.data.get("fileHeader") or {}
        total = (f.data.get("fileControl") or {}).get("fileTotalAmount")
        bits = [f.source_path or "", f"{f.item_count()} item(s)"]
        if total is not None:
            bits.append(f"total {format_amount(total)}")
        bits.append("EBCDIC" if f.encoding == "cp037" else "ASCII")
        if fh.get("immediateDestinationName"):
            bits.append(f"to {fh['immediateDestinationName']}")
        self.status_label.setText("  •  ".join(bits))
        self.setWindowTitle(f"X937 Viewer — {f.source_path}")

        if f.warnings:
            self.warn_label.setText(f"⚠ {len(f.warnings)} warning(s)")
            self.warn_label.setToolTip("\n".join(f.warnings))
        else:
            self.warn_label.setText("")
            self.warn_label.setToolTip("")

        if self.proxy.rowCount():
            self.table.selectRow(0)
        else:
            self.image_pane.set_item(None)
            self.details.clear()

    def _load_failed(self, message: str):
        self.status_label.setText("Failed to open file")
        QMessageBox.critical(self, "X937 Viewer", f"Could not open file:\n\n{message}")

    def export_json(self):
        if not self.file:
            return
        suggested = (self.file.source_path or "icl") + ".json"
        path, _ = QFileDialog.getSaveFileName(self, "Export JSON", suggested,
                                              "JSON (*.json)")
        if not path:
            return
        try:
            write_json(self.file, path)
        except OSError as exc:
            QMessageBox.critical(self, "X937 Viewer", f"Could not write JSON:\n\n{exc}")
            return
        self.status_label.setText(f"Exported {path}")

    # ------------------------------------------------------------------ selection
    def _on_select(self, current, _previous):
        if not current.isValid() or not self.file:
            return
        row = self.proxy.mapToSource(current).row()
        cl, bundle, item, kind = self.model.item_at(row)
        self.image_pane.set_item(item)
        self.details.show_item(cl, bundle, item, kind, self.file.data)


def run(path: str | None = None) -> int:
    app = QApplication(sys.argv[:1])
    app.setApplicationName("X937 Viewer")
    app.setStyle("Fusion")
    win = MainWindow()
    win.show()
    if path:
        win.load(path)
    return app.exec()
