# this project is licensed under the WTFPLv2, see COPYING.txt for details

from PyQt5.QtCore import Qt, QEvent

from ..connector import CategoryMixin
from ..qt import Signal

__all__ = ('acceptIf', 'CategoryMixin', 'WidgetMixin', 'CentralWidgetMixin',
           'parentTabWidget')


def acceptIf(ev, cond):
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
		super(WidgetMixin, self).__init__(**kwargs)

	def giveFocus(self, reason=Qt.OtherFocusReason):
		if not self.isActiveWindow():
			self.activateWindow()

		return self.setFocus(reason)


class CentralWidgetMixin(WidgetMixin):
	windowModifiedChanged = Signal(bool)

	def __init__(self, **kwargs):
		super(CentralWidgetMixin, self).__init__(**kwargs)

	def giveFocus(self, reason=Qt.OtherFocusReason):
		if not self.isActiveWindow():
			self.activateWindow()

		tabBar = parentTabWidget(self)
		if tabBar:
			tabBar.setCurrentWidget(self)

		return self.setFocus(reason)

	def changeEvent(self, ev):
		try:
			super_method = super(CentralWidgetMixin, self).changeEvent
		except AttributeError:
			pass
		else:
			super_method(ev)

		if ev.type() == QEvent.ModifiedChange:
			self.windowModifiedChanged.emit(self.isWindowModified())


def parentTabWidget(widget):
	while widget:
		if hasattr(widget, 'categories') and 'tabwidget' in widget.categories():
			break
		widget = widget.parent()
	return widget
