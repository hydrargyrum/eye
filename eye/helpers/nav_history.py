# this project is licensed under the WTFPLv2, see COPYING.txt for details

"""Module for going back/forward in editors

This module allows recording history of cursor positions when switching to another file or jumping
to a function definition for example. Then, navigation can go back and forth between these
positions like a browser.
"""

from logging import getLogger
from weakref import ref

from PyQt5.QtCore import QEvent, Qt, QObject

from eye.app import qApp
from eye.connector import register_signal, disabled, register_setup

__all__ = (
	'push_history', 'go_back', 'go_forward', 'peek_history',
	'push_history_on_editor_change', 'push_history_on_jump',
	'navigate_with_mouse_back', 'set_enabled',
)


LOGGER = getLogger(__name__)
BACKWARD = []
FORWARD = []
POPPING = ()


def push_history(editor, line, col):
	"""Add an entry in history

	Calling this function pushes an entry on top of the backward history (which is a stack) and
	erases forward history.
	"""

	LOGGER.debug('pushing entry')

	BACKWARD.append((ref(editor), line, col))
	del FORWARD[:]


def go_back():
	"""Go back in editor position history"""

	global POPPING

	current = qApp().last_window.current_buffer()

	try:
		rneweditor, newline, newcol = BACKWARD.pop()
	except IndexError:
		LOGGER.debug('cannot go back, stack is empty')
		return False

	editor = rneweditor()
	if not editor:
		LOGGER.debug('skipping entry, editor was closed')
		return go_back()

	POPPING = (rneweditor, newline, newcol)
	FORWARD.append(make_entry(current))

	LOGGER.debug('going back')
	editor.set_cursor_position(newline, newcol)
	editor.give_focus()
	return True


def go_forward():
	"""Go forward in editor position history"""

	global POPPING

	try:
		rneweditor, newline, newcol = FORWARD.pop()
	except IndexError:
		LOGGER.debug('cannot go forward, stack is empty')
		return False

	editor = rneweditor()
	if not editor:
		LOGGER.debug('skipping entry, editor was closed')
		return go_forward()

	POPPING = (rneweditor, newline, newcol)
	BACKWARD.append(make_entry(qApp().last_window.current_buffer()))

	LOGGER.debug('going forward')
	editor.set_cursor_position(newline, newcol)
	editor.give_focus()
	return True


def peek_history():
	"""Get the backward history entry that could be navigated

	Does not perform any navigation, it just returns a 3-tuple containing the
	:any:`eye.widgets.editor.Editor` widget, the line number and column number.

	:returns: the entry to go back or None if there is no history
	:rtype: tuple[Editor, int, int] or None
	"""
	if BACKWARD:
		reditor, line, col = BACKWARD[-1]
		editor = reditor()
		if editor:
			return editor, line, col
		else:
			BACKWARD.pop()
			return peek_history()


@register_signal('editor', 'cursorPositionChanged')
@disabled
def push_history_on_editor_change(editor, line, col):
	"""Push a history entry when moving cursor to another editor and position.
	"""

	try:
		heditor, _, __ = FORWARD[-1]
	except IndexError:
		pass
	else:
		if editor is heditor():
			return

	try:
		heditor, _, __ = BACKWARD[-1]
	except IndexError:
		pass
	else:
		if editor is heditor():
			return

	try:
		heditor, hline, hcol = POPPING
	except ValueError:
		pass
	else:
		if editor is heditor() and line == hline and col == hcol:
			return

	push_history(editor, line, col)


@register_signal('editor', 'position_jumped')
@disabled
def push_history_on_jump(editor, line, col):
	push_history(editor, line, col)


def make_entry(editor):
	"""Returns a tuple suitable for putting in the history stack"""

	line, col = editor.get_cursor_position()
	return (ref(editor), line, col)


class MouseNavFilter(QObject):
	def eventFilter(self, ed, ev):
		if ev.type() == QEvent.MouseButtonPress:
			if ev.buttons() == Qt.BackButton:
				go_back()
			elif ev.buttons() == Qt.ForwardButton:
				go_forward()
		return False


@register_setup('editor')
@disabled
def navigate_with_mouse_back(editor):
	"""Use navigation with Back/Forward mouse buttons

	Certain mice have dedicated back and forward buttons.
	When this callback is enabled, back and forward mouse buttons will call :any:`go_back` and
	:any:`go_forward`.
	"""

	# event filter on editor widget will not catch mouse events, use viewport instead
	view = editor.viewport()
	filter = MouseNavFilter(parent=view)
	view.installEventFilter(filter)


def set_enabled(enabled):
	"""
	Toggles :any:`push_history_on_editor_change`, :any:`push_history_on_jump` and :any:`navigate_with_mouse_back`.
	"""

	push_history_on_editor_change.enabled = enabled
	push_history_on_jump.enabled = enabled
	navigate_with_mouse_back.enabled = enabled
