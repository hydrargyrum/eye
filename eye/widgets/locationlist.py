# this project is licensed under the WTFPLv2, see COPYING.txt for details

from PyQt5.QtCore import pyqtSlot as Slot, pyqtSignal as Signal, QModelIndex
from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem

from ..three import str
from .helpers import WidgetMixin
from .. import consts


__all__ = ('absolutePathRole', 'lineRole', 'columnRole', 'LocationList')

absolutePathRole = consts.registerRole()
lineRole = consts.registerRole()
columnRole = consts.registerRole()


class LocationList(QTreeWidget, WidgetMixin):
	locationActivated = Signal(str, object)

	def __init__(self, **kwargs):
		super(LocationList, self).__init__(**kwargs)

		self.setAlternatingRowColors(True)
		self.setAllColumnsShowFocus(True)
		self.setRootIsDecorated(False)

		self.addCategory('location_list')

		self.itemActivated.connect(self._resultActivated)

		self.cols = []

	def setColumns(self, cols):
		names = {
			'path': self.tr('Path'),
			'line': self.tr('Line'),
			'snippet': self.tr('Snippet'),
			'message': self.tr('Message'),
		}

		self.cols = list(cols)
		qcols = []
		for c in self.cols:
			qcols.append(names.get(c, c))
		self.setHeaderItem(QTreeWidgetItem(qcols))

	def clear(self):
		super(LocationList, self).clear()

	@Slot(dict)
	def addItem(self, d):
		path = d.get('shortpath', d['path'])
		line = int(d.get('line', 0))
		cols = []
		for c in self.cols:
			if c == 'path':
				cols.append(path)
			else:
				cols.append(str(d.get(c, '')))

		item = QTreeWidgetItem(cols)
		item.setData(0, absolutePathRole, path)
		if line:
			item.setData(0, lineRole, line)
		self.addTopLevelItem(item)

	@Slot()
	def resizeAllColumns(self):
		for i in range(self.columnCount()):
			self.resizeColumnToContents(i)

	@Slot(QModelIndex)
	def _resultActivated(self, qitem, col_number):
		if not qitem:
			return

		path = qitem.data(0, absolutePathRole) # TODO use roles to have shortname vs longname
		loc = qitem.data(0, lineRole) or None
		self.locationActivated.emit(path, loc)


"""
@registerSignal('location_list', 'locationActivated')
@disabled
def locationActivated(widget, path, loc):
	buffers.openEditor(path, loc)
"""
