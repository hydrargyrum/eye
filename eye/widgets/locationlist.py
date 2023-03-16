# this project is licensed under the WTFPLv2, see COPYING.txt for details

"""Location list widget

A location is a file path and an optional line number. Locations are typically used for directory-wide search
results (like with grep), or for compile errors/warnings messages, since a location can be accompanied with various
attributes, like a message or a search snippet.
"""

from PyQt5.QtCore import Qt, QModelIndex
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtWidgets import QTreeView

from eye import consts
from eye.connector import register_signal, disabled
from eye.consts import AbsolutePathRole
from eye.helpers.intent import send_intent
from eye.qt import Signal, Slot
from eye.widgets.helpers import WidgetMixin

__all__ = ('lineRole', 'columnRole', 'LocationList')

lineRole = consts.registerRole()
columnRole = consts.registerRole()


class LocationList(QTreeView, WidgetMixin):
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

		self.dataModel = QStandardItemModel()
		self.setModel(self.dataModel)

		self.setAlternatingRowColors(True)
		self.setAllColumnsShowFocus(True)
		self.setRootIsDecorated(False)
		self.setSelectionBehavior(self.SelectRows)
		self.setWindowTitle(self.tr('Location list'))

		self.activated.connect(self._result_activated)

		self.cols = []

		self.add_category('location_list')

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
		self.dataModel.setHorizontalHeaderLabels(qcols)

	def clear(self):
		self.dataModel.clear()

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

		items = [QStandardItem(col) for col in cols]
		items[0].setData(d['path'], AbsolutePathRole)
		if line:
			items[0].setData(line, lineRole)

		for item in items:
			item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)

		self.dataModel.appendRow(items)

	@Slot()
	def resizeAllColumns(self):
		for i in range(self.model().columnCount()):
			self.resizeColumnToContents(i)

	@Slot(QModelIndex)
	def _result_activated(self, qidx):
		if not qidx.isValid():
			return

		qidx = qidx.sibling(qidx.row(), 0)
		path = self.model().data(qidx, AbsolutePathRole)
		# TODO use roles to have shortname vs longname
		line = self.model().data(qidx, lineRole) or None
		self.locationActivated.emit(path, (line,))

	@Slot()
	def activatePrevious(self):
		"""Select and activate previous item

		If an item is selected in this LocationList, selects the previous item and activates it. If no item
		was currently select, uses the last element.
		"""
		count = self.model().rowCount()
		if not count:
			return

		current = self.currentIndex()

		if not current.isValid():
			current = QModelIndex(count - 1, 0)
		elif current.row() > 0:
			current = current.sibling(current.row() - 1, 0)
		else:
			return
		self.setCurrentIndex(current)
		self.activated.emit(current)

	@Slot()
	def activateNext(self):
		"""Select and activate next item

		If an item is selected in this LocationList, selects the next item and activates it. If no item
		was currently select, uses the first element.
		"""
		count = self.model().rowCount()
		if not count:
			return

		current = self.currentIndex()
		if not current.isValid():
			current = QModelIndex(0, 0)
		elif current.row() < count - 1:
			current = current.sibling(current.row() + 1, 0)
		else:
			return

		self.setCurrentIndex(current)
		self.activated.emit(current)


@register_signal('location_list', 'locationActivated')
@disabled
def locationListOpen(widget, path, loc):
	send_intent(widget, 'open_editor', path=path, loc=loc, reason='locationlist')

