# this project is licensed under the WTFPLv2, see COPYING.txt for details

"""Location list widget

A location list widget displays a list of files and some lines in this file.
It's typically used for displaying search results, where the list will contain the lines of files matching a pattern,
in a grep fashion. It could also display compile errors, with the files and their erroneous lines.
"""

from PyQt5.QtCore import pyqtSlot as Slot, pyqtSignal as Signal
from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem

from ..three import str
from .helpers import WidgetMixin
from .. import consts
from ..connector import registerSignal, disabled
from ..helpers import buffers


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
		item.setData(0, absolutePathRole, d['path'])
		if line:
			item.setData(0, lineRole, line)
		self.addTopLevelItem(item)

	@Slot()
	def resizeAllColumns(self):
		for i in range(self.columnCount()):
			self.resizeColumnToContents(i)

	@Slot(QTreeWidgetItem, int)
	def _resultActivated(self, qitem, col_number):
		if not qitem:
			return

		path = qitem.data(0, absolutePathRole) # TODO use roles to have shortname vs longname
		line = qitem.data(0, lineRole) or None
		self.locationActivated.emit(path, (line,))


@registerSignal('location_list', 'locationActivated')
@disabled
def locationListOpen(widget, path, loc):
	buffers.openEditor(path, loc)

