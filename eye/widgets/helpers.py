# this project is licensed under the WTFPLv2, see COPYING.txt for details

from weakref import WeakValueDictionary

from PyQt5.QtCore import Qt, QEvent

from eye.connector import CategoryMixin
from eye.qt import Signal, override

__all__ = (
	'accept_if', 'CategoryMixin', 'WidgetMixin', 'CentralWidgetMixin',
	'parent_tab_widget',
)


def accept_if(ev, cond):
	"""Accept an event if a condition is True, else ignore it.

	:param ev: the event to accept or ignore
	:type ev: QEvent
	:param cond: the condition determining whether the event should be accepted or ignored
	:returns: whether the event was accepted or not
	"""
	if cond:
		ev.accept()
	else:
		ev.ignore()
	return ev.isAccepted()


class WidgetMixin(CategoryMixin):
	def __init__(self, **kwargs):
		super().__init__(**kwargs)

	def give_focus(self, reason=Qt.OtherFocusReason):
		if not self.isActiveWindow():
			self.activateWindow()

		return self.setFocus(reason)


class CentralWidgetMixin(WidgetMixin):
	windowModifiedChanged = Signal(bool)

	def __init__(self, **kwargs):
		super().__init__(**kwargs)

	def give_focus(self, reason=Qt.OtherFocusReason):
		if not self.isActiveWindow():
			self.activateWindow()

		tab_bar = parent_tab_widget(self)
		if tab_bar:
			tab_bar.setCurrentWidget(self)

		return self.setFocus(reason)

	@override
	def changeEvent(self, ev):
		try:
			super_method = super().changeEvent
		except AttributeError:
			pass
		else:
			super_method(ev)

		if ev.type() == QEvent.ModifiedChange:
			self.windowModifiedChanged.emit(self.isWindowModified())


class WeakHistoryList:
	"""History of objects (from least recent to most recent) with weak references

	This can be typically used for keeping the focus history between widgets.
	"""

	def __init__(self):
		self.objects = WeakValueDictionary()

	def push(self, obj):
		"""Push an object at the front of history

		It does not matter if the object was already in the list.
		"""
		objid = id(obj)
		try:
			del self.objects[objid]
		except KeyError:
			pass

		self.objects[objid] = obj

	def remove(self, obj):
		"""Remove an object of the history

		If the object is garbage-collected, it is automatically removed from the history.
		Does not raise if the object is not (or never was) present in the history.
		"""
		self.objects.pop(id(obj), None)

	def __iter__(self):
		"""Iter over objects, most recent first"""
		return reversed(list(self.objects.values()))

	def __contains__(self, obj):
		return id(obj) in self.objects

	def __len__(self):
		return len(self.objects)


def parent_tab_widget(widget):
	while widget:
		if hasattr(widget, 'categories') and 'tabwidget' in widget.categories():
			break
		widget = widget.parent()
	return widget
