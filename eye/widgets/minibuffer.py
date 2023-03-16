# this project is licensed under the WTFPLv2, see COPYING.txt for details

from enum import IntFlag

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QLineEdit, QShortcut

from eye.app import qApp
from eye.connector import category_objects
from eye.qt import Signal, Slot
from eye.widgets.helpers import WidgetMixin

__all__ = ('Minibuffer', 'open_mini_buffer', 'get_mini_buffer')


class CloseFlag(IntFlag):
	ON_ENTER = 1
	ON_ESCAPE = 2
	ON_FOCUS_OUT = 4
	ALL = ON_ENTER | ON_ESCAPE | ON_FOCUS_OUT


class Minibuffer(QLineEdit, WidgetMixin):
	def __init__(self, parent=None):
		super(Minibuffer, self).__init__(parent=parent)

		self.status_bar = None
		self.close_flags = 0

		sh = QShortcut(QKeySequence(Qt.Key_Escape), self)
		sh.activated.connect(self.on_escape)

		self.returnPressed.connect(self.on_return_pressed)

		self.add_category('minibuffer')

	def __del__(self):
		self.cancelled.emit()

	def add_to_window(self, window):
		if self.status_bar:
			self.remove()
		self.status_bar = window.statusBar()
		self.status_bar.insertWidget(0, self)

	def remove(self):
		# warning: this triggers the focus-out
		if self.status_bar:
			self.status_bar.removeWidget(self)
			self.status_bar = None

	def set_close_flags(self, f):
		self.close_flags = f

	text_entered = Signal(str)
	cancelled = Signal()

	@Slot()
	def cancel(self):
		self.cancelled.emit()
		self.remove()

	@Slot()
	def on_return_pressed(self):
		self.text_entered.emit(self.text())
		if self.close_flags & CloseFlag.ON_ENTER:
			self.remove()

	@Slot()
	def on_escape(self):
		if self.close_flags & CloseFlag.ON_ESCAPE:
			self.cancel()

	def focusOutEvent(self, ev):
		QLineEdit.focusOutEvent(self, ev)
		if self.close_flags & CloseFlag.ON_FOCUS_OUT:
			self.cancel()


def _make_mini_buffer(text='', placeholder='', window=None, category=None, close_flags=CloseFlag.ALL):
	if window is None:
		window = qApp().last_window

	m = Minibuffer()
	m.set_close_flags(close_flags)
	m.setPlaceholderText(placeholder)
	m.setText(text)
	m.add_to_window(window)
	m.give_focus()
	if category:
		m.add_category(category)
	return m


def open_mini_buffer(text='', placeholder='', window=None, category=None, close_flags=CloseFlag.ALL):
	old = get_mini_buffer(window)
	if old:
		old.cancel()
		old = None
	return _make_mini_buffer(text, placeholder, window, category, close_flags)


def get_mini_buffer(window=None, category=None):
	if window is None:
		window = qApp().last_window

	for mb in category_objects('minibuffer'):
		if mb.window() == window:
			if category and category not in mb.categories():
				return None
			return mb

# TODO: only one minibuffer at a time
# create another minibuffer if different category (because different use)
# possible reuse if same category?
