#!/usr/bin/env python

import sys, os
import logging
import argparse

from PyQt4.QtCore import *
from PyQt4.QtGui import *
Signal = pyqtSignal
Slot = pyqtSlot

qApp = lambda: QApplication.instance()

from . import utils


__all__ = 'App qApp'.split()


class App(QApplication):
	def __init__(self, argv):
		QApplication.__init__(self, argv)
		self.setApplicationName('vedit')

		from . import connector
		self.connector = connector.EventConnector()

		logging.basicConfig()
		self.logger = logging.getLogger()

		self.argsFiles = None

	def initUi(self):
		from .widgets import window

		self.win = window.Window()
		window.windows.addWindow(self.win)
		self.win.createDefaultMenuBar()
		self.win.quitRequested.connect(self.quit)

	def _startupScripts(self):
		import glob
		files = glob.glob(os.path.join(self.getConfigPath('startup'), '*.py'))
		files.sort()
		return files

	def _scriptDict(self):
		return {'qApp': QApplication.instance()}

	def runStartScripts(self):
		for f in self._startupScripts():
			self.logger.info('execing startup script %s' % f)
			try:
				execfile(f, self._scriptDict())
			except Exception, e:
				self.logger.exception(e)

	def run(self):
		self._handleArguments()
		self.initUi()
		self.win.show()
		self.runStartScripts()
		self.openCommandLineFiles()
		self.exec_()

	def _handleArguments(self):
		parser = argparse.ArgumentParser()
		parser.add_argument('files', metavar='FILE', nargs='*')
		parser.add_argument('--debug', action='store_true', default=False)

		argv = [unicode(arg) for arg in self.arguments()[1:]]
		args = parser.parse_args(argv)

		if args.debug:
			self.logger.setLevel(logging.DEBUG)

		self.argsFiles = args.files

	def openCommandLineFiles(self):
		if not self.argsFiles:
			return
		for i in self.argsFiles:
			name = unicode(i)
			path, row, col = utils.parseFilename(name)
			ed = self.win.bufferOpen(path)
			if row is not None:
				ed.goto1(row, col)

	def getConfigPath(self, *args):
		try:
			import xdg.BaseDirectory
			return xdg.BaseDirectory.save_config_path('vedit', *args)
		except ImportError:
			return os.path.join(os.path.expanduser('~/.config/vedit'), *args)


def main():
	app = App(sys.argv)
	app.run()
	return 0

if __name__ == '__main__':
	main()
