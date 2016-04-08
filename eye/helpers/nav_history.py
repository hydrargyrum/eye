# this project is licensed under the WTFPLv2, see COPYING.txt for details

from weakref import ref
from logging import getLogger

from ..app import qApp
from ..connector import registerSignal, disabled


__all__ = ('pushHistory', 'goBack', 'goForward', 'peekHistory',
           'pushHistoryOnEditorChange', 'pushHistoryOnJump')


LOGGER = getLogger(__name__)
BACKWARD = []
FORWARD = []
POPPING = ()


def pushHistory(editor, line, col):
	LOGGER.debug('pushing entry')

	BACKWARD.append((ref(editor), line, col))
	del FORWARD[:]


def goBack():
	global POPPING

	current = qApp().lastWindow.currentBuffer()

	try:
		rneweditor, newline, newcol = BACKWARD.pop()
	except IndexError:
		LOGGER.debug('cannot go back, stack is empty')
		return False
	if not rneweditor:
		LOGGER.debug('skipping entry, editor was closed')
		return goBack()

	POPPING = (rneweditor, newline, newcol)
	FORWARD.append(makeEntry(current))

	LOGGER.debug('going back')
	editor = rneweditor()
	editor.setCursorPosition(newline, newcol)
	editor.giveFocus()
	return True


def goForward():
	global POPPING

	try:
		rneweditor, newline, newcol = FORWARD.pop()
	except IndexError:
		LOGGER.debug('cannot go forward, stack is empty')
		return False
	if not rneweditor:
		LOGGER.debug('skipping entry, editor was closed')
		return goForward()

	POPPING = (rneweditor, newline, newcol)
	BACKWARD.append(makeEntry(qApp().lastWindow.currentBuffer()))

	LOGGER.debug('going forward')
	editor = rneweditor()
	editor.setCursorPosition(newline, newcol)
	editor.giveFocus()
	return True


def peekHistory():
	if BACKWARD:
		reditor, line, col = BACKWARD[-1]
		if reditor:
			return reditor(), line, col


@registerSignal('editor', 'cursorPositionChanged')
@disabled
def pushHistoryOnEditorChange(editor, line, col):
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
	line, col = editor.getCursorPosition()
	return (ref(editor), line, col)
