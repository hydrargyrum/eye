
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.Qsci import *
Signal = pyqtSignal
Slot = pyqtSlot

import logging

from app import qApp


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

