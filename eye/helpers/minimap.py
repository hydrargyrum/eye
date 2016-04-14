
from PyQt5.QtCore import pyqtSignal as Signal, pyqtSlot as Slot
from PyQt5.QtWidgets import QLabel, QWidget, QHBoxLayout

from ..connector import *
from ..widgets.editor import Editor
from ..widgets.window import Window


__all__ = ('MiniMap', 'EditorReplacement')


class MiniMap(QLabel):
	pass


class EditorReplacement(QWidget):
	EditorClass = Editor

	titleChanged = Signal()
	iconChanged = Signal()

	def __init__(self, **kwargs):
		super(EditorReplacement, self).__init__(**kwargs)

		layout = QHBoxLayout()
		self.setLayout(layout)
		layout.setContentsMargins(0, 0, 0, 0)
	
		self.editor = self.EditorClass(parent=self)
		layout.addWidget(self.editor)
		self.minimap = MiniMap('foo', self)
		layout.addWidget(self.minimap)

		self.editor.titleChanged.connect(self.titleChanged)
		#~ self.editor.iconChanged.connect(self.iconChanged)

	def __getattr__(self, attr):
		return getattr(self.editor, attr)


def install():
	Window.EditorClass = EditorReplacement

