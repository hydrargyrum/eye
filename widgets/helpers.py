
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.Qsci import *
Signal = pyqtSignal
Slot = pyqtSlot

from app import qApp

__all__ = 'acceptIf CategoryMixin'


def acceptIf(ev, cond):
	if cond:
		ev.accept()
	else:
		ev.ignore()


class CategoryMixin(object):
	def __init__(self):
		super(CategoryMixin, self).__init__()
		self._categories = set()
		qApp().connector.addObject(self)

	def categories(self):
		return self._categories

	def addCategory(self, c):
		if c in self._categories:
			return
		self._categories.add(c)
		qApp().connector.categoryAdded(self, c)

	def removeCategory(self, c):
		if c not in self._categories:
			return
		self._categories.remove(c)
		qApp().connector.categoryRemoved(self, c)

