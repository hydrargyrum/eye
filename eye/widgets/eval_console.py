# this project is licensed under the WTFPLv2, see COPYING.txt for details

"""Interactive evaluator console
"""

from __future__ import print_function

import code
import codecs
from importlib import import_module
import logging
import sys
import traceback

from PyQt5.QtCore import pyqtSlot as Slot, pyqtSignal as Signal, Qt
from PyQt5.QtWidgets import QVBoxLayout, QLineEdit, QPlainTextEdit, QWidget
from six import StringIO, exec_

from ..three import bytes
from ..app import qApp
from ..utils import exceptionLogging
from .helpers import WidgetMixin

__all__ = ('EvalConsole',)


LOGGER = logging.getLogger(__name__)


class HistoryLine(QLineEdit):
	submitted = Signal(str)

	def __init__(self, **kwargs):
		super(HistoryLine, self).__init__(**kwargs)
		self.history = []
		self.history_path = None
		self.idx = None
		self.returnPressed.connect(self.submit)

	@Slot()
	def submit(self):
		self._addHistory()
		self.submitted.emit(self.text())
		self.setText('')

	def _addHistory(self):
		self.idx = None
		if not self.text():
			return

		self.history.append(self.text())

		if self.history_path:
			with exceptionLogging(reraise=False, logger=LOGGER):
				with codecs.open(self.history_path, 'a', 'utf-8') as fd:
					print(self.text(), file=fd)

	def setHistoryFile(self, path):
		if path is not None:
			with open(path, 'a+') as fd:
				self.history = [line.strip() for line in fd]
		self.history_path = path

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
		self.interpreter = code.InteractiveInterpreter(self.namespace)

		layout = QVBoxLayout()
		self.setLayout(layout)

		self.display = QPlainTextEdit(self)
		self.display.setReadOnly(True)
		self.line = HistoryLine()
		self.line.submitted.connect(self.execCode)

		layout.addWidget(self.display)
		layout.addWidget(self.line)

		self.addCategory('eval_console')

	def import_all_qt(self):
		self.interpreter.runsource('from eye.helpers.qt_all import *')

	@Slot(str)
	def execCode(self, code):
		# TODO be able to define functions, do ifs, fors

		import eye
		self.namespace['eye'] = eye
		self.namespace['app'] = qApp()
		self.namespace['window'] = qApp().lastWindow
		self.namespace['editor'] = self.namespace['window'].currentBuffer()
		self.namespace['import_all_qt'] = self.import_all_qt

		output = u'>>> %s\n' % code
		output += capture_output(self.interpreter.runsource, code)
		self.display.appendPlainText(output)

		# avoid retaining references to widgets
		self.namespace.pop('window')
		self.namespace.pop('editor')


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
