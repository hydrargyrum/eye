# this project is licensed under the WTFPLv2, see COPYING.txt for details

"""Tab widget
"""

from PyQt5.QtCore import Qt, QMimeData
from PyQt5.QtGui import QPolygon, QDrag, QIcon
from PyQt5.QtWidgets import QTabWidget, QTabBar, QStackedWidget, QToolButton, QMenu

from eye import consts
from eye.connector import CategoryMixin, disabled, register_setup
from eye.helpers import buffers
from eye.qt import Signal, Slot, override
from eye.widgets.droparea import DropAreaMixin, BandMixin
from eye.widgets.helpers import WidgetMixin, parent_tab_widget

__all__ = (
	'TabWidget', 'TabBar', 'SplitButton',
	'auto_create_corner_splitter',
)


TAB_MIME = 'application/x.eye.tab'


def is_tab_drop_event(ev):
	mdata = ev.mimeData()
	return mdata.hasFormat(TAB_MIME)


def take_widget(widget):
	tw = parent_tab_widget(widget)
	tw.removeTab(tw.indexOf(widget))


def drop_get_widget(ev):
	tb = ev.source()
	tw = tb.parent()
	return tw.widget(tb.tab_drag)


class TabBar(QTabBar, BandMixin, CategoryMixin):
	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		self.setTabsClosable(True)
		#~ self.setMovable(True)
		self.setUsesScrollButtons(True)

		self.tab_drag = None

		self.add_category('tabbar')

	## drag and drop events
	@override
	def mousePressEvent(self, ev):
		super().mousePressEvent(ev)
		self.tab_drag = self.tabAt(ev.pos())

	@override
	def mouseMoveEvent(self, ev):
		mdata = QMimeData()
		mdata.setData(TAB_MIME, b'x')
		drag = QDrag(self)
		drag.setMimeData(mdata)
		drag.exec_(Qt.CopyAction | Qt.MoveAction, Qt.MoveAction)

	def _show_band(self, ev):
		idx = self.tabAt(ev.pos())
		if idx >= 0:
			self.showBand(self.tabRect(idx))
		else:
			self.showBand(self.rect())

	@override
	def dragEnterEvent(self, ev):
		if not is_tab_drop_event(ev):
			return super().dragEnterEvent(ev)

		ev.acceptProposedAction()
		self._show_band(ev)

	@override
	def dragMoveEvent(self, ev):
		if not is_tab_drop_event(ev):
			return super().dragMoveEvent(ev)

		ev.acceptProposedAction()
		self._show_band(ev)

	@override
	def dragLeaveEvent(self, ev):
		self.hide_band()

	@override
	def dropEvent(self, ev):
		if not is_tab_drop_event(ev):
			return super().dropEvent(ev)

		self.hide_band()

		idx = self.tabAt(ev.pos())
		assert isinstance(self.parent(), TabWidget)
		widget = drop_get_widget(ev)

		if ev.proposedAction() == Qt.MoveAction:
			ev.acceptProposedAction()

			take_widget(widget)
			self.parent().insert_widget(idx, widget)
			self.parent().setCurrentWidget(widget)
		elif ev.proposedAction() == Qt.CopyAction:
			ev.acceptProposedAction()
			new = buffers.new_editor_share(widget, parent_tab_bar=self.parent())
			# FIXME put at right place
			new.give_focus()


class TabWidget(DropAreaMixin, QTabWidget, WidgetMixin, BandMixin):
	"""Tab widget class

	By default, instances of this class have the category `"tabwidget"` (see :doc:`eye.connector`).
	"""

	last_tab_closed = Signal()

	"""Signal last_tab_closed()

	This signal is emitted when the last tab of this tab widget has been closed.
	"""

	file_dropped = Signal(str)

	def __init__(self, **kwargs):
		super().__init__(**kwargs)

		self.hide_bar_if_single_tab = False

		self.tabCloseRequested.connect(self._tab_close_requested)
		self.currentChanged.connect(self._current_changed)

		bar = TabBar()
		self.setTabBar(bar)

		self.add_category('tabwidget')

	def current_buffer(self):
		"""Return the widget from the current tab"""
		return self.currentWidget()

	def _idx_container_of(self, widget):
		while widget is not self:
			idx = self.indexOf(widget)
			if idx >= 0:
				return idx
			widget = widget.parent()
		return -1

	## add/remove tabs
	def close_tab(self, ed):
		"""Close the tab containing the specified widget and return True if it can be

		The tab can't be closed if the widget has a `close_file()` method which returns `True` when it is
		called. This method allows a tab content to reject closing if a file wasn't saved.
		"""
		assert self.isAncestorOf(ed)

		if hasattr(ed, 'close_file'):
			if not ed.close_file():
				return False

		idx = self._idx_container_of(ed)

		self.removeTab(idx)
		return True

	def add_widget(self, widget):
		"""Add a new tab with the specified widget"""
		assert not self.isAncestorOf(widget)
		idx = self.addTab(widget, widget.windowIcon(), widget.windowTitle())
		widget.windowTitleChanged.connect(self._sub_title_changed)
		widget.windowIconChanged.connect(self._sub_icon_changed)
		self.setTabToolTip(idx, widget.toolTip())

	def insert_widget(self, idx, widget):
		assert not self.isAncestorOf(widget)
		self.insertTab(idx, widget, widget.windowIcon(), widget.windowTitle())
		widget.windowTitleChanged.connect(self._sub_title_changed)
		widget.windowIconChanged.connect(self._sub_icon_changed)
		self.setTabToolTip(idx, widget.toolTip())

	remove_widget = close_tab

	## tab change
	@override
	def setCurrentWidget(self, widget):
		"""Select the tab containing the specified widget"""
		assert self.isAncestorOf(widget)
		idx = self._idx_container_of(widget)
		if idx >= 0:
			self.setCurrentIndex(idx)

	@Slot()
	def select_prev_tab(self, rotate=False):
		"""Select previous tab.

		:param rotate: if `True` and the current tab is the first tab, the last tab is selected.
		:type rotate: bool
		"""
		cur = self.currentIndex()
		self._select_tab(-1, cur - 1, -1, rotate, self.count() - 1, cur)

	@Slot()
	def select_prev_tab_rotate(self):
		"""Select previous tab or last if current is the first tab"""
		self.select_prev_tab(True)

	@Slot()
	def select_next_tab(self, rotate=False):
		"""Select next tab

		:param rotate: if `True` and the current tab is the last tab, the first tab is selected.
		:type rotate: bool
		"""
		cur = self.currentIndex()
		self._select_tab(1, cur + 1, self.count(), rotate, 0, cur)

	@Slot()
	def select_next_tab_rotate(self):
		"""Select next tab or first tab if current is the last tab"""
		self.select_next_tab(True)

	def _select_tab(self, step, s1, e1, rotate, s2, e2):
		for idx in range(s1, e1, step):
			if self.isTabEnabled(idx):
				self.setCurrentIndex(idx)
				return
		if not rotate:
			return
		for idx in range(s2, e2, step):
			if self.isTabEnabled(idx):
				self.setCurrentIndex(idx)
				return

	@Slot()
	def swap_next_tab(self):
		idx = self.currentIndex()
		if idx + 1 < self.count():
			self.tabBar().moveTab(idx, idx + 1)

	@Slot()
	def swap_prev_tab(self):
		idx = self.currentIndex()
		if idx >= 1:
			self.tabBar().moveTab(idx, idx - 1)

	## close management
	@override
	def closeEvent(self, ev):
		for _ in range(self.count()):
			w = self.widget(0)
			if w.close():
				self.removeTab(0)
			else:
				ev.ignore()
				return
		ev.accept()

	def can_close(self):
		"""Returns True if all sub-widgets can be closed"""
		return all(not w.isWindowModified() for w in self.widgets())

	## private
	@Slot(int)
	def _tab_close_requested(self, idx):
		widget = self.widget(idx)
		if not widget.close_file():
			return
		self.removeTab(idx)

	@Slot(int)
	def _current_changed(self, idx):
		hadFocus = self.hasFocus()
		self.setFocusProxy(self.widget(idx))
		self.tabBar().setFocusProxy(self.widget(idx))
		if hadFocus:
			self.setFocus()

	@Slot(str)
	def _sub_title_changed(self, title):
		w = self.sender()
		idx = self.indexOf(w)
		if idx < 0:
			return
		self.setTabText(idx, title)
		self.setTabToolTip(idx, w.toolTip())

	@Slot(QIcon)
	def _sub_icon_changed(self, icon):
		w = self.sender()
		idx = self.indexOf(w)
		if idx < 0:
			return
		self.setTabIcon(idx, icon)

	## override
	@override
	def tabInserted(self, idx):
		super().tabInserted(idx)
		self._change_tab_bar_visibility()

	@override
	def tabRemoved(self, idx):
		super().tabRemoved(idx)
		self._change_tab_bar_visibility()

		w = self._find_removed_widget()
		w.setParent(None)

		if self.count() == 0:
			self.last_tab_closed.emit()
		elif self.currentIndex() == idx:
			self.currentWidget().give_focus()

	def _find_removed_widget(self):
		# implementation detail, but no access to the removed widget
		base = self.findChild(QStackedWidget)
		for c in base.children():
			if not c.isWidgetType():
				continue
			if self.indexOf(c) < 0:
				return c

	def set_hide_bar_if_single_tab(self, b):
		"""Set whether the tab bar should be hidden if there's only one tab.
		"""
		self.hide_bar_if_single_tab = b
		self._change_tab_bar_visibility()

	def _change_tab_bar_visibility(self):
		if self.hide_bar_if_single_tab:
			visible = (self.count() > 1)
		else:
			visible = True
		self.tabBar().setVisible(visible)

	## misc
	@Slot()
	def refocus(self):
		"""Give focus to the widget inside the current tab"""
		self.currentWidget().setFocus(Qt.OtherFocusReason)

	def widgets(self):
		"""Return widgets contained in tabs"""
		return [self.widget(i) for i in range(self.count())]

	## drag and drop events
	def _show_band(self, pos):
		quad = widget_quadrant(self.rect(), pos)
		r = widget_half(self.rect(), quad)
		self.show_band(r)

	@override
	def dragEnterEvent(self, ev):
		if is_tab_drop_event(ev):
			self.tabBar().setVisible(True)
			ev.acceptProposedAction()
			self._show_band(ev.pos())
		else:
			super().dragEnterEvent(ev)

	@override
	def dragMoveEvent(self, ev):
		if is_tab_drop_event(ev):
			ev.acceptProposedAction()
			self._show_band(ev.pos())
		else:
			super().dragMoveEvent(ev)

	@override
	def dragLeaveEvent(self, ev):
		super().dragLeaveEvent(ev)
		self.hide_band()
		self._change_tab_bar_visibility()

	@override
	def dropEvent(self, ev):
		if is_tab_drop_event(ev):
			self.hide_band()
			splitmanager = self.parent().parentManager()

			quad = widget_quadrant(self.rect(), ev.pos())

			widget = drop_get_widget(ev)
			old_tw = parent_tab_widget(widget)

			if ev.proposedAction() == Qt.MoveAction:
				ev.acceptProposedAction()

				if old_tw.count() == 1:
					if old_tw is self:
						return
					splitmanager.split_at(self, quad, old_tw)
				else:
					take_widget(widget)
					tabs = TabWidget()
					tabs.add_widget(widget)
					splitmanager.split_at(self, quad, tabs)
			elif ev.proposedAction() == Qt.CopyAction:
				ev.acceptProposedAction()

				new = buffers.new_editor_share(widget, parent_tab_bar=self)
				take_widget(new)

				tabs = TabWidget()
				tabs.add_widget(new)
				splitmanager.split_at(self, quad, tabs)

		else:
			super().dropEvent(ev)


class SplitButton(QToolButton, WidgetMixin):
	"""Button for splitting

	When clicked, the button shows a popup menu to choose between horizontal split and vertical split.
	The button is suitable for using as `cornerWidget` of :any:`TabWidget`.
	"""
	def __init__(self, **kwargs):
		super().__init__(**kwargs)

		self.setText('\u25ea')

		menu = QMenu()
		action = menu.addAction('Split &horizontally ―')
		action.triggered.connect(self.split_horizontal)
		action = menu.addAction('Split &vertically |')
		action.triggered.connect(self.split_vertical)
		self.setMenu(menu)
		self.setPopupMode(self.InstantPopup)

	@Slot()
	def split_horizontal(self):
		assert isinstance(self.parent(), TabWidget)

		win = self.window()
		win.buffer_split_horizontal(self.parent())

	@Slot()
	def split_vertical(self):
		assert isinstance(self.parent(), TabWidget)

		win = self.window()
		win.buffer_split_vertical(self.parent())


@register_setup('tabwidget')
@disabled
def auto_create_corner_splitter(tw):
	"""When enabled, will create a corner popup button for splitting.

	.. seealso:: :any:`eye.widgets.splitter`
	"""
	button = SplitButton()
	tw.setCornerWidget(button, Qt.TopRightCorner)
	button.show()


def widget_quadrant(rect, point):
	center = rect.center()

	if QPolygon([rect.topLeft(), rect.topRight(), center]).containsPoint(point, 0):
		return consts.UP
	if QPolygon([rect.bottomLeft(), rect.bottomRight(), center]).containsPoint(point, 0):
		return consts.DOWN
	if QPolygon([rect.topLeft(), rect.bottomLeft(), center]).containsPoint(point, 0):
		return consts.LEFT
	if QPolygon([rect.bottomRight(), rect.topRight(), center]).containsPoint(point, 0):
		return consts.RIGHT


def widget_half(rect, quadrant):
	if quadrant in (consts.UP, consts.DOWN):
		rect.setHeight(rect.height() / 2)
		if quadrant == consts.DOWN:
			rect.translate(0, rect.height())
	elif quadrant in (consts.LEFT, consts.RIGHT):
		rect.setWidth(rect.width() / 2)
		if quadrant == consts.RIGHT:
			rect.translate(rect.width(), 0)
	return rect
