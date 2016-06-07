# this project is licensed under the WTFPLv2, see COPYING.txt for details

"""Tab widget
"""

from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import QTabWidget, QTabBar, QStackedWidget
Signal = pyqtSignal

from ..three import str
from ..qt import Slot
from .droparea import DropAreaMixin
from .helpers import WidgetMixin

__all__ = ('TabWidget',)


class TabBar(QTabBar):
	def __init__(self, **kwargs):
		super(TabBar, self).__init__(**kwargs)
		self.setTabsClosable(True)
		self.setMovable(True)
		self.setUsesScrollButtons(True)


class TabWidget(QTabWidget, WidgetMixin, DropAreaMixin):
	"""Tab widget class

	By default, instances of this class have the category `"tabwidget"` (see :doc:`eye.connector`).
	"""

	lastTabClosed = Signal()

	"""Signal lastTabClosed()

	This signal is emitted when the last tab of this tab widget has been closed.
	"""

	fileDropped = Signal(str)

	def __init__(self, **kwargs):
		super(TabWidget, self).__init__(**kwargs)

		self.tabCloseRequested.connect(self._tabCloseRequested)
		self.currentChanged.connect(self._currentChanged)

		bar = TabBar()
		self.setTabBar(bar)

		self.addCategory('tabwidget')

	def currentBuffer(self):
		"""Return the widget from the current tab"""
		return self.currentWidget()

	def _idxContainerOf(self, widget):
		while widget is not self:
			idx = self.indexOf(widget)
			if idx >= 0:
				return idx
			widget = widget.parent()
		return -1

	def closeTab(self, ed):
		"""Close the tab containing the specified widget and return True if it can be

		The tab can't be closed if the widget has a `closeFile()` method which returns `True` when it is
		called. This method allows a tab content to reject closing if a file wasn't saved.
		"""
		assert self.isAncestorOf(ed)

		if hasattr(ed, 'closeFile'):
			if not ed.closeFile():
				return False

		idx = self._idxContainerOf(ed)

		self.removeTab(idx)
		return True

	def setCurrentWidget(self, widget):
		"""Select the tab containing the specified widget"""
		assert self.isAncestorOf(widget)
		idx = self._idxContainerOf(widget)
		if idx >= 0:
			self.setCurrentIndex(idx)

	def addWidget(self, widget):
		"""Add a new tab with the specified widget"""
		self.addTab(widget, widget.icon(), widget.title())
		if hasattr(widget, 'titleChanged'):
			widget.titleChanged.connect(self._subTitleChanged)
		if hasattr(widget, 'iconChanged'):
			widget.iconChanged.connect(self._subIconChanged)

	def widgetSetFilename(self, widget, filename):
		idx = self.indexOf(widget)
		self.setTabText(idx, self.tr('%s') % filename)

	def widgets(self):
		"""Return widgets contained in tabs"""
		return [self.widget(i) for i in range(self.count())]

	def _selectTab(self, step, s1, e1, rotate, s2, e2):
		for idx in range(s1, e1, step):
			if self.isTabEnabled(idx):
				self.setCurrentIndex(idx)
				return
		if not rotate:
			return
		for idx in range(s2, e2, step):
			if self.isTabEnabled(idx):
				self.setCurrentIndex(idx)
				return

	@Slot()
	def selectPrevTab(self, rotate=False):
		"""Select previous tab

		If `rotate` is `True` and the current tab is the first tab, the last tab is selected.
		"""
		cur = self.currentIndex()
		self._selectTab(-1, cur - 1, -1, rotate, self.count() - 1, cur)

	@Slot()
	def selectPrevTabRotate(self):
		"""Select previous tab or last if current is the first tab"""
		self.selectPrevTab(True)

	@Slot()
	def selectNextTab(self, rotate=False):
		"""Select next tab

		If `rotate` is `True` and the current tab is the last tab, the first tab is selected.
		"""
		cur = self.currentIndex()
		self._selectTab(1, cur + 1, self.count(), rotate, 0, cur)

	@Slot()
	def selectNextTabRotate(self):
		"""Select next tab or first tab if current is the last tab"""
		self.selectNextTab(True)

	def requestClose(self):
		"""Close all tabs and return `True` if all could be closed

		See :any:`closeTab`.
		"""
		for i in range(self.count()):
			w = self.widget(0)
			if w.closeFile():
				self.removeTab(0)
			else:
				return False
		return True

	## private
	@Slot(int)
	def _tabCloseRequested(self, idx):
		widget = self.widget(idx)
		if widget.closeFile():
			self.removeTab(idx)

	@Slot(int)
	def _currentChanged(self, idx):
		hadFocus = self.hasFocus()
		self.setFocusProxy(self.widget(idx))
		self.tabBar().setFocusProxy(self.widget(idx))
		if hadFocus:
			self.setFocus()

	@Slot()
	def _subTitleChanged(self):
		w = self.sender()
		idx = self.indexOf(w)
		if idx < 0:
			return
		self.setTabText(idx, w.title())

	@Slot()
	def _subIconChanged(self):
		w = self.sender()
		idx = self.indexOf(w)
		if idx < 0:
			return
		self.setTabIcon(idx, w.icon())

	# override
	def tabInserted(self, idx):
		super(TabWidget, self).tabInserted(idx)
		self._changeTabBarVisibility()

	def tabRemoved(self, idx):
		super(TabWidget, self).tabRemoved(idx)
		self._changeTabBarVisibility()

		w = self._findRemovedWidget()
		w.setParent(None)

		if self.count() == 0:
			self.lastTabClosed.emit()
		elif self.currentIndex() == idx:
			self.currentWidget().giveFocus()

	def _findRemovedWidget(self):
		# implementation detail, but no access to the removed widget
		base = self.findChild(QStackedWidget)
		for c in base.children():
			if not c.isWidgetType():
				continue
			if self.indexOf(c) < 0:
				return c

	def _changeTabBarVisibility(self):
		visible = (self.count() > 1)
		self.tabBar().setVisible(visible)

	@Slot()
	def refocus(self):
		"""Give focus to the widget inside the current tab"""
		self.currentWidget().setFocus(Qt.OtherFocusReason)
