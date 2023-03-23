# this project is licensed under the WTFPLv2, see COPYING.txt for details

import os
from weakref import ref

from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QMainWindow, QFileDialog, QDockWidget, QWidget

from eye import consts
from eye.connector import register_signal, disabled
from eye.qt import Signal, Slot, override
from eye.widgets.droparea import DropAreaMixin
from eye.widgets.editor import Editor
from eye.widgets.helpers import CategoryMixin, accept_if, parent_tab_widget
from eye.widgets.splitter import SplitManager
from eye.widgets.tabs import TabWidget
from eye.widgets.menus import create_menu

__all__ = ('Window', 'title_on_focus')


class DockWidget(QDockWidget, CategoryMixin):
	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		self.add_category('dock_container')

	@override
	def childEvent(self, ev):
		super().childEvent(ev)

		# cannot catch setWidget() call
		w = self.widget()
		if ev.type() == QEvent.ChildAdded and w:
			try:
				w.windowTitleChanged.connect(self.child_title_changed, Qt.UniqueConnection)
			except TypeError:  # already connected
				pass
			else:
				self.setWindowTitle(w.windowTitle())

	@Slot(str)
	def child_title_changed(self, title):
		if self.sender() is self.widget():
			self.setWindowTitle(title)


class Window(QMainWindow, CategoryMixin, DropAreaMixin):
	"""Main window type.

	This window type should typically be used for editing windows.

	A Window contains a central widget (which is a :any:`SplitManager`), a menu bar, a status bar, toolbars, and
	dock widgets. Dock widgets are widgets which can be placed on the 4 sides of the central widget.

	Access to menu bar, status bar and toolbars is the same as with a :any:`QMainWindow`. Dock widgets access can
	be done with the :any:`add_dockable` helper.
	"""

	EditorClass = Editor

	"""Class of the widget to create when a new tab is opened."""

	file_dropped = Signal(str)

	focused_buffer = Signal(QWidget)

	def __init__(self, *args):
		super().__init__(*args)

		self.menubar = self.menuBar()

		self.splitter = SplitManager()

		ed = self.EditorClass()
		tabs = TabWidget()
		tabs.add_widget(ed)

		self.splitter.split_at(None, consts.RIGHT, tabs)

		self.setCentralWidget(self.splitter)

		self.last_focus = ref(ed)
		from eye.app import qApp
		qApp().focusChanged.connect(self._app_focus_changed)

		REGISTRY.append(self)
		self.add_category('window')

	def create_default_menu_bar(self):
		menu = create_menu(self.menubar, ['&File'])
		action = menu.addAction(QIcon.fromTheme('document-new'), 'New')
		action.triggered.connect(self.buffer_new)

		action = menu.addAction(QIcon.fromTheme('document-open'), 'Open...')
		action.triggered.connect(self.buffer_open_dialog)

		action = menu.addAction(QIcon.fromTheme('document-save'), 'Save')
		action.triggered.connect(self.buffer_save)

		action = menu.addAction(QIcon.fromTheme('application-exit'), 'Quit')
		action.triggered.connect(self.quit_requested)

	@Slot()
	def toggle_full_screen(self):
		self.setWindowState(self.windowState() ^ Qt.WindowFullScreen)

	def add_dockable(self, area, widget, title=''):
		"""Add a widget to a dock of this window

		:param area: the area where to dock the widget
		:type area: Qt.DockWidgetArea
		:param widget: the widget to add
		:param title: the (optional) title of the widget in the dock
		:returns: the DockWidget wrapping `widget`
		:rtype: QDockWidget
		"""
		dw = DockWidget()
		if title:
			dw.setWindowTitle(title)
		dw.setWidget(widget)
		self.addDockWidget(area, dw)
		return dw

	## buffers
	def current_buffer(self):
		"""Return the current buffer in this window, which has had focus last."""
		return self.last_focus()

	@Slot()
	def buffer_new(self):
		"""Open a new, empty editor in current tab container."""
		ed = self.EditorClass()
		cur = self.current_buffer()
		if cur:
			parent = parent_tab_widget(cur)
			parent.add_widget(ed)
			ed.give_focus()
		return ed

	@Slot()
	def buffer_new_at_tabs(self, tabbar):
		"""Open a new, empty editor in specified tab container."""
		ed = self.EditorClass()
		tabbar.add_widget(ed)
		return ed

	@Slot()
	def buffer_open_dialog(self):
		path, _ = QFileDialog.getOpenFileName(self, self.tr('Open file'), os.path.expanduser('~'))
		if path:
			ed = self.buffer_new()
			ed.open_file(path)

	@Slot()
	def buffer_open(self, path):
		"""Open a new buffer in current tab container and load specified path."""
		ed = self.buffer_new()
		if ed.open_file(path):
			return ed
		else:
			parent_tab_widget(ed).close_tab(ed)

	@Slot()
	def buffer_close(self):
		"""Close current buffer."""
		ed = self.current_buffer()
		parent = parent_tab_widget(ed)
		parent.close_tab(ed)

	@Slot()
	def buffer_save(self):
		"""Save current buffer."""
		self.current_buffer().save_file()

	def _buffer_new_split(self, orientation, widget=None):
		if widget is None:
			widget = self.current_buffer()
		parent = parent_tab_widget(widget)

		ed = self.EditorClass()
		tabs = TabWidget()
		tabs.add_widget(ed)

		DIRS = {
			Qt.Vertical: consts.DOWN,
			Qt.Horizontal: consts.RIGHT
		}
		self.splitter.split_at(parent, DIRS[orientation], tabs)

	@Slot()
	def buffer_split_horizontal(self, widget=None):
		"""Split window horizontally at current buffer.

		A new empty editor is created.
		"""
		self._buffer_new_split(Qt.Horizontal, widget)

	@Slot()
	def buffer_split_vertical(self, widget=None):
		"""Split window vertically at current buffer.

		A new empty editor is created.
		"""
		self._buffer_new_split(Qt.Vertical, widget)

	## signals
	quit_requested = Signal()

	"""Signal quitRequested()"""

	closing = Signal()

	## events
	@override
	def closeEvent(self, ev):
		if accept_if(ev, self.splitter.close()):
			super().closeEvent(ev)
			self.closing.emit()
			REGISTRY.remove(self)

	def can_close(self):
		return self.splitter.can_close()

	def on_tabbar_last_closed(self, tw):
		self.splitter.remove_widget(tw)

	@Slot('QWidget*', 'QWidget*')
	def _app_focus_changed(self, _, new):
		if self.centralWidget().isAncestorOf(new):
			self.last_focus = ref(new)
			self.focused_buffer.emit(new)


@register_signal('tabwidget', 'last_tab_closed')
def on_last_tab_closed(tw):
	win = tw.window()
	win.on_tabbar_last_closed(tw)


@register_signal('window', 'focused_buffer')
@disabled
def title_on_focus(window, buffer):
	"""Handler to let the window title reflect the focused buffer title"""
	window.setWindowTitle(buffer.windowTitle())


REGISTRY = []
