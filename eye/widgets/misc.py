# this project is licensed under the WTFPLv2, see COPYING.txt for details

from PyQt5.QtCore import pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QPlainTextEdit, QLabel, QWidget
Signal = pyqtSignal
Slot = pyqtSlot

import logging
from weakref import ref

from ..app import qApp
from .helpers import WidgetMixin

__all__ = ('LogWidget', 'PositionIndicator')


class LogWidget(QPlainTextEdit):
	class LogHandler(logging.Handler):
		def __init__(self, widget):
			super(LogWidget.LogHandler, self).__init__()
			self.widget = widget
			self.setFormatter(logging.Formatter('%(asctime)s %(message)s'))

		def emit(self, record):
			self.widget.appendPlainText(self.format(record))

	def __init__(self, parent=None):
		super(LogWidget, self).__init__(parent=parent)
		self.handler = LogWidget.LogHandler(self)
		self.setReadOnly(True)

	def install(self):
		qApp().logger.addHandler(self.handler)

	def uninstall(self):
		qApp().logger.removeHandler(self.handler)


class PositionIndicator(QLabel, WidgetMixin):
	format = '%(percent)3d%% %(line)5d:%(col)3d'

	def __init__(self, **kwargs):
		super(PositionIndicator, self).__init__(**kwargs)
		self.lastFocus = None

		qApp().focusChanged.connect(self.focusChanged)

	@Slot(QWidget, QWidget)
	def focusChanged(self, _, new):
		if not hasattr(new, 'categories'):
			return
		if 'editor' not in new.categories():
			return
		if new.window() != self.window():
			return

		if self.lastFocus:
			lastFocus = self.lastFocus()
			lastFocus.cursorPositionChanged.disconnect(self.onPosChanged)
			lastFocus.linesChanged.disconnect(self.onLinesChanged)

		self.lastFocus = ref(new)
		new.cursorPositionChanged.connect(self.onPosChanged)
		new.linesChanged.connect(self.onLinesChanged)
		self.updateLabel()

	@Slot()
	def onLinesChanged(self):
		self.updateLabel()

	@Slot(int, int)
	def onPosChanged(self, ln, col):
		self.updateLabel()

	@Slot()
	def updateLabel(self):
		line, col = self.lastFocus().getCursorPosition()
		line, col = line + 1, col + 1
		lines = self.lastFocus().lines()

		d = dict(line=line, col=col, percent=line * 100. / lines)
		self.setText(self.format % d)
