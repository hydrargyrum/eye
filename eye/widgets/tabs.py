# this project is licensed under the WTFPLv2, see COPYING.txt for details

from PyQt5.QtCore import pyqtSignal, pyqtSlot, Qt
from PyQt5.QtWidgets import QTabWidget, QTabBar, QStackedWidget
Signal = pyqtSignal
Slot = pyqtSlot

from .helpers import WidgetMixin

__all__ = ('TabWidget',)


class TabBar(QTabBar):
	def __init__(self, *args):
		QTabBar.__init__(self, *args)
		self.setTabsClosable(True)
		self.setMovable(True)
		self.setUsesScrollButtons(True)

	def focusInEvent(self, ev):
		QTabBar.focusInEvent(self, ev)
		self.focused.emit()

	focused = Signal()


class TabWidget(QTabWidget, WidgetMixin):
	lastTabClosed = Signal()

	def __init__(self, *args):
		QTabWidget.__init__(self, *args)
		WidgetMixin.__init__(self)

		self.tabCloseRequested.connect(self._tabCloseRequested)
		self.currentChanged.connect(self._currentChanged)

		bar = TabBar()
		self.setTabBar(bar)
		bar.focused.connect(self.refocus)

		self.addCategory('tabwidget')

	def currentBuffer(self):
		return self.currentWidget()

	def closeTab(self, ed):
		if ed.closeFile():
			self.removeTab(self.indexOf(ed))
			return True
		else:
			return False

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
		return [self.widget(i) for i in xrange(self.count())]

	def requestClose(self):
		for i in xrange(self.count()):
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
		if self.hasFocus():
			self.widget(idx).setFocus(Qt.OtherFocusReason)

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

	def tabInserted(self, idx):
		QTabWidget.tabInserted(self, idx)
		self._changeTabBarVisibility()

	def tabRemoved(self, idx):
		QTabWidget.tabRemoved(self, idx)
		self._changeTabBarVisibility()

		w = self._findRemovedWidget()
		w.setParent(None)

		if self.count() == 0:
			self.lastTabClosed.emit()

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
