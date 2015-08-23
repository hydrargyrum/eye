
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.Qsci import *
Signal = pyqtSignal
Slot = pyqtSlot

from ..app import qApp
from ..connector import CONNECTOR

__all__ = ('acceptIf', 'CategoryMixin', 'WidgetMixin', 'CentralWidgetMixin')


def acceptIf(ev, cond):
	if cond:
		ev.accept()
	else:
		ev.ignore()


class CategoryMixin(object):
	def __init__(self):
		super(CategoryMixin, self).__init__()
		self._categories = set()
		CONNECTOR.addObject(self)

	def categories(self):
		return self._categories

	def addCategory(self, c):
		if c in self._categories:
			return
		self._categories.add(c)
		CONNECTOR.categoryAdded(self, c)

	def removeCategory(self, c):
		if c not in self._categories:
			return
		self._categories.remove(c)
		CONNECTOR.categoryRemoved(self, c)


class WidgetMixin(CategoryMixin):
	def __init__(self):
		CategoryMixin.__init__(self)

	def giveFocus(self, reason=Qt.OtherFocusReason):
		if not self.isActiveWindow():
			self.activateWindow()

		return self.setFocus(reason)


class CentralWidgetMixin(WidgetMixin):
	def __init__(self):
		WidgetMixin.__init__(self)

	def title(self):
		return ''

	def icon(self):
		return QIcon()

	def parentTabBar(self):
		w = self
		while True:
			if hasattr(w, 'categories') and 'tabwidget' in w.categories():
				break
			w = w.parent()
		return w

	def giveFocus(self, reason=Qt.OtherFocusReason):
		if not self.isActiveWindow():
			self.activateWindow()

		tabBar = self.parentTabBar()
		if tabBar:
			tabBar.setCurrentWidget(self)

		return self.setFocus(reason)
