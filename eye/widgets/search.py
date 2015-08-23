
from PyQt4.QtCore import *
from PyQt4.QtGui import *
Signal = pyqtSignal
Slot = pyqtSlot

from .helpers import WidgetMixin
from .. import consts
from ..helpers import file_search
from ..reutils import csToQtEnum


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


class SearchOptionsButton(QPushButton):
	def __init__(self):
		QPushButton.__init__(self)

		self.setText(self.tr('Options'))

		menu = QMenu()
		self.actionCi = menu.addAction(self.tr('Case insensitive'))

		menu.addSeparator()
		self.actionFormat = QActionGroup(self)
		self.actionPlain = menu.addAction(self.tr('Plain text'))
		self.actionRe = menu.addAction(self.tr('Regular expression'))
		self.actionGlob = menu.addAction(self.tr('Glob pattern'))
		self.actionFormat.addAction(self.actionPlain)
		self.actionFormat.addAction(self.actionRe)
		self.actionFormat.addAction(self.actionGlob)

		self.actionRoot = menu.addAction(self.tr('Search in best root dir'))

		for act in [self.actionCi, self.actionRe, self.actionPlain, self.actionGlob]:
			act.setCheckable(True)
		self.actionPlain.setChecked(True)

		self.setMenu(menu)

	def shouldFindRoot(self):
		return self.actionRoot.isChecked()

	def caseSensitive(self):
		return not self.actionCi.isChecked()

	def reFormat(self):
		if self.actionPlain.isChecked():
			return QRegExp.FixedString
		elif self.actionRe.isChecked():
			return QRegExp.RegExp
		elif self.actionGlob.isChecked():
			return QRegExp.WildcardUnix


class SearchWidget(QWidget, WidgetMixin):
	def __init__(self):
		QWidget.__init__(self)
		WidgetMixin.__init__(self)

		layout = QGridLayout()
		self.setLayout(layout)

		self.exprEdit = QLineEdit()
		self.exprEdit.returnPressed.connect(self.returnPressed)

		self.optionsButton = SearchOptionsButton()

		self.pluginChoice = QComboBox()
		plugins = sorted(file_search.enabledPlugins(), key=lambda p: p.name())
		for plugin in plugins:
			self.pluginChoice.addItem(plugin.name(), plugin.id)

		self.results = ResultsWidget()

		layout.addWidget(self.exprEdit, 0, 0)
		layout.addWidget(self.optionsButton, 0, 1)
		layout.addWidget(self.pluginChoice, 0, 2)
		layout.addWidget(self.results, 1, 0, 1, -1)

		self.addCategory('file_search_widget')

	def setPlugin(self, id):
		index = self.pluginChoice.findData(id)
		if index >= 0:
			self.pluginChoice.setCurrentIndex(index)

	def setText(self, text):
		self.exprEdit.setText(text)

	def selectedPlugin(self):
		return self.pluginChoice.itemData(self.pluginChoice.currentIndex()).toString()

	def regexp(self):
		re = QRegExp(self.exprEdit.text())
		re.setCaseSensitivity(csToQtEnum(self.optionsButton.caseSensitive()))
		re.setPatternSyntax(self.optionsButton.reFormat())
		return re

	def shouldFindRoot(self):
		return self.optionsButton.shouldFindRoot()

	returnPressed = Signal()
