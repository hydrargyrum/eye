
from PyQt4.QtCore import *
from PyQt4.QtGui import *
Signal = pyqtSignal
Slot = pyqtSlot

from .helpers import WidgetMixin
from .. import consts


__all__ = ('absolutePathRole', 'lineRole', 'columnRole', 'ResultsWidget')

absolutePathRole = consts.registerRole()
lineRole = consts.registerRole()
columnRole = consts.registerRole()

class ResultsWidget(QTreeWidget, WidgetMixin):
	def __init__(self, parent=None):
		QTreeWidget.__init__(self)
		WidgetMixin.__init__(self)

		self.setAlternatingRowColors(True)
		self.setAllColumnsShowFocus(True)
		self.setRootIsDecorated(False)

		self.addCategory('search_results')

		self.itemActivated.connect(self._resultActivated)

	def setColumns(self, loc=False, snippet=False, extra=None):
		cols = [self.tr('File')]
		if loc:
			cols.append(self.tr('Line'))
		if snippet:
			cols.append(self.tr('Result'))
		cols.extend(extra or [])

		self.setHeaderItem(QTreeWidgetItem(cols))

	def addItem(self, path, loc=None, snippet=None, extra=None):
		cols = [path]
		if loc is not None:
			cols.append(loc)
		if snippet is not None:
			cols.append(snippet)
		cols.extend(extra or [])

		item = QTreeWidgetItem(cols)
		item.setData(0, absolutePathRole, path)
		if loc is not None:
			item.setData(0, lineRole, loc)
		self.addTopLevelItem(item)

	@Slot(QModelIndex)
	def _resultActivated(self, qitem, col_number):
		if not qitem:
			return

		path = qitem.data(0, absolutePathRole).toString() # TODO use roles to have shortname vs longname
		loc = qitem.data(0, lineRole).toInt() or None
		self.resultActivated.emit(path, loc)

	resultActivated = Signal(unicode, object)

