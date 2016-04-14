# this project is licensed under the WTFPLv2, see COPYING.txt for details

from PyQt5.QtCore import pyqtSlot
from PyQt5.QtWidgets import QVBoxLayout, QLineEdit, QPlainTextEdit, QWidget
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

	@Slot()
	def execLine(self):
		# TODO catch prints
		# TODO be able to define functions, do ifs, fors

		self.namespace['window'] = qApp().lastWindow
		self.namespace['editor'] = self.namespace['window'].currentBuffer()

		text = self.line.text()
		self.line.setText('')

		res = None
		output = '>>> %s\n' % text
		try:
			try:
				res = eval(text, self.namespace)
			except SyntaxError:
				exec text in self.namespace
		except Exception as e:
			output += '%s\n' % traceback.format_exc()
		else:
			if res is not None:
				output += '%r\n' % res
		self.display.appendPlainText(output)
