#!/usr/bin/env python
# this project is licensed under the WTFPLv2, see COPYING.txt for details

import argparse
import logging
import os
import sys

import sip
sip.setapi('QString', 2)

from PyQt5.QtCore import pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow
Signal = pyqtSignal
Slot = pyqtSlot

qApp = lambda: QApplication.instance()

from .three import execfile
from . import pathutils
from . import connector


__all__ = ('App', 'qApp', 'main')


class App(QApplication):
	def __init__(self, argv):
		super(App, self).__init__(argv)
		self.setApplicationName('eye')

		logging.basicConfig()
		self.logger = logging.getLogger()

		self.argsFiles = None

		self.lastWindow = None
		self.focusChanged.connect(self._appFocusChanged)

	def initUi(self):
		from .widgets import window

		win = window.Window()
		win.createDefaultMenuBar()
		win.quitRequested.connect(self.quit)
		return win

	def _startupScripts(self):
		import glob
		files = glob.glob(os.path.join(pathutils.getConfigPath('startup'), '*.py'))
		files.sort()
		return files

	def _scriptDict(self):
		return {'qApp': QApplication.instance()}

	def runStartScripts(self):
		for f in self._startupScripts():
			self.logger.debug('execing startup script %s', f)
			try:
				execfile(f, self._scriptDict())
			except Exception:
				self.logger.error('cannot execute startup script %r', f, exc_info=True)

	def run(self):
		self._handleArguments()
		win = self.initUi()
		win.show()
		self.runStartScripts()
		self.openCommandLineFiles()
		self.exec_()

	def _handleArguments(self):
		parser = argparse.ArgumentParser()
		parser.add_argument('files', metavar='FILE', nargs='*')
		parser.add_argument('--debug', action='store_true', default=False)

		argv = self.arguments()[1:]
		args = parser.parse_args(argv)

		if args.debug:
			self.logger.setLevel(logging.DEBUG)

		self.argsFiles = args.files

	def openCommandLineFiles(self):
		if not self.argsFiles:
			return

		win = connector.categoryObjects('window')[0]

		for name in self.argsFiles:
			path, row, col = pathutils.parseFilename(name)
			path = os.path.abspath(path)

			ed = win.bufferOpen(path)
			if row is not None:
				ed.goto1(row, col)

	@Slot(QWidget, QWidget)
	def _appFocusChanged(self, old, new):
		while new and not new.isWindow():
			new = new.parentWidget()
		if not new or not isinstance(new, QMainWindow):
			# exclude dialogs
			return
		self.lastWindow = new


def main():
	# if the default excepthook is used, PyQt 5.5 *aborts* the app when an unhandled exception occurs
	# see http://pyqt.sourceforge.net/Docs/PyQt5/incompatibilities.html
	# as this behaviour is questionable, we restore the old one

	if sys.excepthook is sys.__excepthook__:
		sys.excepthook = lambda *args: sys.__excepthook__(*args)

	app = App(sys.argv)
	app.run()
	return 0

if __name__ == '__main__':
	main()
