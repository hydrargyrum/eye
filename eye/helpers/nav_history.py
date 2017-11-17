# this project is licensed under the WTFPLv2, see COPYING.txt for details

"""Module for going back/forward in editors

This module allows recording history of cursor positions when switching to another file or jumping
to a function definition for example. Then, navigation can go back and forth between these
positions like a browser.
"""

from weakref import ref
from logging import getLogger

from PyQt5.QtCore import QEvent, Qt, QObject

from ..app import qApp
from ..connector import registerSignal, disabled, registerSetup


__all__ = ('pushHistory', 'goBack', 'goForward', 'peekHistory',
           'pushHistoryOnEditorChange', 'pushHistoryOnJump',
           'navigateWithMouseBack', 'setEnabled',
          )


LOGGER = getLogger(__name__)
BACKWARD = []
FORWARD = []
POPPING = ()


def pushHistory(editor, line, col):
	"""Add an entry in history

	Calling this function pushes an entry on top of the backward history (which is a stack) and
	erases forward history.
	"""

	LOGGER.debug('pushing entry')

	BACKWARD.append((ref(editor), line, col))
	del FORWARD[:]


def goBack():
	"""Go back in editor position history"""

	global POPPING

	current = qApp().lastWindow.currentBuffer()

	try:
		rneweditor, newline, newcol = BACKWARD.pop()
	except IndexError:
		LOGGER.debug('cannot go back, stack is empty')
		return False

	editor = rneweditor()
	if not editor:
		LOGGER.debug('skipping entry, editor was closed')
		return goBack()

	POPPING = (rneweditor, newline, newcol)
	FORWARD.append(makeEntry(current))

	LOGGER.debug('going back')
	editor.setCursorPosition(newline, newcol)
	editor.giveFocus()
	return True


def goForward():
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
		return goForward()

	POPPING = (rneweditor, newline, newcol)
	BACKWARD.append(makeEntry(qApp().lastWindow.currentBuffer()))

	LOGGER.debug('going forward')
	editor.setCursorPosition(newline, newcol)
	editor.giveFocus()
	return True


def peekHistory():
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
			return peekHistory()


@registerSignal('editor', 'cursorPositionChanged')
@disabled
def pushHistoryOnEditorChange(editor, line, col):
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

	pushHistory(editor, line, col)


@registerSignal('editor', 'positionJumped')
@disabled
def pushHistoryOnJump(editor, line, col):
	pushHistory(editor, line, col)


def makeEntry(editor):
	"""Returns a tuple suitable for putting in the history stack"""

	line, col = editor.getCursorPosition()
	return (ref(editor), line, col)


class MouseNavFilter(QObject):
	def eventFilter(self, ed, ev):
		if ev.type() == QEvent.MouseButtonPress:
			if ev.buttons() == Qt.BackButton:
				goBack()
			elif ev.buttons() == Qt.ForwardButton:
				goForward()
		return False


@registerSetup('editor')
@disabled
def navigateWithMouseBack(editor):
	"""Use navigation with Back/Forward mouse buttons

	Certain mice have dedicated back and forward buttons.
	When this callback is enabled, back and forward mouse buttons will call :any:`goBack` and
	:any:`goForward`.
	"""

	# event filter on editor widget will not catch mouse events, use viewport instead
	view = editor.viewport()
	filter = MouseNavFilter(parent=view)
	view.installEventFilter(filter)


def setEnabled(enabled):
	"""
	Toggles :any:`pushHistoryOnEditorChange`, :any:`pushHistoryOnJump` and :any:`navigateWithMouseBack`.
	"""

	pushHistoryOnEditorChange.enabled = enabled
	pushHistoryOnJump.enabled = enabled
	navigateWithMouseBack.enabled = enabled

