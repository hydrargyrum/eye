
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.Qsci import *
Signal = pyqtSignal
Slot = pyqtSlot

from ..app import qApp
from .helpers import WidgetMixin, acceptIf

__all__ = ('TabWidget',)


class TabBar(QTabBar):
	def __init__(self, *args):
		QTabBar.__init__(self, *args)
		self.setTabsClosable(True)
		self.setMovable(True)
		self.setUsesScrollButtons(True)


class TabWidget(QTabWidget, WidgetMixin):
	def __init__(self, *args):
		QTabWidget.__init__(self, *args)
		WidgetMixin.__init__(self)

		self.tabCloseRequested.connect(self._tabCloseRequested)
		self.currentChanged.connect(self._currentChanged)
		self.setTabBar(TabBar())

		self.addCategory('tabwidget')

	def currentBuffer(self):
		return self.currentWidget()

	def closeTab(self, ed):
		if ed.closeFile():
			self.removeTab(self.indexOf(ed))
			return True
		else:
			return False

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

	def addEditor(self, editor):
		self.addTab(editor, editor.title())
		editor.titleChanged.connect(self._subTitleChanged)

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

	def tabInserted(self, idx):
		QTabWidget.tabInserted(self, idx)
		self._changeTabBarVisibility()

	def tabRemoved(self, idx):
		QTabWidget.tabRemoved(self, idx)
		self._changeTabBarVisibility()

		w = self._findRemovedWidget()
		w.setParent(None)

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
