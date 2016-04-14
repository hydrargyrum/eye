# this project is licensed under the WTFPLv2, see COPYING.txt for details

from PyQt5.QtCore import pyqtSlot
from PyQt5.QtWidgets import QVBoxLayout, QLineEdit, QPlainTextEdit, QWidget

from six import StringIO, exec_
import sys
import traceback

from ..app import qApp
from .helpers import WidgetMixin

Slot = pyqtSlot

__all__ = ('EvalConsole',)


class EvalConsole(QWidget, WidgetMixin):
	def __init__(self, **kwargs):
		super(EvalConsole, self).__init__(**kwargs)
		self.namespace = {}

		layout = QVBoxLayout()
		self.setLayout(layout)

		self.display = QPlainTextEdit(self)
		self.line = QLineEdit(self)
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
