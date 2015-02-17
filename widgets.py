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
		self.tabs = TabWidget(self)
		self.setCentralWidget(self.tabs)

		self.menubar = self.menuBar()
		ed = Editor()
		self.tabs.addEditor(ed)

	def createDefaultMenuBar(self):
		menu = self.menubar.addMenu('File')
		menu.addAction('New').triggered.connect(self.bufferNew)
		menu.addAction('Open...').triggered.connect(self.bufferOpenDialog)
		menu.addAction('Save').triggered.connect(self.bufferSave)
		menu.addAction('Quit').triggered.connect(self.wantQuit)

	wantQuit = Signal()

	def currentBuffer(self):
		return self.tabs.currentBuffer()

	@Slot()
	def bufferNew(self):
		ed = Editor()
		self.tabs.addEditor(ed)
		self.tabs.focusBuffer(ed)
		return ed

	@Slot()
	def bufferOpenDialog(self):
		path = QFileDialog.getOpenFileName(self, self.tr('Open file'), os.path.expanduser('~'))
		if path:
			path = unicode(path)
			self.currentBuffer().openFile(path)

	@Slot()
	def bufferOpen(self, path):
		ed = self.bufferNew()
		if ed.openFile(path):
			return ed
		else:
			self.tabs.closeTab(ed)

	@Slot()
	def bufferSave(self):
		self.currentBuffer().saveFile()

	def closeEvent(self, ev):
		acceptIf(ev, self.tabs.requestClose())


class Editor(QsciScintilla):
	def __init__(self, *a):
		QsciScintilla.__init__(self, *a)

		self.path = ''
		self.modificationChanged.connect(self.titleChanged)

	def title(self):
		t = os.path.basename(self.path)
		if self.isModified():
			return '%s*' % t
		else:
			return t

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
			qApp.logger.exception(e)
			return False
		self.path = path
		self.setModified(False)
		self.titleChanged.emit()
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
		try:
			with open(path) as f:
				self.setText(f.read().decode('utf-8'))
		except IOError, e:
			qApp.logger.exception(e)
			return False
		self.setModified(False)
		return True

	titleChanged = Signal()

	# events
	def closeEvent(self, ev):
		acceptIf(ev, self.closeFile())


class TabWidget(QTabWidget):
	def __init__(self, *args):
		QTabWidget.__init__(self, *args)
		self.setMovable(True)
		self.setTabsClosable(True)
		self.setUsesScrollButtons(True)
		self.tabCloseRequested.connect(self.onTabCloseRequested)

	def currentBuffer(self):
		return self.currentWidget()

	def focusBuffer(self, ed):
		self.setCurrentWidget(ed)

	def closeTab(self, ed):
		if ed.closeFile():
			self.removeTab(self.indexOf(ed))
			return True
		else:
			return False

	@Slot(int)
	def onTabCloseRequested(self, idx):
		widget = self.widget(idx)
		if widget.closeFile():
			self.removeTab(idx)

	@Slot()
	def _subTitleChanged(self):
		w = self.sender()
		idx = self.indexOf(w)
		if idx < 0:
			return
		self.setTabText(idx, w.title())

	def addEditor(self, editor):
		self.addTab(editor, editor.title())
		editor.titleChanged.connect(self._subTitleChanged)

	def widgetSetFilename(self, widget, filename):
		idx = self.indexOf(widget)
		self.setTabText(idx, self.tr('%1').arg(filename))

	def currentBuffer(self):
		return self.currentWidget()

	def widgets(self):
		return [self.widget(i) for i in xrange(self.count())]

	def requestClose(self):
		for i in xrange(self.count()):
			w = self.widget(0)
			if w.closeFile():
				self.removeTab(0)
			else:
				return False
		return True


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
