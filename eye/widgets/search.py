# this project is licensed under the WTFPLv2, see COPYING.txt for details

import logging
import os

from PyQt5.QtCore import QRegExp
from PyQt5.QtWidgets import QPushButton, QMenu, QWidget, QActionGroup, QGridLayout, QLineEdit, QComboBox, QToolButton

from eye.helpers import file_search, buffers
from eye.helpers.editor_search import SearchProps
from eye.qt import Signal, Slot
from eye.reutils import cs_to_qt_enum
from eye.widgets.helpers import WidgetMixin
from eye.widgets.locationlist import LocationList

__all__ = ('SearchWidget',)


LOGGER = logging.getLogger(__name__)


class SearchOptionsMenu(QMenu):
	def __init__(self, **kwargs):
		super().__init__(**kwargs)

		self.ci = self.addAction(self.tr('Case insensitive'))
		# TODO "smart case sensitive", i.e. CI if only lowercase chars
		self.addSeparator()

		self.formatGroup = QActionGroup(self)
		self.plain = self.addAction(self.tr('Plain text'))
		self.re = self.addAction(self.tr('Regular expression'))
		self.glob = self.addAction(self.tr('Glob pattern')) # TODO
		self.glob.setEnabled(False)
		self.formatGroup.addAction(self.plain)
		self.formatGroup.addAction(self.re)
		self.formatGroup.addAction(self.glob)

		for action in [self.ci, self.re, self.plain, self.glob]:
			action.setCheckable(True)
		self.plain.setChecked(True)

	def to_search_props(self, expr: str):
		ret = SearchProps(
			expr=expr,
			case_sensitive=not self.ci.isChecked(),
			is_re=self.re.isChecked()
		)
		return ret


class SearchOptionsButton(QPushButton):
	def __init__(self, **kwargs):
		super().__init__(**kwargs)

		self.setText(self.tr('Options'))

		# TODO factor with SearchOptionsMenu
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


# FIXME no wrap around
class SearchReplaceWidget(QWidget, WidgetMixin):
	def __init__(self, **kwargs):
		super().__init__(**kwargs)

		layout = QGridLayout()
		self.setLayout(layout)

		self.pattern_edit = QLineEdit()
		self.pattern_edit.returnPressed.connect(self._search)
		self.pattern_edit.textChanged.connect(self._update_enabling)
		self.pattern_options = SearchOptionsMenu()
		self.pattern_button = QToolButton(self)
		self.pattern_button.setText('Options')
		self.pattern_button.setPopupMode(QToolButton.InstantPopup)
		self.pattern_button.setMenu(self.pattern_options)

		self.replace_edit = QLineEdit()
		self.replace_edit.returnPressed.connect(self._replace)

		self.search_button = QPushButton(self.tr('&Search'))
		self.search_button.clicked.connect(self._search)
		self.replace_button = QPushButton(self.tr('&Replace'))
		self.replace_button.clicked.connect(self._replace)
		self.replace_all_button = QPushButton(self.tr('Replace &all'))
		self.replace_all_button.clicked.connect(self._replace_all)

		layout.addWidget(self.pattern_edit, 0, 0)
		layout.addWidget(self.pattern_button, 0, 1)
		layout.addWidget(self.search_button, 0, 2)
		layout.addWidget(self.replace_edit, 1, 0)
		layout.addWidget(self.replace_button, 1, 1)
		layout.addWidget(self.replace_all_button, 1, 2)

		self._update_enabling()

		self.setWindowTitle(self.tr('Search/Replace'))
		self.add_category('search_replace_widget')

	@Slot()
	def _update_enabling(self):
		has_pattern = bool(self.pattern_edit.text())
		self.search_button.setEnabled(has_pattern)
		self.replace_button.setEnabled(has_pattern)

	@Slot(str)
	def set_pattern(self, text):
		self.pattern_edit.setText(text)
		self.pattern_edit.selectAll()

	@Slot()
	def _search(self):
		pattern = self.pattern_edit.text()
		if not pattern:
			return

		editor = self.window().current_buffer()
		props = self.pattern_options.to_search_props(expr=pattern)

		from eye.helpers import editor_search
		editor_search.perform_search_seek(editor, props)

	@Slot()
	def _replace(self):
		editor = self.window().current_buffer()
		if not hasattr(editor, 'search_obj'):
			LOGGER.info('no editor_search has been performed on %r', editor)
			return

		props = self.pattern_options.to_search_props(expr=None)

		editor.search_obj.replace_selection(self.replace_edit.text(), is_re=props.is_re)
		self._search()

	@Slot()
	def _replace_all(self):
		editor = self.window().current_buffer()
		if not hasattr(editor, 'search_obj'):
			LOGGER.info('no editor_search has been performed on %r', editor)
			return

		props = self.pattern_options.to_search_props(expr=None)

		editor.search_obj.replace_all(self.replace_edit.text(), is_re=props.is_re)
