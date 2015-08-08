
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.Qsci import *
Signal = pyqtSignal
Slot = pyqtSlot

import os

from ..app import qApp
from .helpers import CategoryMixin, acceptIf
from .editor import Editor
from .tabs import TabWidget
from .splitter import SplitManager

__all__ = ('Window',)


class Window(QMainWindow, CategoryMixin):
	def __init__(self, *a):
		QMainWindow.__init__(self, *a)
		CategoryMixin.__init__(self)

		self.menubar = self.menuBar()
		ed = Editor()

		tabs = TabWidget()
		tabs.addEditor(ed)

		self.splitter = SplitManager()
		self.splitter.splitAt(None, Qt.Horizontal, tabs)
		
		self.setCentralWidget(self.splitter)

		self.lastFocus = ed
		qApp().focusChanged.connect(self.appFocusChanged)

		self.addCategory('window')

	def createDefaultMenuBar(self):
		menu = self.menubar.addMenu('File')
		menu.addAction('New').triggered.connect(self.bufferNew)
		menu.addAction('Open...').triggered.connect(self.bufferOpenDialog)
		menu.addAction('Save').triggered.connect(self.bufferSave)
		menu.addAction('Quit').triggered.connect(self.quitRequested)

	quitRequested = Signal()

	def currentBuffer(self):
		#return self.tabs.currentBuffer()
		return self.lastFocus

	@Slot()
	def bufferNew(self):
		ed = Editor()
		if self.lastFocus:
			parent = self.lastFocus.parentTabBar()
			parent.addEditor(ed)
			ed.giveFocus()
		return ed

	@Slot()
	def bufferOpenDialog(self):
		path = QFileDialog.getOpenFileName(self, self.tr('Open file'), os.path.expanduser('~'))
		if path:
			self.currentBuffer().openFile(path)

	@Slot()
	def bufferOpen(self, path):
		ed = self.bufferNew()
		if ed.openFile(path):
			return ed
		else:
			ed.parentTabBar().closeTab(ed)

	@Slot()
	def bufferSave(self):
		self.currentBuffer().saveFile()

	def closeEvent(self, ev):
		acceptIf(ev, self.splitter.requestClose())

	@Slot(QWidget, QWidget)
	def appFocusChanged(self, old, new):
		if self.centralWidget().isAncestorOf(new):
			self.lastFocus = new
