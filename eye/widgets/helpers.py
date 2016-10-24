# this project is licensed under the WTFPLv2, see COPYING.txt for details

from PyQt5.QtCore import pyqtSignal as Signal, pyqtSlot as Slot, Qt, QEvent
from PyQt5.QtGui import QIcon

from ..connector import CategoryMixin

__all__ = ('acceptIf', 'CategoryMixin', 'WidgetMixin', 'CentralWidgetMixin')


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

	def parentTabBar(self):
		w = self
		while True:
			if hasattr(w, 'categories') and 'tabwidget' in w.categories():
				break
			w = w.parent()
		return w

	def giveFocus(self, reason=Qt.OtherFocusReason):
		if not self.isActiveWindow():
			self.activateWindow()

		tabBar = self.parentTabBar()
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
