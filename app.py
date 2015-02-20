#!/usr/bin/env python

import sys, os
import logging
from PyQt4.QtCore import *
from PyQt4.QtGui import *
Signal = pyqtSignal
Slot = pyqtSlot

qApp = lambda: QApplication.instance()

import widgets
import utils


__all__ = 'App qApp'.split()


class App(QApplication):
	def __init__(self, argv):
		QApplication.__init__(self, argv)
		self.logger = logging.getLogger()
		logging.basicConfig()
		self.win = widgets.Window()
		widgets.windows.addWindow(self.win)
		self.win.createDefaultMenuBar()
		self.win.quitRequested.connect(self.quit)

	def _startupScripts(self):
		import glob
		files = glob.glob(os.path.join(self.getConfigPath('startup'), '*.py'))
		files.sort()
		return files

	def _scriptDict(self):
		return {'qApp': QApplication.instance(), 'widgets': widgets}

	def runStartScripts(self):
		for f in self._startupScripts():
			self.logger.info('execing startup script %s' % f)
			try:
				execfile(f, self._scriptDict())
			except Exception, e:
				self.logger.exception(e)

	def run(self):
		self.win.show()
		self.runStartScripts()
		self._handleArguments()
		self.exec_()

	def _handleArguments(self):
		for i in self.arguments()[1:]:
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

if __name__ == '__main__':
	main()
