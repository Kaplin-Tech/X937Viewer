"""Check image viewer: TIFF decode (Pillow), front/back toggle, zoom."""

from __future__ import annotations

import io

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QPainter
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGraphicsView, QGraphicsScene,
    QPushButton, QButtonGroup, QLabel, QToolButton, QSizePolicy,
)


def decode_image(data: bytes) -> QPixmap:
    """Decode TIFF (or any Pillow-supported) image bytes to a QPixmap."""
    pix = QPixmap()
    if not data:
        return pix
    try:
        from PIL import Image
        with Image.open(io.BytesIO(data)) as im:
            buf = io.BytesIO()
            im.save(buf, format="PNG")
        pix.loadFromData(buf.getvalue(), "PNG")
    except Exception:
        # last resort: maybe Qt can read it natively
        pix.loadFromData(data)
    return pix


class _ZoomView(QGraphicsView):
    """QGraphicsView with Ctrl+wheel zoom (plain wheel still scrolls)."""

    def __init__(self, scene, pane):
        super().__init__(scene)
        self._pane = pane

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            self._pane.zoom(1.25 if event.angleDelta().y() > 0 else 0.8)
            event.accept()
        else:
            super().wheelEvent(event)


class ImagePane(QWidget):
    """Front/back toggle + zoomable image of the selected check."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._views = []        # list of (label, image_bytes)
        self._current = 0
        self._fit = True

        self.scene = QGraphicsScene(self)
        self.view = _ZoomView(self.scene, self)
        self.view.setRenderHints(QPainter.SmoothPixmapTransform)
        self.view.setDragMode(QGraphicsView.ScrollHandDrag)
        self.view.setBackgroundBrush(self.palette().window())
        self._pixmap_item = None

        self.btn_front = QPushButton("Front")
        self.btn_back = QPushButton("Back")
        for b in (self.btn_front, self.btn_back):
            b.setCheckable(True)
            b.setMinimumWidth(90)
        self.btn_front.setChecked(True)
        group = QButtonGroup(self)
        group.addButton(self.btn_front, 0)
        group.addButton(self.btn_back, 1)
        group.idClicked.connect(self.show_side)

        self.btn_zoom_in = QToolButton(text="+")
        self.btn_zoom_out = QToolButton(text="−")
        self.btn_fit = QToolButton(text="Fit")
        self.btn_zoom_in.clicked.connect(lambda: self.zoom(1.25))
        self.btn_zoom_out.clicked.connect(lambda: self.zoom(0.8))
        self.btn_fit.clicked.connect(self.fit)

        self.info = QLabel("")
        self.info.setAlignment(Qt.AlignCenter)
        self.info.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        bar = QHBoxLayout()
        bar.addStretch(1)
        bar.addWidget(self.btn_front)
        bar.addWidget(self.btn_back)
        bar.addSpacing(24)
        bar.addWidget(self.btn_zoom_out)
        bar.addWidget(self.btn_fit)
        bar.addWidget(self.btn_zoom_in)
        bar.addStretch(1)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addLayout(bar)
        lay.addWidget(self.view, 1)
        lay.addWidget(self.info)

    # ------------------------------------------------------------------ data
    def set_item(self, item: dict | None):
        """Show images for a check/return dict (Moov-shaped)."""
        self._views = []
        if item:
            details = item.get("imageViewDetail") or []
            datas = item.get("imageViewData") or []
            for i, ivd in enumerate(datas):
                side = None
                if i < len(details):
                    side = details[i].get("viewSideIndicator")
                if side is None:
                    side = i
                label = "Front" if side == 0 else "Back"
                self._views.append((label, ivd.get("imageData") or b""))
        has_back = any(lbl == "Back" for lbl, _ in self._views)
        self.btn_back.setEnabled(has_back)
        self.btn_front.setChecked(True)
        self.show_side(0)

    def show_side(self, side: int):
        self._current = side
        want = "Front" if side == 0 else "Back"
        data = b""
        for lbl, d in self._views:
            if lbl == want:
                data = d
                break
        self.scene.clear()
        self._pixmap_item = None
        if not data:
            self.info.setText("No image" if not self._views else f"No {want.lower()} image")
            return
        pix = decode_image(data)
        if pix.isNull():
            self.info.setText(f"{want}: could not decode image ({len(data):,} bytes)")
            return
        self._pixmap_item = self.scene.addPixmap(pix)
        self.scene.setSceneRect(self._pixmap_item.boundingRect())
        self.info.setText(f"{want} • {pix.width()}×{pix.height()} px • {len(data):,} bytes")
        if self._fit:
            self.fit()

    # ------------------------------------------------------------------ zoom
    def zoom(self, factor: float):
        self._fit = False
        self.view.scale(factor, factor)

    def fit(self):
        self._fit = True
        if self._pixmap_item:
            self.view.fitInView(self._pixmap_item, Qt.KeepAspectRatio)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._fit:
            self.fit()
