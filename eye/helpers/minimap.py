# this project is licensed under the WTFPLv2, see COPYING.txt for details

from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QBrush, QPen, QPainter, QPolygon, QIcon
from PyQt5.QtWidgets import QFrame, QSizePolicy, QWidget, QHBoxLayout

from ..connector import CategoryMixin, registerSignal, disabled
from ..widgets.editor import Editor, SciModification
from ..widgets.window import Window
from ..widgets.helpers import acceptIf
from ..three import range
from ..qt import Signal, Slot


__all__ = ('MiniMap', 'EditorReplacement', 'scrollOnClick', 'install')


class MiniMap(QFrame, CategoryMixin):
	lineClicked = Signal(int)

	def __init__(self, editor=None, **kwargs):
		super(MiniMap, self).__init__(**kwargs)

		self.editor = editor
		if self.editor:
			self.editor.sciModified.connect(self.editorModification)

		self.markerStyles = {}
		self.indicatorStyles = {}

		self.setFixedWidth(10)
		self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Expanding)
		self.setCursor(Qt.OpenHandCursor)

		self.addCategory('minimap')

	@Slot(SciModification)
	def editorModification(self, mod):
		update_mask = self.editor.SC_MOD_CHANGEINDICATOR | self.editor.SC_MOD_CHANGEMARKER

		if mod.modificationType & update_mask:
			self.update()

	def setLines(self, lines):
		self.lines = lines

	def _doMove(self, ev):
		line = ev.pos().y() * self.editor.lines() / self.height()
		line = max(0, min(self.editor.lines(), line))
		self.lineClicked.emit(line)

	def mousePressEvent(self, ev):
		self.setCursor(Qt.ClosedHandCursor)
		self._doMove(ev)

	def mouseMoveEvent(self, ev):
		self._doMove(ev)

	def mouseReleaseEvent(self, ev):
		self.setCursor(Qt.OpenHandCursor)

	def paintEvent(self, ev):
		painter = QPainter(self)

		painter.fillRect(0, 0, self.width(), self.height(), Qt.white) # TODO bg color
		if not self.editor:
			return

		total = self.editor.lines()

		for name in self.editor.markers:
			mpainter = self.markerStyles.get(name)
			if mpainter is None:
				continue

			marker = self.editor.markers[name]
			for line in marker.listAll():
				mpainter.draw(painter, line, total, self)

		for name in self.editor.indicators:
			mpainter = self.indicatorStyles.get(name)
			if mpainter is None:
				continue

			indicator = self.editor.indicators[name]
			for offset_start, offset_end, _ in indicator.iterRanges():
				line_start, _ = self.editor.lineIndexFromPosition(offset_start)
				line_end, _ = self.editor.lineIndexFromPosition(offset_end)
				for line in range(line_start, line_end + 1):
					mpainter.draw(painter, line, total, self)

	# TODO mouse cursor changes over highlight zone
	# TODO thicker zone for easier clicks?


class EditorReplacement(QWidget):
	EditorClass = Editor

	def __init__(self, **kwargs):
		super(EditorReplacement, self).__init__(**kwargs)

		layout = QHBoxLayout()
		self.setLayout(layout)
		layout.setContentsMargins(0, 0, 0, 0)

		self.editor = self.EditorClass(parent=self)
		layout.addWidget(self.editor)
		self.minimap = MiniMap(editor=self.editor, parent=self)
		layout.addWidget(self.minimap)
		self.setFocusProxy(self.editor)

		self.editor.windowTitleChanged.connect(self.setWindowTitle)
		self.setWindowTitle(self.editor.windowTitle())

		self.editor.windowIconChanged.connect(self.setWindowIcon)
		self.setWindowIcon(self.editor.windowIcon())

		self.editor.windowModifiedChanged.connect(self.setWindowModified)
		self.setWindowModified(self.editor.isWindowModified())

	def closeEvent(self, ev):
		acceptIf(ev, self.editor.close())

	def __getattr__(self, attr):
		return getattr(self.editor, attr)

	@Slot(QIcon)
	def setWindowIcon(self, icon):
		# redefine as a slot to avoid keeping useless refs to self
		super(EditorReplacement, self).setWindowIcon(icon)


@registerSignal('minimap', 'lineClicked')
@disabled
def scrollOnClick(minimap, line):
	minimap.editor.ensureLineVisible(line)


def install():
	Window.EditorClass = EditorReplacement

## styles

class MiniMapStyle(object):
	pass


class Shape(MiniMapStyle):
	Circle = 1
	Square = 2
	Triangle = 3

	def __init__(self, shape, pen=None, brush=None):
		self.shape = shape
		self.pen = pen or QPen()
		self.brush = brush or QBrush()

	def draw(self, painter, line, total, minimap):
		line = line * minimap.height() / total

		painter.setPen(self.pen)
		painter.setBrush(self.brush)
		if self.shape == Shape.Circle:
			painter.drawEllipse(0, line - 4, 8, 8)
		elif self.shape == Shape.Square:
			painter.drawRect(0, line - 4, 8, 8)
		elif self.shape == Shape.Triangle:
			triangle = QPolygon([QPoint(0, line - 4), QPoint(0, line + 4), QPoint(8, line)])
			painter.drawPolygon(triangle)


class Line(MiniMapStyle):
	def __init__(self, pen=None, proportional_thickness=False):
		self.pen = pen or QPen()
		self.proportional_thickness = proportional_thickness

	def draw(self, painter, line, total, minimap):
		line = line * minimap.height() / total
		pen = QPen(self.pen)

		if self.proportional_thickness:
			lineheight = int(max(1, minimap.height() / total))
			pen.setWidth(lineheight)

		painter.setPen(pen)
		painter.drawLine(0, line, minimap.width(), line)
