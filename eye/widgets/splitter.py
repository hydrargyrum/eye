# this project is licensed under the WTFPLv2, see COPYING.txt for details

"""Multi-splitter widget

The multi-splitter widget allows to have complex splitting layouts, with arbitrary levels of horizontal/vertical
splits. For example, it's possible to have editors layed out this way in a window::

	+--+----+----+
	|  |    |    |
	+--+----+    |
	|       |    |
	|       +----+
	|       |    |
	+-------+----+

Each split may contain a :any:`eye.widgets.tabs.TabWidget`, containing a single or multiple tabs.
"""

from PyQt5.QtCore import pyqtSignal, pyqtSlot, Qt, QPoint, QRect
from PyQt5.QtWidgets import QSplitter, QWidget, QStackedLayout
Signal = pyqtSignal
Slot = pyqtSlot

from .helpers import WidgetMixin

__all__ = ('SplitManager', 'Splitter', 'QSplitter')


class Splitter(QSplitter, WidgetMixin):
	"""Splitter widget for a single splitting level

	`Splitter` objects are handled by the :any:`SplitManager` widget.
	"""

	HandleBar = 42

	def __init__(self, **kwargs):
		super(Splitter, self).__init__(**kwargs)

		self.addCategory('splitter')

	def childAt(self, pos):
		"""Return child widget at position

		`pos` should be a `QPoint` relative to the top-left corner of this `Splitter` (which is at `(0, 0)`).
		The return value will be `HandleBar` if `pos` is right on a handle bar of this splitter.
		If the final widget under `pos` is contained in a sub-`Splitter` or sub-sub-`Splitter`, it won't be
		returned, only the direct child, the direct sub-`Splitter` will be returned.
		"""
		if pos.x() < 0 or pos.y() < 0 or pos.x() >= self.width() or pos.y() >= self.height():
			return None
		for i in range(self.count()):
			w = self.widget(i)
			if w.geometry().contains(pos):
				return w
		return self.HandleBar

	def parentManager(self):
		"""Returns the :any:`SplitManager` managing this splitter"""
		w = self.parent()
		while not isinstance(w, SplitManager):
			w = w.parent()
		return w


class SplitManager(QWidget, WidgetMixin):
	"""Split manager widget

	This widget allows to do multiple levels of splitter without having to manage the levels by hand.

	Instances of this class have the `"splitmanager"` category by default.
	"""

	North = 0
	South = 1
	West = 2
	East = 3

	SplitterClass = Splitter

	def __init__(self, **kwargs):
		super(SplitManager, self).__init__(**kwargs)

		self.root = self.SplitterClass(orientation=Qt.Horizontal)

		layout = QStackedLayout()
		self.setLayout(layout)
		layout.addWidget(self.root)

		self.addCategory('splitmanager')

	def splitAt(self, widgetLocation, orientation, newWidget):
		if widgetLocation:
			parent = widgetLocation.parent()
			pos = parent.indexOf(widgetLocation)
		else:
			parent = self.root
			pos = 0

		if parent.orientation() == orientation:
			parent.insertWidget(pos + 1, newWidget)
		else:
			newSplit = self.SplitterClass(orientation=orientation)
			parent.insertWidget(pos, newSplit)
			if widgetLocation:
				newSplit.addWidget(widgetLocation)
			newSplit.addWidget(newWidget)

	def removeWidget(self, widget):
		parent = widget.parent()
		widget.setParent(None)
		if not parent.count() and parent != self.root:
			self.removeWidget(parent)

	@Slot()
	def balanceSplitsRecursive(self, startAt=None):
		for w in self._iterRecursive(startAt):
			if isinstance(w, self.SplitterClass):
				self.balanceSplits(w)

	def balanceSplits(self, spl):
		spl.setSizes([1] * spl.count())  # qt redistributes space

	def allChildren(self):
		return [w for w in self._iterRecursive() if not isinstance(w, self.SplitterClass)]

	def _iterRecursive(self, startAt=None):
		if startAt is None:
			startAt = self.root

		splitters = [startAt]
		yield startAt
		while splitters:
			spl = splitters.pop()
			for i in range(spl.count()):
				w = spl.widget(i)
				if isinstance(w, self.SplitterClass):
					splitters.append(w)
				yield w


	def getRect(self, widget):
		return QRect(widget.mapTo(self, QPoint()), widget.size())

	def childId(self, widget):
		spl = widget
		while not isinstance(spl, self.SplitterClass):
			spl = spl.parent()
		return (spl, spl.indexOf(widget))

	def deepChildAt(self, pos):
		widget = self.root
		while isinstance(widget, QSplitter):
			widget = widget.childAt(widget.mapFrom(self, pos))
		return widget

	def requestClose(self):
		for c in self.allChildren():
			if not c.requestClose():
				return False
		return True
