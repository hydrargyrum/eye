# this project is licensed under the WTFPLv2, see COPYING.txt for details

from PyQt5.QtCore import pyqtSignal as Signal, pyqtSlot as Slot, QSize, Qt
from PyQt5.QtGui import QBrush, QPainter
from PyQt5.QtWidgets import QFrame, QSizePolicy, QWidget, QHBoxLayout

from ..connector import CategoryMixin
from ..widgets.editor import Editor
from ..widgets.window import Window


__all__ = ('MiniMap', 'EditorReplacement')


class MiniMap(QFrame, CategoryMixin):
	lineClicked = Signal(int)

	def __init__(self, editor=None, **kwargs):
		super(MiniMap, self).__init__(**kwargs)
		self.editor = editor
		self.lines = []
		self.proportional_thickness = True
		self.setFixedWidth(10)
		self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Expanding)
		self.addCategory('minimap')

	def setLines(self, lines):
		self.lines = lines

	def mousePressEvent(self, ev):
		line = ev.pos().y() * self.editor.lines() / self.height()
		self.lineClicked.emit(line)

	def mouseMoveEvent(self, ev):
		self.mousePressEvent(ev)

	def paintEvent(self, ev):
		painter = QPainter(self)
		painter.fillRect(0, 0, self.width(), self.height(), Qt.white) # TODO bg color
		if not self.editor:
			return

		total = self.editor.lines()
		lineheight = int(max(1, self.height() / total)) if self.proportional_thickness else 1
		for line in self.lines:
			line = line * self.height() / total
			painter.fillRect(0, line, self.width(), lineheight, Qt.red)

	# TODO mouse cursor changes over highlight zone
	# TODO thicker zone for easier clicks?
	# TODO different colored highlight zone types (e.g. search, compile error, bookmark, etc.)
	# TODO 	by genre? i.e. annotation, margin, etc.


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

	def __getattr__(self, attr):
		return getattr(self.editor, attr)


def install():
	Window.EditorClass = EditorReplacement

