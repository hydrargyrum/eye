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

from __future__ import print_function

import logging

from PyQt5.QtCore import Qt, QPoint, QRect, QTimer
from PyQt5.QtWidgets import QSplitter, QWidget, QStackedLayout

from eye import consts
from eye.qt import Slot, override
from eye.widgets.helpers import WidgetMixin

__all__ = ('SplitManager', 'Splitter', 'QSplitter')


LOGGER = logging.getLogger(__name__)


class Splitter(QSplitter, WidgetMixin):
	"""Splitter widget for a single splitting level

	`Splitter` objects are handled by the :any:`SplitManager` widget.
	"""

	def __init__(self, **kwargs):
		super().__init__(**kwargs)

		self.add_category('splitter')

	def child_at(self, pos):
		"""Return direct child widget at the given position

		The returned child will be a direct child of `self`. If the real widget at `pos` is in a
		sub-Splitter, only the sub-Splitter which is a direct child of `self` will be returned.

		:type pos: QPoint
		:param pos: relative to the top-left corner of this `Splitter` (which is at `(0, 0)`).
		:return: the direct child at `pos`, a :any:`Py_qt5.Qt_widgets.QSplitter_handle` if `pos` is
		         on a handle, or None if `pos` is outside `self`'s geometry
		:rtype: QWidget
		"""
		if not self.rect().contains(pos):
			return None
		for i in range(self.count()):
			for w in (self.widget(i), self.handle(i)):
				if w.geometry().contains(pos):
					return w

	def parent_manager(self):
		"""Returns the :any:`Split_manager` managing this splitter

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

	children = widgets

	def remove_child(self, widget):
		assert self.isAncestorOf(widget)
		assert self is not widget

		widget.setParent(None)

	def replace_child(self, child, new):
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
		super().__init__(**kwargs)

		self.root = self.SplitterClass(orientation=Qt.Horizontal)

		layout = QStackedLayout()
		self.setLayout(layout)
		layout.addWidget(self.root)

		self.optimize_timer = QTimer()
		self.optimize_timer.setInterval(0)
		self.optimize_timer.setSingleShot(True)
		self.optimize_timer.timeout.connect(self._optimize)

		self.add_category('splitmanager')

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
				parent.remove_child(spl)
			elif spl.count() == 1:
				child = next(iter(spl.children()))
				LOGGER.debug('replace %s by only child %s', spl, child)
				parent.replace_child(spl, child)

	## split/move/delete
	def split_at(self, current_widget, direction, new_widget):
		"""Insert a widget into the splits

		`new_widget` is inserted next to `current_widget`, in `direction`. `current_widget` size is
		halved, and the newly created space is used for `new_widget`.

		A new `Splitter` may be created if `current_widget` is not in a `Splitter` of the proper
		orientation. For example, if `current_widget` is in horizontal splitter, but `new_widget`
		should be inserted below, a new vertical splitter replaces `current_widget` and both
		`current_widget` and `new_widget` are put in it.

		:param current_widget: the widget next to which insert a new widget
		:param direction: direction relative to `current_widget` where to insert `new_widget`.
		                  Possible values are the 4 directions from :any:`eye.consts`.
		:param new_widget: the widget to insert
		"""

		if current_widget is None:
			parent = self.root
			idx = 0
		else:
			assert self.isAncestorOf(current_widget)
			parent = current_widget.parent()
			idx = parent.indexOf(current_widget)

		orientation = consts.ORIENTATIONS[direction]
		if parent.orientation() == orientation:
			oldsize = parent.sizes()
			if oldsize:
				oldsize[idx] //= 2
				oldsize.insert(idx, oldsize[idx])

			if direction in (consts.DOWN, consts.RIGHT):
				idx += 1

			LOGGER.debug('inserting %r at %r in %r in the same orientation', new_widget, idx, parent)
			parent.insertWidget(idx, new_widget)

			if oldsize:
				parent.setSizes(oldsize)
		else:
			# current_widget is moved, so it may lose focus
			refocus = current_widget and current_widget.hasFocus()

			new_split = self.SplitterClass(orientation=orientation)

			LOGGER.debug('inserting %r in new splitter %r at %r of %r in different orientation', new_widget, new_split, idx, parent)

			if current_widget:
				# save/restore size because Qt goes crazy when moving splitter widgets around
				oldsize = parent.sizes()
				if direction in (consts.DOWN, consts.RIGHT):
					new_split.addWidget(current_widget)
					parent.insertWidget(idx, new_split)
					new_split.addWidget(new_widget)
				else:
					new_split.addWidget(new_widget)
					parent.insertWidget(idx, new_split)
					new_split.addWidget(current_widget)
				parent.setSizes(oldsize)
				new_split.setSizes([1, 1]) # force Qt to rebalance it
			else:
				new_split.addWidget(new_widget)
				parent.insertWidget(idx, new_split)

			if refocus:
				current_widget.setFocus()

	def move_widget(self, current_widget, direction, new_widget):
		"""Move a child widget in another part of the splitting

		`current_widget`, `direction` and `new_widget` have the same meaning as for the `split_at`
		method, except that `new_widget` must be already present in the `SplitManager`.
		"""

		if current_widget is new_widget:
			LOGGER.info('will not move %r over itself', current_widget)
			return

		self.remove_widget(new_widget)
		self.split_at(current_widget, direction, new_widget)
		self.optimize_timer.start()

	def remove_widget(self, widget):
		if not self.isAncestorOf(widget):
			LOGGER.info("cannot remove widget %r since it doesn't belong to %r", widget, self)
			return

		spl, _ = self.child_id(widget)
		spl.remove_child(widget)
		self.optimize_timer.start()

	## balance
	@Slot()
	def balance_splits_recursive(self, start_at=None):
		for w in self._iter_recursive(start_at):
			if isinstance(w, self.SplitterClass):
				self.balance_splits(w)

	def balance_splits(self, spl):
		spl.setSizes([1] * spl.count())  # qt redistributes space

	## neighbours
	def _neighbour_up(self, widget, direction):
		if widget is None or widget is self.root:
			return None

		spl, idx = self.child_id(widget)

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
	def all_children(self):
		"""Get all non-splitter children widgets (recursive)

		Takes all children :any:`eye.widgets.splitter.Splitter` widgets (recursively) and return
		their direct children (the children that are not `Splitter` themselves).

		:rtype: list
		"""
		return [w for w in self._iter_recursive() if not isinstance(w, self.SplitterClass)]

	def child_rect(self, widget):
		return QRect(widget.mapTo(self, QPoint()), widget.size())

	def child_id(self, widget):
		spl = widget.parent()
		while not isinstance(spl, QSplitter):
			spl = spl.parent()
		return (spl, spl.indexOf(widget))

	def deep_child_at(self, pos):
		"""Get the non-splitter widget at `pos`

		:param pos: the point where to look a widget, in coordinates relative to top-left corner of
		              this `SplitManager`
		:type pos: QPoint
		:return: the first child at position `pos` that is not a splitter, unlike :any:`Splitter.child_at`.
		:rtype: QWidget
		"""
		widget = self.root
		while isinstance(widget, QSplitter):
			widget = widget.childAt(widget.mapFrom(self, pos))
		return widget

	def _iter_recursive(self, start_at=None):
		if start_at is None:
			start_at = self.root

		splitters = [start_at]
		yield start_at
		while splitters:
			spl = splitters.pop()
			for i in range(spl.count()):
				w = spl.widget(i)
				if isinstance(w, self.SplitterClass):
					splitters.append(w)
				yield w

	## close management
	@override
	def closeEvent(self, ev):
		for c in self.all_children():
			if not c.close():
				ev.ignore()
				return
		ev.accept()

	def can_close(self):
		"""Returns True if all sub-widgets can be closed."""
		return all(w.can_close() for w in self.all_children())


def dump_splitter(splitter, indent=''):
	print('%s%s %s' % (indent, splitter, splitter.sizes()))
	indent += '  '
	for i in range(splitter.count()):
		child = splitter.widget(i)
		if isinstance(child, QSplitter):
			dump_splitter(child, indent)
		else:
			print('%s%s' % (indent, child))
