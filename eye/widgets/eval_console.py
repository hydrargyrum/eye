# this project is licensed under the WTFPLv2, see COPYING.txt for details

"""Interactive Python evaluator console
"""

from __future__ import print_function

import code
import codecs
from importlib import reload
from io import StringIO
import logging
import os
import rlcompleter
import sys

from PyQt5.QtCore import Qt, QStringListModel
from PyQt5.QtWidgets import QVBoxLayout, QLineEdit, QPlainTextEdit, QWidget, QAction, QCompleter

from eye.app import qApp
from eye.qt import Signal, Slot
from eye.utils import exceptionLogging
from eye.widgets.helpers import WidgetMixin

__all__ = (
	'EvalConsole', 'NAMESPACE', 'registerConsoleSymbol',
)


LOGGER = logging.getLogger(__name__)


NAMESPACE = {}

"""Additional shared namespace between all :any:`EvalConsole` objects.

Example::

	def hello():
		print('Hello world')

	eye.widgets.eval_console.NAMESPACE['hello'] = hello

Then, the `hello()` function can be called in the console.
"""

NAMESPACE["reload"] = reload


class PythonCompleter(QCompleter):
	def __init__(self, *args, **kwargs):
		super(PythonCompleter, self).__init__(*args, **kwargs)
		self.setModel(QStringListModel())

	def splitPath(self, path):
		# hack, this function seems called everytime
		# so we can force our custom completion
		completer = rlcompleter.Completer(self.widget().parent().namespace)
		text = self.widget().text()
		text = text[:self.widget().cursorPosition()]
		i = 0
		comps = []
		while True:
			comp = completer.complete(text, i)
			if comp is None:
				break
			comps.append(comp)
			i += 1

		self.model().setStringList(comps)

		return super(PythonCompleter, self).splitPath(path)


class HistoryLine(QLineEdit):
	submitted = Signal(str)

	def __init__(self, **kwargs):
		super(HistoryLine, self).__init__(**kwargs)
		self.history = []
		self.history_path = None
		self.idx = None
		self.returnPressed.connect(self.submit)
		self.setCompleter(PythonCompleter())

	@Slot()
	def submit(self):
		text = self.text()

		self._addHistory(text)
		self.setText('')
		self.submitted.emit(text)

	def _addHistory(self, text):
		self.idx = None
		if not text or (self.history and self.history[-1] == text):
			return
		self.history.append(text)

		if self.history_path:
			with exceptionLogging(reraise=False, logger=LOGGER):
				with codecs.open(self.history_path, 'a', 'utf-8') as fd:
					print(text, file=fd)

	def setHistoryFile(self, path):
		if path is not None:
			self.history = []
			if os.path.exists(path):
				with open(path, 'r+') as fd:
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


class PlainTextEdit(QPlainTextEdit):
	def contextMenuEvent(self, ev):
		menu = self.createStandardContextMenu()
		menu.addSeparator()
		for action in self.actions():
			menu.addAction(action)
		menu.exec_(ev.globalPos())


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

		self.display = PlainTextEdit(self)
		self.display.setReadOnly(True)
		clearAction = QAction(self.tr('Clear'), self.display)
		clearAction.triggered.connect(self.display.clear)
		self.display.addAction(clearAction)

		self.line = HistoryLine()
		self.line.submitted.connect(self.execCode)
		self.line.installEventFilter(self)
		self.line.completer().popup().installEventFilter(self)
		self.setFocusProxy(self.line)

		layout.addWidget(self.display)
		layout.addWidget(self.line)

		self.setWindowTitle(self.tr('Eval console'))

		self.addCategory('eval_console')

	def import_all_qt(self):
		self.interpreter.runsource('from eye.helpers.qt_all import *')

	@Slot(str)
	def execCode(self, code):
		# TODO be able to define functions, do ifs, fors

		self.setNamespace()
		try:
			output = u'>>> %s\n' % code
			output += capture_output(self.interpreter.runsource, code)
			self.display.appendPlainText(output)
		finally:
			self.protectNamespace()

	def setNamespace(self):
		import eye
		self.namespace['eye'] = eye
		self.namespace['app'] = qApp()
		self.namespace['window'] = qApp().lastWindow
		self.namespace['editor'] = self.namespace['window'].currentBuffer()
		self.namespace['import_all_qt'] = self.import_all_qt
		self.namespace.update(NAMESPACE)

	def protectNamespace(self):
		# avoid retaining references to widgets
		self.namespace.pop('window', None)
		self.namespace.pop('editor', None)

	def eventFilter(self, obj, event):
		if event.type() in (event.FocusIn, event.FocusOut):
			if self.line.hasFocus():
				self.setNamespace()
			else:
				self.protectNamespace()
		return False


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


def registerConsoleSymbol(name):
	"""Decorator to register a function on the eval console

	Example::

		@registerConsoleSymbol('foo')
		def foo():
			pass

	Is equivalent to::

		def foo():
			pass

		NAMESPACE['foo'] = foo

	"""

	def decorator(cb):
		NAMESPACE[name] = cb
		return cb
	return decorator
