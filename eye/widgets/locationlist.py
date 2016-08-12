# this project is licensed under the WTFPLv2, see COPYING.txt for details

"""Location list widget

A location is a file path and an optional line number. Locations are typically used for directory-wide search
results (like with grep), or for compile errors/warnings messages, since a location can be accompanied with various
attributes, like a message or a search snippet.
"""

from PyQt5.QtCore import pyqtSignal as Signal
from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem

from ..three import str
from .helpers import WidgetMixin
from .. import consts
from ..connector import registerSignal, disabled
from ..qt import Slot
from ..helpers.intent import sendIntent


__all__ = ('absolutePathRole', 'lineRole', 'columnRole', 'LocationList')

absolutePathRole = consts.registerRole()
lineRole = consts.registerRole()
columnRole = consts.registerRole()


class LocationList(QTreeWidget, WidgetMixin):
	"""Location list widget

	A location is a file path, an optional line number, and various optional attributes.
	A location list widgets displays clickable locations coming from a search, or a compilation.
	"""

	locationActivated = Signal(str, object)

	"""
	Signal locationActivated(path, line)

	:param path: the path of the activated location
	:type path: str
	:param line: the file line number of the activated location
	:type line: int or None
	"""

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

	@Slot()
	def activatePrevious(self):
		"""Select and activate previous item

		If an item is selected in this LocationList, selects the previous item and activates it. If no item
		was currently select, uses the last element.
		"""
		count = self.topLevelItemCount()
		if not count:
			return

		current = self.currentIndex()
		if not current.isValid():
			item = self.topLevelItem(count - 1)
		elif current.row() > 0:
			item = self.topLevelItem(current.row() - 1)
		else:
			return
		self.setCurrentItem(item)

		self.setCurrentItem(item)
		self.activated.emit(self.indexFromItem(item))
		self.itemActivated.emit(item, 0)

	@Slot()
	def activateNext(self):
		"""Select and activate next item

		If an item is selected in this LocationList, selects the next item and activates it. If no item
		was currently select, uses the first element.
		"""
		count = self.topLevelItemCount()
		if not count:
			return

		current = self.currentIndex()
		if not current.isValid():
			item = self.topLevelItem(0)
		elif current.row() < count - 1:
			item = self.topLevelItem(current.row() + 1)
		else:
			return

		self.setCurrentItem(item)
		self.activated.emit(self.indexFromItem(item))
		self.itemActivated.emit(item, 0)


@registerSignal('location_list', 'locationActivated')
@disabled
def locationListOpen(widget, path, loc):
	sendIntent(widget, 'openEditor', path=path, loc=loc, reason='locationlist')

