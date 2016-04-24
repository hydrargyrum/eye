# this project is licensed under the WTFPLv2, see COPYING.txt for details

from PyQt5.QtCore import pyqtSignal, pyqtSlot, QModelIndex, QRegExp
from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem, QPushButton, QMenu
from PyQt5.QtWidgets import QWidget, QActionGroup, QGridLayout, QLineEdit, QComboBox
Signal = pyqtSignal
Slot = pyqtSlot

import os

from ..three import str
from .. import consts
from .helpers import WidgetMixin
from ..helpers import file_search, buffers
from ..reutils import csToQtEnum
from .locationlist import LocationList


__all__ = ('absolutePathRole', 'lineRole', 'columnRole', 'SearchWidget')

absolutePathRole = consts.registerRole()
lineRole = consts.registerRole()
columnRole = consts.registerRole()


class SearchOptionsButton(QPushButton):
	def __init__(self, **kwargs):
		super(SearchOptionsButton, self).__init__(**kwargs)

		self.setText(self.tr('Options'))

		menu = QMenu()
		self.actionCi = menu.addAction(self.tr('Case insensitive'))

		menu.addSeparator()
		self.actionFormat = QActionGroup(self)
		self.actionPlain = menu.addAction(self.tr('Plain text'))
		self.actionPlain.setEnabled(False)
		self.actionRe = menu.addAction(self.tr('Regular expression'))
		self.actionGlob = menu.addAction(self.tr('Glob pattern'))
		self.actionGlob.setEnabled(False)
		self.actionFormat.addAction(self.actionPlain)
		self.actionFormat.addAction(self.actionRe)
		self.actionFormat.addAction(self.actionGlob)

		self.actionRoot = menu.addAction(self.tr('Search in best root dir'))

		for act in [self.actionCi, self.actionRe, self.actionPlain, self.actionGlob, self.actionRoot]:
			act.setCheckable(True)
		self.actionRe.setChecked(True)

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
	def __init__(self, **kwargs):
		super(SearchWidget, self).__init__(**kwargs)

		layout = QGridLayout()
		self.setLayout(layout)

		self.exprEdit = QLineEdit()
		self.exprEdit.returnPressed.connect(self.returnPressed)
		self.setFocusProxy(self.exprEdit)

		self.optionsButton = SearchOptionsButton()

		self.pluginChoice = QComboBox()
		plugins = sorted(file_search.enabledPlugins(), key=lambda p: p.name())
		for plugin in plugins:
			self.pluginChoice.addItem(plugin.name(), plugin.id)

		self.results = LocationList()
		self.results.setColumns(['path', 'line', 'snippet'])

		self.searcher = None

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
		return self.pluginChoice.itemData(self.pluginChoice.currentIndex())

	def regexp(self):
		re = QRegExp(self.exprEdit.text())
		re.setCaseSensitivity(csToQtEnum(self.optionsButton.caseSensitive()))
		re.setPatternSyntax(self.optionsButton.reFormat())
		return re

	def shouldFindRoot(self):
		return self.optionsButton.shouldFindRoot()

	def makeArgs(self, plugin):
		ed = buffers.currentBuffer()

		if self.shouldFindRoot():
			path = plugin.searchRootPath(ed.path)
		else:
			path = os.path.dirname(ed.path)
		pattern = self.exprEdit.text()
		ci = self.optionsButton.caseSensitive()
		return (path, pattern, ci)

	@Slot()
	def doSearch(self):
		self.results.clear()
		plugin_type = file_search.getPlugin(self.selectedPlugin())
		self.searcher = plugin_type()
		file_search.setupLocationList(self.searcher, self.results)
		args = self.makeArgs(self.searcher)
		self.searcher.search(*args)

	returnPressed = Signal()
