# this project is licensed under the WTFPLv2, see COPYING.txt for details

from enum import IntFlag

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QLineEdit, QShortcut

from eye.app import qApp
from eye.connector import categoryObjects
from eye.qt import Signal, Slot
from eye.widgets.helpers import WidgetMixin

__all__ = ('Minibuffer', 'openMiniBuffer', 'getMiniBuffer')


class CloseFlag(IntFlag):
	ON_ENTER = 1
	ON_ESCAPE = 2
	ON_FOCUS_OUT = 4
	ALL = ON_ENTER | ON_ESCAPE | ON_FOCUS_OUT


class Minibuffer(QLineEdit, WidgetMixin):
	def __init__(self, parent=None):
		super(Minibuffer, self).__init__(parent=parent)

		self.statusBar = None
		self.closeFlags = 0

		sh = QShortcut(QKeySequence(Qt.Key_Escape), self)
		sh.activated.connect(self.onEscape)

		self.returnPressed.connect(self.onReturnPressed)

		self.addCategory('minibuffer')

	def __del__(self):
		self.cancelled.emit()

	def addToWindow(self, window):
		if self.statusBar:
			self.remove()
		self.statusBar = window.statusBar()
		self.statusBar.insertWidget(0, self)

	def remove(self):
		# warning: this triggers the focus-out
		if self.statusBar:
			self.statusBar.removeWidget(self)
			self.statusBar = None

	def setCloseFlags(self, f):
		self.closeFlags = f

	textEntered = Signal(str)
	cancelled = Signal()

	@Slot()
	def cancel(self):
		self.cancelled.emit()
		self.remove()

	@Slot()
	def onReturnPressed(self):
		self.textEntered.emit(self.text())
		if self.closeFlags & CloseFlag.ON_ENTER:
			self.remove()

	@Slot()
	def onEscape(self):
		if self.closeFlags & CloseFlag.ON_ESCAPE:
			self.cancel()

	def focusOutEvent(self, ev):
		QLineEdit.focusOutEvent(self, ev)
		if self.closeFlags & CloseFlag.ON_FOCUS_OUT:
			self.cancel()


def _make_mini_buffer(text='', placeholder='', window=None, category=None, closeFlags=CloseFlag.ALL):
	if window is None:
		window = qApp().lastWindow

	m = Minibuffer()
	m.setCloseFlags(closeFlags)
	m.setPlaceholderText(placeholder)
	m.setText(text)
	m.addToWindow(window)
	m.giveFocus()
	if category:
		m.addCategory(category)
	return m


def openMiniBuffer(text='', placeholder='', window=None, category=None, closeFlags=CloseFlag.ALL):
	old = getMiniBuffer(window)
	if old:
		old.cancel()
		old = None
	return _make_mini_buffer(text, placeholder, window, category, closeFlags)


def getMiniBuffer(window=None, category=None):
	if window is None:
		window = qApp().lastWindow

	for mb in categoryObjects('minibuffer'):
		if mb.window() == window:
			if category and category not in mb.categories():
				return None
			return mb

# TODO: only one minibuffer at a time
# create another minibuffer if different category (because different use)
# possible reuse if same category?
