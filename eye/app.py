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
from . import connector
from .widgets import window


__all__ = 'App qApp'.split()


class App(QApplication):
	def __init__(self, argv):
		QApplication.__init__(self, argv)
		self.setApplicationName('eye')

		logging.basicConfig()
		self.logger = logging.getLogger()

		self.argsFiles = None

	def initUi(self):
		win = window.Window()
		win.createDefaultMenuBar()
		win.quitRequested.connect(self.quit)
		return win

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
		win = self.initUi()
		win.show()
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
			win = connector.categoryObjects('window')[0]
			ed = win.bufferOpen(path)
			if row is not None:
				ed.goto1(row, col)

	def getConfigPath(self, *args):
		try:
			import xdg.BaseDirectory
			return xdg.BaseDirectory.save_config_path('eyeditor', *args)
		except ImportError:
			return os.path.join(os.path.expanduser('~/.config/eyeditor'), *args)


def main():
	app = App(sys.argv)
	app.run()
	return 0

if __name__ == '__main__':
	main()
