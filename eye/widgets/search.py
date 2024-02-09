# this project is licensed under the WTFPLv2, see COPYING.txt for details

import os

from PyQt5.QtCore import QRegExp
from PyQt5.QtWidgets import QPushButton, QMenu, QWidget, QActionGroup, QGridLayout, QLineEdit, QComboBox

from eye.helpers import file_search, buffers
from eye.qt import Signal, Slot
from eye.reutils import cs_to_qt_enum
from eye.widgets.helpers import WidgetMixin
from eye.widgets.locationlist import LocationList

__all__ = ('SearchWidget',)


class SearchOptionsButton(QPushButton):
	def __init__(self, **kwargs):
		super().__init__(**kwargs)

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

	def should_find_root(self):
		return self.actionRoot.isChecked()

	def case_sensitive(self):
		return not self.actionCi.isChecked()

	def re_format(self):
		if self.actionPlain.isChecked():
			return QRegExp.FixedString
		elif self.actionRe.isChecked():
			return QRegExp.RegExp
		elif self.actionGlob.isChecked():
			return QRegExp.WildcardUnix


class SearchWidget(QWidget, WidgetMixin):
	def __init__(self, **kwargs):
		super().__init__(**kwargs)

		layout = QGridLayout()
		self.setLayout(layout)

		self.expr_edit = QLineEdit()
		self.expr_edit.returnPressed.connect(self.returnPressed)
		self.setFocusProxy(self.expr_edit)

		self.options_button = SearchOptionsButton()

		self.plugin_choice = QComboBox()
		plugins = sorted(file_search.enabled_plugins(), key=lambda p: p.name())
		for plugin in plugins:
			self.plugin_choice.addItem(plugin.name(), plugin.id)

		self.results = LocationList()
		self.results.set_columns(['path', 'line', 'snippet'])

		self.searcher = None

		layout.addWidget(self.expr_edit, 0, 0)
		layout.addWidget(self.options_button, 0, 1)
		layout.addWidget(self.plugin_choice, 0, 2)
		layout.addWidget(self.results, 1, 0, 1, -1)

		self.add_category('file_search_widget')

	def setPlugin(self, id):
		index = self.plugin_choice.findData(id)
		if index >= 0:
			self.plugin_choice.setCurrentIndex(index)

	def setText(self, text):
		self.expr_edit.setText(text)

	def selected_plugin(self):
		return self.plugin_choice.itemData(self.plugin_choice.currentIndex())

	def regexp(self):
		re = QRegExp(self.expr_edit.text())
		re.setCaseSensitivity(cs_to_qt_enum(self.options_button.case_sensitive()))
		re.setPatternSyntax(self.options_button.re_format())
		return re

	def should_find_root(self):
		return self.options_button.should_find_root()

	def make_args(self, plugin):
		ed = buffers.current_buffer()

		if self.should_find_root():
			path = plugin.search_root_path(ed.path)
		else:
			path = os.path.dirname(ed.path)
		pattern = self.expr_edit.text()
		ci = self.options_button.case_sensitive()
		return (path, pattern, ci)

	@Slot()
	def do_search(self):
		self.results.clear()
		plugin_type = file_search.get_plugin(self.selected_plugin())
		self.searcher = plugin_type()
		file_search.setup_location_list(self.searcher, self.results)
		args = self.make_args(self.searcher)
		self.searcher.search(*args)

	returnPressed = Signal()
