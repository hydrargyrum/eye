# this project is licensed under the WTFPLv2, see COPYING.txt for details

import os
from weakref import ref

from PyQt5.QtCore import Qt, pyqtSignal as Signal
from PyQt5.QtWidgets import QMainWindow, QFileDialog, QDockWidget, QWidget

from ..connector import registerSignal
from ..three import str
from ..qt import Slot
from .. import consts
from .helpers import CategoryMixin, acceptIf
from .editor import Editor
from .tabs import TabWidget
from .splitter import SplitManager
from .droparea import DropAreaMixin

__all__ = ('Window',)


class DockWidget(QDockWidget, CategoryMixin):
	def __init__(self, **kwargs):
		super(QDockWidget, self).__init__(**kwargs)
		self.addCategory('dock_container')


class Window(QMainWindow, CategoryMixin, DropAreaMixin):
	"""Main window type.

	This window type should typically be used for editing windows.

	A Window contains a central widget (which is a :any:`SplitManager`), a menu bar, a status bar, toolbars, and
	dock widgets. Dock widgets are widgets which can be placed on the 4 sides of the central widget.

	Access to menu bar, status bar and toolbars is the same as with a :any:`QMainWindow`. Dock widgets access can
	be done with the :any:`addDockable` helper.
	"""

	EditorClass = Editor

	"""Class of the widget to create when a new tab is opened."""

	fileDropped = Signal(str)

	def __init__(self, *args):
		super(Window, self).__init__(*args)

		self.menubar = self.menuBar()

		self.splitter = SplitManager()

		ed = self.EditorClass()
		tabs = TabWidget()
		tabs.addWidget(ed)

		self.splitter.splitAt(None, consts.RIGHT, tabs)

		self.setCentralWidget(self.splitter)

		self.lastFocus = ref(ed)
		from ..app import qApp
		qApp().focusChanged.connect(self._appFocusChanged)

		REGISTRY.append(self)
		self.addCategory('window')

	def createDefaultMenuBar(self):
		menu = self.menubar.addMenu('File')
		menu.addAction('New').triggered.connect(self.bufferNew)
		menu.addAction('Open...').triggered.connect(self.bufferOpenDialog)
		menu.addAction('Save').triggered.connect(self.bufferSave)
		menu.addAction('Quit').triggered.connect(self.quitRequested)

	@Slot()
	def toggleFullScreen(self):
		self.setWindowState(self.windowState() ^ Qt.WindowFullScreen)

	def addDockable(self, area, widget, title=''):
		"""Add a widget to a dock of this window

		:param area: the area where to dock the widget
		:type area: Qt.DockWidgetArea
		:param widget: the widget to add
		:param title: the (optional) title of the widget in the dock
		:returns: the DockWidget wrapping `widget`
		:rtype: QDockWidget
		"""
		dw = DockWidget()
		if title:
			dw.setWindowTitle(title)
		dw.setWidget(widget)
		self.addDockWidget(area, dw)
		return dw

	## buffers
	def currentBuffer(self):
		"""Return the current buffer in this window, which has had focus last."""
		return self.lastFocus()

	@Slot()
	def bufferNew(self):
		"""Open a new, empty editor in current tab container."""
		ed = self.EditorClass()
		cur = self.currentBuffer()
		if cur:
			parent = cur.parentTabBar()
			parent.addWidget(ed)
			ed.giveFocus()
		return ed

	@Slot()
	def bufferNewAtTabs(self, tabbar):
		"""Open a new, empty editor in specified tab container."""
		ed = self.EditorClass()
		tabbar.addWidget(ed)
		return ed

	@Slot()
	def bufferOpenDialog(self):
		path, qfilter = QFileDialog.getOpenFileName(self, self.tr('Open file'), os.path.expanduser('~'))
		if path:
			ed = self.bufferNew()
			ed.openFile(path)

	@Slot()
	def bufferOpen(self, path):
		"""Open a new buffer in current tab container and load specified path."""
		ed = self.bufferNew()
		if ed.openFile(path):
			return ed
		else:
			ed.parentTabBar().closeTab(ed)

	@Slot()
	def bufferClose(self):
		"""Close current buffer."""
		ed = self.currentBuffer()
		parent = ed.parentTabBar()
		parent.closeTab(ed)

	@Slot()
	def bufferSave(self):
		"""Save current buffer."""
		self.currentBuffer().saveFile()

	def _bufferNewSplit(self, orientation, widget=None):
		if widget is None:
			parent = self.currentBuffer().parentTabBar()
		elif hasattr(widget, 'parentTabBar'):
			parent = widget.parentTabBar()
		else:
			parent = widget

		spl, idx = self.splitter.childId(parent)

		ed = self.EditorClass()
		tabs = TabWidget()
		tabs.addWidget(ed)

		DIRS = {
			Qt.Vertical: consts.DOWN,
			Qt.Horizontal: consts.RIGHT
		}
		self.splitter.splitAt(parent, DIRS[orientation], tabs)

	@Slot()
	def bufferSplitHorizontal(self, widget=None):
		"""Split window horizontally at current buffer.

		A new empty editor is created.
		"""
		self._bufferNewSplit(Qt.Horizontal, widget)

	@Slot()
	def bufferSplitVertical(self, widget=None):
		"""Split window vertically at current buffer.

		A new empty editor is created.
		"""
		self._bufferNewSplit(Qt.Vertical, widget)

	## signals
	quitRequested = Signal()

	"""Signal quitRequested()"""

	closing = Signal()

	## events
	def closeEvent(self, ev):
		if acceptIf(ev, self.splitter.close()):
			super(Window, self).closeEvent(ev)
			self.closing.emit()
			REGISTRY.remove(self)

	def canClose(self):
		return self.splitter.canClose()

	def onTabbarLastClosed(self, tw):
		self.splitter.removeWidget(tw)

	@Slot('QWidget*', 'QWidget*')
	def _appFocusChanged(self, old, new):
		if self.centralWidget().isAncestorOf(new):
			self.lastFocus = ref(new)


@registerSignal('tabwidget', 'lastTabClosed')
def onLastTabClosed(tw):
	win = tw.window()
	win.onTabbarLastClosed(tw)


REGISTRY = []
