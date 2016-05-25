# this project is licensed under the WTFPLv2, see COPYING.txt for details

"""Interactive evaluator console
"""

from PyQt5.QtCore import pyqtSlot, Qt
from PyQt5.QtWidgets import QVBoxLayout, QLineEdit, QPlainTextEdit, QWidget

from six import StringIO, exec_
import sys
import traceback

from ..app import qApp
from .helpers import WidgetMixin

Slot = pyqtSlot

__all__ = ('EvalConsole',)


class HistoryLine(QLineEdit):
	def __init__(self, **kwargs):
		super(HistoryLine, self).__init__(**kwargs)
		self.lines = []
		self.idx = None
		self.returnPressed.connect(self._addHistory)

	@Slot()
	def _addHistory(self):
		self.idx = None
		self.lines.insert(0, self.text())

	def keyPressEvent(self, ev):
		if ev.key() == Qt.Key_Up:
			if self.idx is None:
				if not self.lines:
					return
				self.idx = 0
			elif self.idx + 1 < len(self.lines):
				self.idx += 1
			else:
				return

			self.setText(self.lines[self.idx])
		elif ev.key() == Qt.Key_Down:
			if self.idx is None:
				return
			elif self.idx <= 0:
				self.idx = None
				self.setText('')
				return
			else:
				self.idx -= 1

			self.setText(self.lines[self.idx])
		else:
			super(HistoryLine, self).keyPressEvent(ev)


class EvalConsole(QWidget, WidgetMixin):
	"""Interactive evaluator console widget

	Text typed in the console will be executed as Python code, in the context of the EYE app, which allows to do
	some operations on widgets directly from this console.

	The `editor` variable is automatically set to the last focused editor widget in the current window.
	The `window` variable is set to current window. The `eye` module is imported, and so are the submodules
	already imported by the configuration files.

	During execution of a line, stdout and stderr are captured and are output to this widget console.
	Do not execute statemements taking a lot of time as it would freeze the UI.

	This widget can typically added as a dock widget.
	"""

	def __init__(self, **kwargs):
		super(EvalConsole, self).__init__(**kwargs)
		self.namespace = {}

		layout = QVBoxLayout()
		self.setLayout(layout)

		self.display = QPlainTextEdit(self)
		self.line = HistoryLine()
		self.line.returnPressed.connect(self.execLine)

		layout.addWidget(self.display)
		layout.addWidget(self.line)

	def _exec(self, line):
		res = None
		try:
			try:
				res = eval(line, self.namespace)
			except SyntaxError:
				pass
			else:
				if res is not None:
					print(repr(res))
				return
			exec_(line, self.namespace)
		except Exception as e:
			traceback.print_exc()

	@Slot()
	def execLine(self):
		# TODO be able to define functions, do ifs, fors

		import eye
		self.namespace['eye'] = eye
		self.namespace['app'] = qApp()
		self.namespace['window'] = qApp().lastWindow
		self.namespace['editor'] = self.namespace['window'].currentBuffer()

		text = self.line.text()
		self.line.setText('')

		output = '>>> %s\n' % text
		output += capture_output(self._exec, text)
		self.display.appendPlainText(output)


def capture_output(cb, *args, **kwargs):
	sio = StringIO()
	old = sys.stdout, sys.stderr
	sys.stdout, sys.stderr = sio, sio
	try:
		res = cb(*args, **kwargs)
	finally:
		sys.stdout, sys.stderr = old
	return sio.getvalue()
