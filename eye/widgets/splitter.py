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

import logging

from PyQt5.QtCore import Qt, QPoint, QRect, QTimer
from PyQt5.QtWidgets import QSplitter, QWidget, QStackedLayout

from .. import consts
from .helpers import WidgetMixin
from ..qt import Slot

__all__ = ('SplitManager', 'Splitter', 'QSplitter')


LOGGER = logging.getLogger(__name__)


class Splitter(QSplitter, WidgetMixin):
	"""Splitter widget for a single splitting level

	`Splitter` objects are handled by the :any:`SplitManager` widget.
	"""

	def __init__(self, **kwargs):
		super(Splitter, self).__init__(**kwargs)

		self.addCategory('splitter')

	def children(self):
		for i in range(self.count()):
			yield self.widget(i)

	def childAt(self, pos):
		"""Return direct child widget at the given position

		The returned child will be a direct child of `self`. If the real widget at `pos` is in a
		sub-Splitter, only the sub-Splitter which is a direct child of `self` will be returned.

		:type pos: QPoint
		:param pos: relative to the top-left corner of this `Splitter` (which is at `(0, 0)`).
		:return: the direct child at `pos`, a :any:`QSplitterHandle` if `pos` is on a handle, or None if
		         `pos` is outside `self`'s geometry
		:rtype: QWidget
		"""
		if not self.rect().contains(pos):
			return None
		for i in range(self.count()):
			for w in (self.widget(i), self.handle(i)):
				if w.geometry().contains(pos):
					return w

	def parentManager(self):
		"""Returns the :any:`SplitManager` managing this splitter

		:rtype: SplitManager
		"""
		w = self.parent()
		while not isinstance(w, SplitManager):
			w = w.parent()
		return w

	def widgets(self):
		"""Return all direct children widgets

		Children returned by this method may be `Splitter` widgets if there are sub-splitters.
		:rtype: list
		"""
		return [self.widget(i) for i in range(self.count())]

	def removeChild(self, widget):
		assert self.isAncestorOf(widget)
		assert self is not widget

		widget.setParent(None)

	def replaceChild(self, child, new):
		assert child is not new
		assert self is not child
		assert self is not new
		assert self.isAncestorOf(child)

		idx = self.indexOf(child)
		child.setParent(None)
		self.insertWidget(idx, new)


class SplitManager(QWidget, WidgetMixin):
	"""Split manager widget

	This widget allows to do multiple levels of splitter without having to manage the levels by hand.

	Instances of this class have the `"splitmanager"` category by default.
	"""

	SplitterClass = Splitter

	def __init__(self, **kwargs):
		super(SplitManager, self).__init__(**kwargs)

		self.root = self.SplitterClass(orientation=Qt.Horizontal)

		layout = QStackedLayout()
		self.setLayout(layout)
		layout.addWidget(self.root)

		self.optimizeTimer = QTimer()
		self.optimizeTimer.setInterval(0)
		self.optimizeTimer.setSingleShot(True)
		self.optimizeTimer.timeout.connect(self._optimize)

		self.addCategory('splitmanager')

	# TODO check if it can be integrated synchronously in calls
	@Slot()
	def _optimize(self):
		splitters = [self.root]
		i = 0
		while i < len(splitters):
			spl = splitters[i]
			splitters.extend(c for c in spl.children() if isinstance(c, QSplitter))
			i += 1
		splitters.pop(0)
		splitters.reverse()

		for spl in splitters:
			parent = spl.parent()
			if parent is None:
				continue

			if spl.count() == 0:
				LOGGER.debug('optimizer remove empty %s', spl)
				parent.removeChild(spl)
			elif spl.count() == 1:
				child = next(iter(spl.children()))
				LOGGER.debug('replace %s by only child %s', spl, child)
				parent.replaceChild(spl, child)

	## split/move/delete
	def splitAt(self, currentWidget, direction, newWidget):
		if currentWidget is None:
			parent = self.root
			idx = 0
		else:
			assert self.isAncestorOf(currentWidget)
			parent = currentWidget.parent()
			idx = parent.indexOf(currentWidget)

		orientation = consts.ORIENTATIONS[direction]
		if parent.orientation() == orientation:
			oldsize = parent.sizes()
			if oldsize:
				oldsize[idx] //= 2
				oldsize.insert(idx, oldsize[idx])

			if direction in (consts.DOWN, consts.RIGHT):
				idx += 1

			LOGGER.debug('inserting %r at %r in %r in the same orientation', newWidget, idx, parent)
			parent.insertWidget(idx, newWidget)

			if oldsize:
				parent.setSizes(oldsize)
		else:
			# currentWidget is moved, so it may lose focus
			refocus = currentWidget and currentWidget.hasFocus()

			newSplit = self.SplitterClass(orientation=orientation)

			LOGGER.debug('inserting %r in new splitter %r at %r of %r in different orientation', newWidget, newSplit, idx, parent)

			if currentWidget:
				# save/restore size because Qt goes crazy when moving splitter widgets around
				oldsize = parent.sizes()
				if direction in (consts.DOWN, consts.RIGHT):
					newSplit.addWidget(currentWidget)
					parent.insertWidget(idx, newSplit)
					newSplit.addWidget(newWidget)
				else:
					newSplit.addWidget(newWidget)
					parent.insertWidget(idx, newSplit)
					newSplit.addWidget(currentWidget)
				parent.setSizes(oldsize)
				newSplit.setSizes([1, 1]) # force Qt to rebalance it
			else:
				newSplit.addWidget(newWidget)
				parent.insertWidget(idx, newSplit)

			if refocus:
				currentWidget.setFocus()

	def moveWidget(self, currentWidget, direction, newWidget):
		if currentWidget is newWidget:
			LOGGER.info('will not move %r over itself', currentWidget)
			return

		self.removeWidget(newWidget)
		self.splitAt(currentWidget, direction, newWidget)
		self.optimizeTimer.start()

	def removeWidget(self, widget):
		if not self.isAncestorOf(widget):
			LOGGER.info("cannot remove widget %r since it doesn't belong to %r", widget, self)
			return

		spl, _ = self.childId(widget)
		spl.removeChild(widget)
		self.optimizeTimer.start()

	## balance
	@Slot()
	def balanceSplitsRecursive(self, startAt=None):
		for w in self._iterRecursive(startAt):
			if isinstance(w, self.SplitterClass):
				self.balanceSplits(w)

	def balanceSplits(self, spl):
		spl.setSizes([1] * spl.count())  # qt redistributes space

	## neighbours
	def _neighbour_up(self, widget, direction):
		if widget is None or widget is self.root:
			return None

		spl, idx = self.childId(widget)

		orientation = consts.ORIENTATIONS[direction]
		new_idx = idx + consts.MOVES[direction]
		if spl.orientation() != orientation or not (0 <= new_idx < spl.count()):
			return self._neighbour_up(spl, direction)
		return spl.widget(new_idx)

	def _neighbour_down(self, spl, direction, pos):
		orientation = consts.ORIENTATIONS[direction]
		if spl.orientation() == orientation:
			if direction in (consts.DOWN, consts.RIGHT):
				child = spl.widget(0)
			else:
				child = spl.widget(spl.count() - 1)
		else:
			for child in spl.children():
				if spl.orientation() == Qt.Vertical:
					end = QPoint(0, child.height())
					if child.mapTo(self, end).y() >= pos.y():
						break
				else:
					end = QPoint(child.width(), 0)
					if child.mapTo(self, end).x() >= pos.x():
						break
			else:
				return

		if isinstance(child, QSplitter):
			return self._neighbour_down(child, direction, pos)
		else:
			return child

	def neighbour(self, widget, direction):
		res = self._neighbour_up(widget, direction)
		LOGGER.debug('neighbour_up %r of %r: %r', direction, widget, res)
		if not isinstance(res, QSplitter):
			return res

		wcenter = widget.rect().center()
		pos = widget.mapTo(self, wcenter)
		res = self._neighbour_down(res, direction, pos)
		LOGGER.debug('neighbour_down %r of %r: %r', direction, widget, res)
		return res

	## getters
	def allChildren(self):
		"""Get all non-splitter children widgets

		:return: the direct children of `Splitter`s that are not `Splitter`s themselves
		:rtype: list
		"""
		return [w for w in self._iterRecursive() if not isinstance(w, self.SplitterClass)]

	def childRect(self, widget):
		return QRect(widget.mapTo(self, QPoint()), widget.size())

	def childId(self, widget):
		spl = widget.parent()
		while not isinstance(spl, QSplitter):
			spl = spl.parent()
		return (spl, spl.indexOf(widget))

	def deepChildAt(self, pos):
		"""Get the non-splitter widget at `pos`

		:param pos: the point where to look a widget, in coordinates relative to top-left corner of
		              this `SplitManager`
		:type pos: QPoint
		:return: the first child at position `pos` that is not a splitter, unlike :any:`Splitter.childAt`.
		:rtype: QWidget
		"""
		widget = self.root
		while isinstance(widget, QSplitter):
			widget = widget.childAt(widget.mapFrom(self, pos))
		return widget

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

	## close management
	def closeEvent(self, ev):
		for c in self.allChildren():
			if not c.close():
				ev.ignore()
				return
		ev.accept()

	def canClose(self):
		return all(w.canClose() for w in self.allChildren())


def dumpSplitter(splitter, indent=''):
	print('%s%s %s' % (indent, splitter, splitter.sizes()))
	indent += '  '
	for i in range(splitter.count()):
		child = splitter.widget(i)
		if isinstance(child, QSplitter):
			dumpSplitter(child, indent)
		else:
			print('%s%s' % (indent, child))
