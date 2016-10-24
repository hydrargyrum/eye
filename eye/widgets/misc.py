# this project is licensed under the WTFPLv2, see COPYING.txt for details

import logging
from weakref import ref

from PyQt5.QtWidgets import QPlainTextEdit, QLabel, QWidget

from ..app import qApp
from ..qt import Slot
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
	"""Widget indicating cursor position of currently focused editor

	When cursor position changes or focus goes to another editor widget, the text of this label is refreshed.
	"""

	format = '{percent:3.0f}% {line:5d}:{col:3d}'

	"""Text format of the label

	Uses PEP-3101 string formatting. Usable keys are `line`, `col`, `percent`, `offset`, `path`, `title` and `editor`.
	"""

	def __init__(self, format=None, **kwargs):
		super(PositionIndicator, self).__init__(**kwargs)
		if format is not None:
			self.format = format

		self.lastFocus = lambda: None

		qApp().focusChanged.connect(self.focusChanged)

	@Slot('QWidget*', 'QWidget*')
	def focusChanged(self, _, new):
		if not hasattr(new, 'categories'):
			return
		if 'editor' not in new.categories():
			return
		if new.window() != self.window():
			return

		lastFocus = self.lastFocus()
		if lastFocus:
			lastFocus.cursorPositionChanged.disconnect(self.updateLabel)
			lastFocus.linesChanged.disconnect(self.updateLabel)

		self.lastFocus = ref(new)
		new.cursorPositionChanged.connect(self.updateLabel)
		new.linesChanged.connect(self.updateLabel)
		self.updateLabel()

	@Slot()
	def updateLabel(self):
		ed = self.lastFocus()

		line, col = ed.getCursorPosition()
		offset = ed.cursorOffset()
		line, col = line + 1, col + 1
		lines = ed.lines()

		d = {
			'line': line,
			'col': col,
			'percent': line * 100. / lines,
			'offset': offset,
			'path': ed.path,
			'title': ed.windowTitle(),
			'editor': ed,
		}
		self.setText(self.format.format(**d))
