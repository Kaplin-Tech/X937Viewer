"""Check/return list: table model + search filtering."""

from __future__ import annotations

import re

from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, QSortFilterProxyModel


def format_amount(cents) -> str:
    try:
        return f"${cents / 100:,.2f}"
    except (TypeError, ValueError):
        return ""


def short_date(iso: str) -> str:
    if isinstance(iso, str) and len(iso) >= 10 and not iso.startswith(("0001-", "0000-")):
        return iso[:10]
    return ""


class ItemTableModel(QAbstractTableModel):
    """One row per check or return across all cash letters and bundles."""

    COLUMNS = ["#", "Type", "Amount", "Payor Routing", "On-Us / Account", "Sequence #", "Date"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.items = []  # list of (cash_letter, bundle, item, kind)

    def set_file(self, x937file):
        self.beginResetModel()
        self.items = x937file.all_items() if x937file else []
        self.endResetModel()

    # Qt model API -----------------------------------------------------------
    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.items)

    def columnCount(self, parent=QModelIndex()):
        return len(self.COLUMNS)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.COLUMNS[section]
        return None

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        _, _, item, kind = self.items[index.row()]
        col = index.column()
        if role in (Qt.DisplayRole, Qt.ToolTipRole):
            if col == 0:
                return index.row() + 1
            if col == 1:
                return "Return" if kind == "return" else "Check"
            if col == 2:
                return format_amount(item.get("itemAmount"))
            if col == 3:
                rt = item.get("payorBankRoutingNumber", "")
                digit = item.get("payorBankCheckDigit", "")
                return f"{rt}{digit}"
            if col == 4:
                return item.get("onUs") or item.get("auxiliaryOnUs") or ""
            if col == 5:
                return item.get("eceInstitutionItemSequenceNumber", "")
            if col == 6:
                adds = item.get("checkDetailAddendumA") or item.get("returnDetailAddendumA") or []
                if adds:
                    return short_date(adds[0].get("bofdEndorsementDate", ""))
                return short_date(item.get("forwardBundleDate", ""))
        if role == Qt.UserRole:  # for sorting
            if col == 0:
                return index.row()
            if col == 2:
                return item.get("itemAmount") or 0
        if role == Qt.TextAlignmentRole and col in (0, 2):
            return int(Qt.AlignRight | Qt.AlignVCenter)
        return None

    def item_at(self, row: int):
        return self.items[row]


class ItemFilterProxy(QSortFilterProxyModel):
    """Filters on amount (dollars or cents) and account/routing/sequence text."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._needle = ""
        self.setSortRole(Qt.UserRole)

    def set_search(self, text: str):
        self._needle = text.strip()
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        if not self._needle:
            return True
        model: ItemTableModel = self.sourceModel()
        _, _, item, _ = model.items[source_row]
        needle = self._needle.lower()

        # amount search: "123.45", "$1,234.56" or raw cents "12345"
        amount = item.get("itemAmount") or 0
        cleaned = needle.replace("$", "").replace(",", "")
        if re.fullmatch(r"\d+\.\d{1,2}", cleaned):
            if abs(float(cleaned) * 100 - amount) < 0.5:
                return True
        elif cleaned.isdigit():
            if int(cleaned) == amount:
                return True

        haystacks = [
            item.get("onUs", ""), item.get("auxiliaryOnUs", ""),
            item.get("payorBankRoutingNumber", ""),
            item.get("eceInstitutionItemSequenceNumber", ""),
        ]
        for add in (item.get("checkDetailAddendumA") or item.get("returnDetailAddendumA") or []):
            haystacks += [add.get("bofdAccountNumber", ""), add.get("bofdItemSequenceNumber", ""),
                          add.get("returnLocationRoutingNumber", ""), add.get("payeeName", "")]
        return any(needle in (h or "").lower() for h in haystacks)
