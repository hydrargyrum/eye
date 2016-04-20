# this project is licensed under the WTFPLv2, see COPYING.txt for details

from PyQt5.QtCore import pyqtSignal, pyqtSlot, Qt
from PyQt5.QtWidgets import QTabWidget, QTabBar, QStackedWidget
Signal = pyqtSignal
Slot = pyqtSlot

from .helpers import WidgetMixin

__all__ = ('TabWidget',)


class TabBar(QTabBar):
	def __init__(self, **kwargs):
		super(TabBar, self).__init__(**kwargs)
		self.setTabsClosable(True)
		self.setMovable(True)
		self.setUsesScrollButtons(True)


class TabWidget(QTabWidget, WidgetMixin):
	lastTabClosed = Signal()

	def __init__(self, **kwargs):
		super(TabWidget, self).__init__(**kwargs)

		self.tabCloseRequested.connect(self._tabCloseRequested)
		self.currentChanged.connect(self._currentChanged)

		bar = TabBar()
		self.setTabBar(bar)

		self.addCategory('tabwidget')

	def currentBuffer(self):
		return self.currentWidget()

	def _idxContainerOf(self, widget):
		while widget is not self:
			idx = self.indexOf(widget)
			if idx >= 0:
				return idx
			widget = widget.parent()
		return -1

	def closeTab(self, ed):
		assert self.isAncestorOf(ed)
		if ed.closeFile():
			idx = self._idxContainerOf(ed)

			self.removeTab(idx)
			return True
		else:
			return False

	def setCurrentWidget(self, widget):
		assert self.isAncestorOf(widget)
		idx = self._idxContainerOf(widget)
		if idx >= 0:
			self.setCurrentIndex(idx)

	def addWidget(self, widget):
		self.addTab(widget, widget.icon(), widget.title())
		if hasattr(widget, 'titleChanged'):
			widget.titleChanged.connect(self._subTitleChanged)
		if hasattr(widget, 'iconChanged'):
			widget.iconChanged.connect(self._subIconChanged)

	def widgetSetFilename(self, widget, filename):
		idx = self.indexOf(widget)
		self.setTabText(idx, self.tr('%s') % filename)

	def widgets(self):
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
		cur = self.currentIndex()
		self._selectTab(-1, cur - 1, -1, rotate, self.count() - 1, cur)

	@Slot()
	def selectPrevTabRotate(self):
		self.selectPrevTab(True)

	@Slot()
	def selectNextTab(self, rotate=False):
		cur = self.currentIndex()
		self._selectTab(1, cur + 1, self.count(), rotate, 0, cur)

	@Slot()
	def selectNextTabRotate(self):
		self.selectNextTab(True)

	def requestClose(self):
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
		self.setFocusProxy(self.widget(idx))
		self.tabBar().setFocusProxy(self.widget(idx))

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
		self.currentWidget().setFocus(Qt.OtherFocusReason)
