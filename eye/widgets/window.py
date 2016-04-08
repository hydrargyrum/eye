# this project is licensed under the WTFPLv2, see COPYING.txt for details

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

		self.splitter = SplitManager()

		ed = Editor()
		tabs = TabWidget()
		tabs.addWidget(ed)

		self.splitter.splitAt(None, Qt.Horizontal, tabs)
		tabs.lastTabClosed.connect(self._tabbarLastClosed)
		
		self.setCentralWidget(self.splitter)

		self.lastFocus = ed
		qApp().focusChanged.connect(self._appFocusChanged)

		self.addCategory('window')

	def createDefaultMenuBar(self):
		menu = self.menubar.addMenu('File')
		menu.addAction('New').triggered.connect(self.bufferNew)
		menu.addAction('Open...').triggered.connect(self.bufferOpenDialog)
		menu.addAction('Save').triggered.connect(self.bufferSave)
		menu.addAction('Quit').triggered.connect(self.quitRequested)

	## buffers
	def currentBuffer(self):
		return self.lastFocus

	@Slot()
	def bufferNew(self):
		ed = Editor()
		if self.lastFocus:
			parent = self.lastFocus.parentTabBar()
			parent.addWidget(ed)
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
	def bufferClose(self):
		ed = self.currentBuffer()
		parent = ed.parentTabBar()
		parent.closeTab(ed)

	@Slot()
	def bufferSave(self):
		self.currentBuffer().saveFile()

	def _bufferNewSplit(self, orientation):
		parent = self.currentBuffer().parentTabBar()
		spl, idx = self.splitter.childId(parent)

		ed = Editor()
		tabs = TabWidget()
		tabs.addWidget(ed)

		self.splitter.splitAt(parent, orientation, tabs)
		tabs.lastTabClosed.connect(self._tabbarLastClosed)

	@Slot()
	def bufferSplitHorizontal(self):
		self._bufferNewSplit(Qt.Horizontal)

	@Slot()
	def bufferSplitVertical(self):
		self._bufferNewSplit(Qt.Vertical)

	## signals
	quitRequested = Signal()

	## events
	def closeEvent(self, ev):
		acceptIf(ev, self.splitter.requestClose())

	@Slot()
	def _tabbarLastClosed(self):
		self.splitter.removeWidget(self.sender())

	@Slot(QWidget, QWidget)
	def _appFocusChanged(self, old, new):
		if self.centralWidget().isAncestorOf(new):
			self.lastFocus = new

	def addDockable(self, area, widget):
		dw = QDockWidget()
		self.addDockWidget(area, dw)
		dw.setWidget(widget)
