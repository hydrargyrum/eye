# this project is licensed under the WTFPLv2, see COPYING.txt for details

from .. import connector
from ..app import qApp
from ..widgets.editor import Editor

__all__ = ('findEditor', 'openEditor', 'listEditors')


def findEditor(path):
	for ed in connector.categoryObjects('editor'):
		if ed.path == path:
			return ed


def _createEditor(path):
	win = qApp().lastWindow
	cur = win.currentBuffer()
	tabs = cur.parentTabBar()

	ed = Editor()
	ed.openFile(path)
	tabs.addWidget(ed)

	return ed


def openEditor(path, loc=None):
	ed = findEditor(path)
	if not ed:
		ed = _createEditor(path)

	if loc:
		ed.goto1(*loc)
	ed.giveFocus()

	ed.positionJumped.emit(*ed.getCursorPosition())
	return ed


def listEditors():
	for ed in connector.categoryObjects('editor'):
		yield ed.path


def currentBuffer():
	win = qApp().lastWindow
	return win.currentBuffer()
