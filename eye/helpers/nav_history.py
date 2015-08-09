
from weakref import ref

from ..app import qApp
from ..connector import registerSignal, disabled


__all__ = ('pushHistory', 'popHistory', 'peekHistory',
           'pushHistoryOnEditorChange')


HISTORY = []

def pushHistory(editor, line, col):
	HISTORY.append((ref(editor), line, col))


def popHistory():
	# TODO: pop again if we didn't move
	current = qApp().win.lastFocus

	try:
		reditor, line, col = HISTORY.pop()
	except IndexError:
		return
	if not reditor:
		return popHistory()

	if ref(current) == reditor:
		return popHistory()

	editor = reditor()
	editor.setCursorPosition(line, col)
	editor.giveFocus()


def peekHistory():
	if HISTORY:
		reditor, line, col = HISTORY[-1]
		if reditor:
			return reditor(), line, col


@registerSignal('editor', 'cursorPositionChanged')
@disabled
def pushHistoryOnEditorChange(editor, line, col):
	entry = peekHistory()
	if entry and entry[0] == ref(editor):
		HISTORY.pop()
	pushHistory(editor, line, col)
