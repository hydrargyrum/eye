
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.Qsci import *
Signal = pyqtSignal
Slot = pyqtSlot

from app import qApp
from .helpers import CategoryMixin, acceptIf
from .editor import Editor
from .tabs import TabWidget
from .splitter import SplitManager

__all__ = 'Window windows'.split()


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

	def parentTabBarOf(self, w):
		while not isinstance(w, TabWidget):
			w = w.parent()
		return w

	@Slot()
	def bufferNew(self):
		ed = Editor()
		if self.lastFocus:
			par = self.parentTabBarOf(self.lastFocus)
			par.addEditor(ed)
			par.focusBuffer(ed)
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
			self.parentTabBarOf(ed).closeTab(ed)

	@Slot()
	def bufferSave(self):
		self.currentBuffer().saveFile()

	def closeEvent(self, ev):
		acceptIf(ev, self.splitter.requestClose())

	@Slot(QWidget, QWidget)
	def appFocusChanged(self, old, new):
		if self.centralWidget().isAncestorOf(new):
			self.lastFocus = new


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
