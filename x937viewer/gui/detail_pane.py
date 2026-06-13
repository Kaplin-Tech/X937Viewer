"""Metadata side pane: grouped tree of the selected item's records."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem

from .check_list import format_amount

_AMOUNT_KEYS = {
    "itemAmount", "bundleTotalAmount", "micrValidTotalAmount",
    "cashLetterTotalAmount", "fileTotalAmount", "routingNumberTotalAmount",
}
_SKIP_KEYS = {"id", "imageData", "digitalSignature"}


class DetailPane(QTreeWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(2)
        self.setHeaderLabels(["Field", "Value"])
        self.setAlternatingRowColors(True)
        self.setUniformRowHeights(True)
        self.header().setStretchLastSection(True)

    # ------------------------------------------------------------------ build
    def show_item(self, cash_letter, bundle, item, kind, file_data):
        self.clear()
        if item is None:
            return
        title = "Return Detail" if kind == "return" else "Check Detail"
        self._add_group(title, {k: v for k, v in item.items() if not isinstance(v, list)})

        for key, label in [
            ("checkDetailAddendumA", "Addendum A (BOFD)"),
            ("checkDetailAddendumB", "Addendum B"),
            ("checkDetailAddendumC", "Addendum C (Endorsing Bank)"),
            ("returnDetailAddendumA", "Addendum A (BOFD)"),
            ("returnDetailAddendumB", "Addendum B (Payor Bank)"),
            ("returnDetailAddendumC", "Addendum C"),
            ("returnDetailAddendumD", "Addendum D (Endorsing Bank)"),
            ("imageViewDetail", "Image View Detail"),
            ("imageViewData", "Image View Data"),
            ("imageViewAnalysis", "Image View Analysis"),
        ]:
            entries = item.get(key) or []
            for i, entry in enumerate(entries):
                suffix = f" #{i + 1}" if len(entries) > 1 else ""
                self._add_group(label + suffix, entry, expanded=key.startswith("checkDetail")
                                or key.startswith("returnDetail"))

        if bundle is not None:
            self._add_group("Bundle Header", bundle.get("bundleHeader") or {}, expanded=False)
            if bundle.get("bundleControl"):
                self._add_group("Bundle Control", bundle["bundleControl"], expanded=False)
        if cash_letter is not None:
            self._add_group("Cash Letter Header", cash_letter.get("cashLetterHeader") or {},
                            expanded=False)
        if file_data is not None:
            self._add_group("File Header", file_data.get("fileHeader") or {}, expanded=False)

        self.resizeColumnToContents(0)

    def _add_group(self, title: str, mapping: dict, expanded: bool = True):
        root = QTreeWidgetItem([title, ""])
        font = root.font(0)
        font.setBold(True)
        root.setFont(0, font)
        self.addTopLevelItem(root)
        for k, v in mapping.items():
            if k in _SKIP_KEYS or isinstance(v, (list, dict)):
                continue
            root.addChild(QTreeWidgetItem([k, self._fmt(k, v)]))
        root.setExpanded(expanded)
        return root

    @staticmethod
    def _fmt(key, value) -> str:
        if key in _AMOUNT_KEYS:
            return f"{format_amount(value)}  ({value})"
        if isinstance(value, str) and value.endswith("T00:00:00Z") and not value.startswith(("0001-", "0000-")):
            return value[:10]
        return str(value)
