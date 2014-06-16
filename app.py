#!/usr/bin/env python

import sys, os
from PyQt4.QtCore import *
from PyQt4.QtGui import *
Signal = pyqtSignal
Slot = pyqtSlot

from widgets import *


class App(QApplication):
	def __init__(self, argv):
		QApplication.__init__(self, argv)
		self.win = Window()

	def run(self):
		self.win.show()
		self.exec_()


def main():
	app = App(sys.argv)
	app.run()

if __name__ == '__main__':
	main()
