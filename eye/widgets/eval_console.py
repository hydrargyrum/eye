# this project is licensed under the WTFPLv2, see COPYING.txt for details

"""Interactive evaluator console
"""

from __future__ import print_function

import sys
import traceback

from PyQt5.QtCore import pyqtSlot as Slot, pyqtSignal as Signal, Qt
from PyQt5.QtWidgets import QVBoxLayout, QLineEdit, QPlainTextEdit, QWidget
from six import StringIO, exec_

from ..three import bytes
from ..app import qApp
from .helpers import WidgetMixin

__all__ = ('EvalConsole',)


class HistoryLine(QLineEdit):
	submitted = Signal(str)

	def __init__(self, **kwargs):
		super(HistoryLine, self).__init__(**kwargs)
		self.history = []
		self.idx = None
		self.returnPressed.connect(self.submit)

	@Slot()
	def submit(self):
		self._addHistory()
		self.submitted.emit(self.text())
		self.setText('')

	def _addHistory(self):
		self.idx = None
		self.history.append(self.text())

	def keyPressEvent(self, ev):
		if ev.key() == Qt.Key_Up:
			if self.idx is None:
				if not self.history:
					return
				self.idx = len(self.history) - 1
			elif self.idx > 0:
				self.idx -= 1
			else:
				return

			self.setText(self.history[self.idx])
		elif ev.key() == Qt.Key_Down:
			if self.idx is None:
				return
			elif self.idx + 1 >= len(self.history):
				self.idx = None
				self.setText('')
				return
			else:
				self.idx += 1

			self.setText(self.history[self.idx])
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
		self.display.setReadOnly(True)
		self.line = HistoryLine()
		self.line.submitted.connect(self.execCode)

		layout.addWidget(self.display)
		layout.addWidget(self.line)

	def _exec(self, line):
		res = None
		try:
			try:
				res = eval(line, self.namespace)  # pylint: disable=eval-used
			except SyntaxError:
				pass
			else:
				if res is not None:
					print(repr(res))
				return
			exec_(line, self.namespace)
		except Exception:
			traceback.print_exc()

	@Slot(str)
	def execCode(self, code):
		# TODO be able to define functions, do ifs, fors

		import eye
		self.namespace['eye'] = eye
		self.namespace['app'] = qApp()
		self.namespace['window'] = qApp().lastWindow
		self.namespace['editor'] = self.namespace['window'].currentBuffer()

		output = u'>>> %s\n' % code
		output += capture_output(self._exec, code)
		self.display.appendPlainText(output)


def capture_output(cb, *args, **kwargs):
	sio = StringIO()
	old = sys.stdout, sys.stderr
	sys.stdout, sys.stderr = sio, sio
	try:
		res = cb(*args, **kwargs)
	finally:
		sys.stdout, sys.stderr = old

	res = sio.getvalue()
	if isinstance(res, bytes):
		res = res.decode('utf-8', 'replace')
	return res
