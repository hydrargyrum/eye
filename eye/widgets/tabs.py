# this project is licensed under the WTFPLv2, see COPYING.txt for details

"""Tab widget
"""

from PyQt5.QtCore import pyqtSignal as Signal, Qt, QMimeData
from PyQt5.QtGui import QPolygon, QDrag, QIcon
from PyQt5.QtWidgets import QTabWidget, QTabBar, QStackedWidget, QToolButton, QMenu

from .. import consts
from ..three import str
from ..qt import Slot
from ..connector import CategoryMixin, disabled, registerSetup
from .droparea import DropAreaMixin, BandMixin
from .helpers import WidgetMixin
from ..helpers import buffers

__all__ = ('TabWidget', 'TabBar', 'SplitButton')


TAB_MIME = 'application/x.eye.tab'


def isTabDropEvent(ev):
	mdata = ev.mimeData()
	return mdata.hasFormat(TAB_MIME)


def takeWidget(widget):
	tw = widget.parentTabBar()
	tw.removeTab(tw.indexOf(widget))


def dropGetWidget(ev):
	tb = ev.source()
	tw = tb.parent()
	return tw.widget(tb.tabDrag)


class TabBar(QTabBar, BandMixin, CategoryMixin):
	def __init__(self, **kwargs):
		super(TabBar, self).__init__(**kwargs)
		self.setTabsClosable(True)
		#~ self.setMovable(True)
		self.setUsesScrollButtons(True)
		self.addCategory('tabbar')

	## drag and drop events
	def mousePressEvent(self, ev):
		super(TabBar, self).mousePressEvent(ev)
		self.tabDrag = self.tabAt(ev.pos())

	def mouseMoveEvent(self, ev):
		mdata = QMimeData()
		mdata.setData(TAB_MIME, b'x')
		drag = QDrag(self)
		drag.setMimeData(mdata)
		res = drag.exec_(Qt.CopyAction | Qt.MoveAction, Qt.MoveAction)

	def _showBand(self, ev):
		idx = self.tabAt(ev.pos())
		if idx >= 0:
			self.showBand(self.tabRect(idx))
		else:
			self.showBand(self.rect())

	def dragEnterEvent(self, ev):
		if not isTabDropEvent(ev):
			return super(TabBar, self).dragEnterEvent(ev)

		ev.acceptProposedAction()
		self._showBand(ev)

	def dragMoveEvent(self, ev):
		if not isTabDropEvent(ev):
			return super(TabBar, self).dragMoveEvent(ev)

		ev.acceptProposedAction()
		self._showBand(ev)

	def dragLeaveEvent(self, ev):
		self.hideBand()

	def dropEvent(self, ev):
		if not isTabDropEvent(ev):
			return super(TabBar, self).dropEvent(ev)

		self.hideBand()

		idx = self.tabAt(ev.pos())
		assert isinstance(self.parent(), TabWidget)
		widget = dropGetWidget(ev)

		if ev.proposedAction() == Qt.MoveAction:
			ev.acceptProposedAction()

			takeWidget(widget)
			self.parent().insertWidget(idx, widget)
			self.parent().setCurrentWidget(widget)
		elif ev.proposedAction() == Qt.CopyAction:
			ev.acceptProposedAction()
			new = buffers.newEditorShare(widget, parentTabBar=self.parent())
			# FIXME put at right place
			new.giveFocus()


class TabWidget(DropAreaMixin, QTabWidget, WidgetMixin, BandMixin):
	"""Tab widget class

	By default, instances of this class have the category `"tabwidget"` (see :doc:`eye.connector`).
	"""

	lastTabClosed = Signal()

	"""Signal lastTabClosed()

	This signal is emitted when the last tab of this tab widget has been closed.
	"""

	fileDropped = Signal(str)

	def __init__(self, **kwargs):
		super(TabWidget, self).__init__(**kwargs)

		self.hideBarIfSingleTab = False

		self.tabCloseRequested.connect(self._tabCloseRequested)
		self.currentChanged.connect(self._currentChanged)

		bar = TabBar()
		self.setTabBar(bar)

		self.addCategory('tabwidget')

	def currentBuffer(self):
		"""Return the widget from the current tab"""
		return self.currentWidget()

	def _idxContainerOf(self, widget):
		while widget is not self:
			idx = self.indexOf(widget)
			if idx >= 0:
				return idx
			widget = widget.parent()
		return -1

	## add/remove tabs
	def closeTab(self, ed):
		"""Close the tab containing the specified widget and return True if it can be

		The tab can't be closed if the widget has a `closeFile()` method which returns `True` when it is
		called. This method allows a tab content to reject closing if a file wasn't saved.
		"""
		assert self.isAncestorOf(ed)

		if hasattr(ed, 'closeFile'):
			if not ed.closeFile():
				return False

		idx = self._idxContainerOf(ed)

		self.removeTab(idx)
		return True

	def setCurrentWidget(self, widget):
		assert self.isAncestorOf(widget)
		idx = self._idxContainerOf(widget)
		if idx >= 0:
			self.setCurrentIndex(idx)

	def addWidget(self, widget):
		"""Add a new tab with the specified widget"""
		assert not self.isAncestorOf(widget)
		idx = self.addTab(widget, widget.windowIcon(), widget.windowTitle())
		widget.windowTitleChanged.connect(self._subTitleChanged)
		widget.windowIconChanged.connect(self._subIconChanged)
		self.setTabToolTip(idx, widget.toolTip())

	def insertWidget(self, idx, widget):
		assert not self.isAncestorOf(widget)
		self.insertTab(idx, widget, widget.windowIcon(), widget.windowTitle())
		widget.windowTitleChanged.connect(self._subTitleChanged)
		widget.windowIconChanged.connect(self._subIconChanged)
		self.setTabToolTip(idx, widget.toolTip())

	removeWidget = closeTab

	def _selectTab(self, step, s1, e1, rotate, s2, e2):
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
	## tab change
	def setCurrentWidget(self, widget):
		"""Select the tab containing the specified widget"""
		assert self.isAncestorOf(widget)
		idx = self._idxContainerOf(widget)
		if idx >= 0:
			self.setCurrentIndex(idx)

	@Slot()
	def selectPrevTab(self, rotate=False):
		"""Select previous tab

		If `rotate` is `True` and the current tab is the first tab, the last tab is selected.
		"""
		cur = self.currentIndex()
		self._selectTab(-1, cur - 1, -1, rotate, self.count() - 1, cur)

	@Slot()
	def selectPrevTabRotate(self):
		"""Select previous tab or last if current is the first tab"""
		self.selectPrevTab(True)

	@Slot()
	def selectNextTab(self, rotate=False):
		"""Select next tab

		If `rotate` is `True` and the current tab is the last tab, the first tab is selected.
		"""
		cur = self.currentIndex()
		self._selectTab(1, cur + 1, self.count(), rotate, 0, cur)

	@Slot()
	def selectNextTabRotate(self):
		"""Select next tab or first tab if current is the last tab"""
		self.selectNextTab(True)

	def _selectTab(self, step, s1, e1, rotate, s2, e2):
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

	## close management
	def closeEvent(self, ev):
		for _ in range(self.count()):
			w = self.widget(0)
			if w.close():
				self.removeTab(0)
			else:
				ev.ignore()
				return
		ev.accept()

	def canClose(self):
		return all(not w.isWindowModified() for w in self.widgets())

	## private
	@Slot(int)
	def _tabCloseRequested(self, idx):
		widget = self.widget(idx)
		if not widget.closeFile():
			return
		self.removeTab(idx)

	@Slot(int)
	def _currentChanged(self, idx):
		hadFocus = self.hasFocus()
		self.setFocusProxy(self.widget(idx))
		self.tabBar().setFocusProxy(self.widget(idx))
		if hadFocus:
			self.setFocus()

	@Slot(str)
	def _subTitleChanged(self, title):
		w = self.sender()
		idx = self.indexOf(w)
		if idx < 0:
			return
		self.setTabText(idx, title)
		self.setTabToolTip(idx, w.toolTip())

	@Slot(QIcon)
	def _subIconChanged(self, icon):
		w = self.sender()
		idx = self.indexOf(w)
		if idx < 0:
			return
		self.setTabIcon(idx, icon)

	## override
	def tabInserted(self, idx):
		super(TabWidget, self).tabInserted(idx)
		self._changeTabBarVisibility()

	def tabRemoved(self, idx):
		super(TabWidget, self).tabRemoved(idx)
		self._changeTabBarVisibility()

		w = self._findRemovedWidget()
		w.setParent(None)

		if self.count() == 0:
			self.lastTabClosed.emit()
		elif self.currentIndex() == idx:
			self.currentWidget().giveFocus()

	def _findRemovedWidget(self):
		# implementation detail, but no access to the removed widget
		base = self.findChild(QStackedWidget)
		for c in base.children():
			if not c.isWidgetType():
				continue
			if self.indexOf(c) < 0:
				return c

	def setHideBarIfSingleTab(self, b):
		self.hideBarIfSingleTab = b
		self._changeTabBarVisibility()

	def _changeTabBarVisibility(self):
		if self.hideBarIfSingleTab:
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
	def _showBand(self, pos):
		quad = widgetQuadrant(self.rect(), pos)
		r = widgetHalf(self.rect(), quad)
		self.showBand(r)

	def dragEnterEvent(self, ev):
		if isTabDropEvent(ev):
			self.tabBar().setVisible(True)
			ev.acceptProposedAction()
			self._showBand(ev.pos())
		else:
			super(TabWidget, self).dragEnterEvent(ev)

	def dragMoveEvent(self, ev):
		if isTabDropEvent(ev):
			ev.acceptProposedAction()
			self._showBand(ev.pos())
		else:
			super(TabWidget, self).dragMoveEvent(ev)

	def dragLeaveEvent(self, ev):
		super(TabWidget, self).dragLeaveEvent(ev)
		self.hideBand()
		self._changeTabBarVisibility()

	def dropEvent(self, ev):
		if isTabDropEvent(ev):
			self.hideBand()
			splitmanager = self.parent().parentManager()

			quad = widgetQuadrant(self.rect(), ev.pos())

			widget = dropGetWidget(ev)
			oldTw = widget.parentTabBar()

			if ev.proposedAction() == Qt.MoveAction:
				ev.acceptProposedAction()

				if oldTw.count() == 1:
					if oldTw is self:
						return
					splitmanager.splitAt(self, quad, oldTw)
				else:
					takeWidget(widget)
					tabs = TabWidget()
					tabs.addWidget(widget)
					splitmanager.splitAt(self, quad, tabs)
			elif ev.proposedAction() == Qt.CopyAction:
				ev.acceptProposedAction()

				new = buffers.newEditorShare(widget, parentTabBar=self)
				takeWidget(new)

				tabs = TabWidget()
				tabs.addWidget(new)
				splitmanager.splitAt(self, quad, tabs)

		else:
			super(TabWidget, self).dropEvent(ev)


class SplitButton(QToolButton, WidgetMixin):
	"""Button for splitting

	When clicked, the button shows a popup menu to choose between horizontal split and vertical split.
	The button is suitable for using as `cornerWidget` of :any:`TabWidget`.
	"""
	def __init__(self, **kwargs):
		super(SplitButton, self).__init__(**kwargs)

		self.setText(u'\u25ea')

		menu = QMenu()
		action = menu.addAction('Split horizontally')
		action.triggered.connect(self.splitHorizontal)
		action = menu.addAction('Split vertically')
		action.triggered.connect(self.splitVertical)
		self.setMenu(menu)
		self.setPopupMode(self.InstantPopup)

	@Slot()
	def splitHorizontal(self):
		assert isinstance(self.parent(), TabWidget)

		win = self.window()
		win.bufferSplitHorizontal(self.parent())

	@Slot()
	def splitVertical(self):
		assert isinstance(self.parent(), TabWidget)

		win = self.window()
		win.bufferSplitVertical(self.parent())


@registerSetup('tabwidget')
@disabled
def autoCreateCornerSplitter(tw):
	button = SplitButton()
	tw.setCornerWidget(button, Qt.TopRightCorner)
	button.show()


def widgetQuadrant(rect, point):
	center = rect.center()

	if QPolygon([rect.topLeft(), rect.topRight(), center]).containsPoint(point, 0):
		return consts.UP
	if QPolygon([rect.bottomLeft(), rect.bottomRight(), center]).containsPoint(point, 0):
		return consts.DOWN
	if QPolygon([rect.topLeft(), rect.bottomLeft(), center]).containsPoint(point, 0):
		return consts.LEFT
	if QPolygon([rect.bottomRight(), rect.topRight(), center]).containsPoint(point, 0):
		return consts.RIGHT


def widgetHalf(rect, quadrant):
	if quadrant in (consts.UP, consts.DOWN):
		rect.setHeight(rect.height() / 2)
		if quadrant == consts.DOWN:
			rect.translate(0, rect.height())
	elif quadrant in (consts.LEFT, consts.RIGHT):
		rect.setWidth(rect.width() / 2)
		if quadrant == consts.RIGHT:
			rect.translate(rect.width(), 0)
	return rect
