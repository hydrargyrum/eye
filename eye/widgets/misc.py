
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.Qsci import *
Signal = pyqtSignal
Slot = pyqtSlot

import logging

from ..app import qApp
from .helpers import UtilsMixin

__all__ = 'LogWidget PositionIndicator'.split()


class LogWidget(QPlainTextEdit):
	class LogHandler(logging.Handler):
		def __init__(self, widget):
			logging.Handler.__init__(self)
			self.widget = widget
			self.setFormatter(logging.Formatter('%(asctime)s %(message)s'))

		def emit(self, record):
			self.widget.appendPlainText(self.format(record))

	def __init__(self, parent=None):
		QPlainTextEdit.__init__(self, parent)
		self.handler = LogWidget.LogHandler(self)
		self.setReadOnly(True)

	def install(self):
		qApp().logger.addHandler(self.handler)

	def uninstall(self):
		qApp().logger.removeHandler(self.handler)


class PositionIndicator(QLabel, UtilsMixin):
	def __init__(self, *a):
		QLabel.__init__(self, *a)
		self.lastFocus = None

		qApp().focusChanged.connect(self.focusChanged)

	@Slot(QWidget, QWidget)
	def focusChanged(self, _, new):
		if not hasattr(new, 'categories'):
			return
		if 'editor' not in new.categories():
			return
		if new.parentWindow() != self.parentWindow():
			return

		if self.lastFocus:
			self.lastFocus.cursorPositionChanged.disconnect(self.updatePos)

		new.cursorPositionChanged.connect(self.updatePos)
		self.updatePos(*new.getCursorPosition())
		self.lastFocus = new

	@Slot(int, int)
	def updatePos(self, ln, col):
		self.setText('%d : %d' % (ln + 1, col + 1))
