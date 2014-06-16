#!/usr/bin/env python

import sys, os
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.Qsci import *
Signal = pyqtSignal
Slot = pyqtSlot


__all__ = 'Window windows Editor'.split()


class Window(QMainWindow):
	def __init__(self, *a):
		QMainWindow.__init__(self, *a)
		self.editor = Editor(self)
		self.setCentralWidget(self.editor)


class Editor(QsciScintilla):
	def __init__(self, *a):
		QsciScintilla.__init__(self, *a)


class WindowRegistry(QObject):
	def __init__(self):
		self.windows = []

	def add_window(self, window):
		self.windows.append(window)

	def del_window(self, window):
		self.windows.remove(window)


windows = WindowRegistry()
