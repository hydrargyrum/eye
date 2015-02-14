#!/usr/bin/env python

import sys, os
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.Qsci import *
Signal = pyqtSignal
Slot = pyqtSlot


__all__ = 'Window windows Editor'.split()


def acceptIf(ev, cond):
	if cond:
		ev.accept()
	else:
		ev.ignore()


class Window(QMainWindow):
	def __init__(self, *a):
		QMainWindow.__init__(self, *a)
		self.editor = Editor(self)
		self.setCentralWidget(self.editor)

		self.menubar = self.menuBar()

	def createDefaultMenuBar(self):
		menu = self.menubar.addMenu('File')
		menu.addAction('Open...').triggered.connect(self.bufferOpenFile)
		menu.addAction('Save').triggered.connect(self.bufferSave)
		menu.addAction('Quit').triggered.connect(self.wantQuit)

	wantQuit = Signal()

	@Slot()
	def bufferOpenFile(self):
		path = QFileDialog.getOpenFileName(self, self.tr('Open file'), os.path.expanduser('~'))
		if path:
			path = unicode(path)
			self.editor.openFile(path)

	@Slot()
	def bufferSave(self):
		self.editor.saveFile()

	def closeEvent(self, ev):
		acceptIf(ev, self.editor.closeFile())


class Editor(QsciScintilla):
	def __init__(self, *a):
		QsciScintilla.__init__(self, *a)

		self.path = ''

	def _getFilename(self):
		if not self.path:
			return ''
		return os.path.basename(self.path)

	def saveFile(self):
		path = self.path
		if not path:
			path = QFileDialog.getSaveFileName(self, self.tr('Save file'), os.path.expanduser('~'))
			if not path:
				return False
			path = unicode(path)
		try:
			with open(path, 'w') as f:
				f.write(self.text().toUtf8())
		except IOError, e:
			print e
			return False
		self.setModified(False)
		return True

	def closeFile(self):
		ret = True

		if self.isModified():
			file = self._getFilename() or '<unnamed>'

			answer = QMessageBox.question(self, self.tr('Unsaved file'), self.tr('%1 has been modified, do you want to close it?').arg(file), QMessageBox.Discard | QMessageBox.Cancel | QMessageBox.Save)
			if answer == QMessageBox.Discard:
				ret = True
			elif answer == QMessageBox.Cancel:
				ret = False
			elif answer == QMessageBox.Save:
				ret = self.saveFile()
		return ret

	def openFile(self, path):
		if not self.closeFile():
			return False
		self.path = path
		with open(path) as f:
			self.setText(f.read().decode('utf-8'))
		self.setModified(False)

	# events
	def closeEvent(self, ev):
		acceptIf(ev, self.closeFile())


class WindowRegistry(QObject):
	def __init__(self):
		QObject.__init__(self)
		self.windows = []

	def addWindow(self, window):
		self.windows.append(window)
		self.windowOpened.emit(window)

	def delWindow(self, window):
		self.windows.remove(window)
		self.windowClosed(window)

	windowOpened = Signal(Window)
	windowClosed = Signal(Window)


windows = WindowRegistry()
