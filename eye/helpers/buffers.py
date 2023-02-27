# this project is licensed under the WTFPLv2, see COPYING.txt for details

from eye import connector
from eye.app import qApp
from eye.widgets.helpers import parentTabWidget

__all__ = ('findEditor', 'openEditor', 'listEditors',
           'newEditorOpen', 'newEditorShare', 'newEditorTryShare')


def findEditor(path):
	"""Get an editor widget which has `path` opened

	Searches in existing `Editor` widgets if one has `path` opened and return it, or `None` if `path` isn't open
	in any editor. Searches with category `"editor"`.

	:returns: an existing editor or None if no widget matches.
	:rtype: eye.widgets.editor.Editor
	"""
	for ed in connector.categoryObjects('editor'):
		if ed.path == path:
			return ed


def _get_window():
	win = qApp().lastWindow
	if win is None:
		for win in connector.categoryObjects('window'):
			break
	return win


def createEditorWidget():
	from eye.widgets.window import Window
	return Window.EditorClass()


def _create_editor(path):
	win = _get_window()
	cur = win.currentBuffer()
	tabs = parentTabWidget(cur)

	ed = createEditorWidget()
	ed.openFile(path)
	tabs.addWidget(ed)

	return ed


def openEditor(path, loc=None):
	"""Open a file in a new editor or focus an existing one.

	If an editor widget already has `path` open, give it focus. Else, create a new editor (in a new
	tab of the currently focused tab widget).

	:param path: path of the file to open in an editor widget
	:type path: str
	:param loc: optional line and column where to focus
	:type loc: tuple[int, int]
	:returns: an editor widget open to the file
	:rtype: :any:`eye.widgets.editor.Editor`
	"""

	ed = findEditor(path)
	if not ed:
		ed = _create_editor(path)

	if loc:
		ed.goto1(*loc)
	ed.giveFocus()

	ed.positionJumped.emit(*ed.getCursorPosition())
	return ed


def listEditors():
	"""List all editor widgets

	Uses category `"editor"`.
	"""
	for ed in connector.categoryObjects('editor'):
		yield ed.path


def currentBuffer():
	"""Get currently focused editor"""
	win = _get_window()
	return win.currentBuffer()


def _default_tabs():
	win = _get_window()
	cur = win.currentBuffer()
	return parentTabWidget(cur)


def _do_new(ed, loc, parentTabBar):
	if parentTabBar is None:
		parentTabBar = _default_tabs()
	if loc:
		ed.goto1(*loc)
	parentTabBar.addWidget(ed)


def newEditorOpen(path, loc=None, parentTabBar=None):
	"""Create a new editor with file `path` open

	An Editor widget is created, with the contents of file at `path`.
	The new widget is attached to either the current tab widget or to `parentTabBar` if given. If `loc` is given,
	the widget will display this line-column index by default.

	A new Editor will be created even if another Editor exists with the same file open already exists, and their
	documents won't be shared together, so editing in a widget won't propagate the changes into the other widget.

	.. seealso:: :any:`eye.widgets.editor.Editor.goto1`

	:param path: path of the file to open
	:type path: str
	:param parentTabBar: the parent tab widget where to append the editor.
	                     If None, the currently focused tab widget will be used.
	:type parentTabBar: :any:`eye.widgets.tabs.TabWidget`
	:param loc: if not None, the editor shall be opened with this line/column shown (starting at 1)
	:type loc: tuple[int, int]
	:returns: the new editor
	:rtype: eye.widgets.editor.Editor
	"""
	ed = createEditorWidget()
	ed.openFile(path)
	_do_new(ed, loc, parentTabBar)
	return ed


def newEditorShare(ed, loc=None, parentTabBar=None):
	"""Create a new editor with same document as `ed` open

	An editor widget is created, with the same document as existing editor `ed`.
	The new widget is attached to either the current tab widget or to `parentTabBar` if given. If `loc` is given,
	the widget will display this line-column index by default.

	Since the documents of the new editor widget and `ed` are shared, making an modification in a widget (e.g.
	adding/removing characters, modifying markers/indicators, etc.) will propagate it to the other widget.

	.. seealso:: :any:`newEditorOpen` for the `loc` and `parentTabBar` parameters.

	:param ed: the editor with which the new editor should share the document
	:type ed: eye.widgets.editor.Editor
	:param loc: if not None, the editor shall be opened with this line/column shown (starting at 1)
	:type loc: tuple[int, int]
	:param parentTabBar: the parent tab widget where to append the editor.
	                     If None, the currently focused tab widget will be used.
	:type parentTabBar: :any:`eye.widgets.tabs.TabWidget`
	:returns: the new editor
	:rtype: eye.widgets.editor.Editor
	"""
	new = createEditorWidget()
	new.openDocument(ed)
	_do_new(new, loc, parentTabBar)
	return new


def newEditorTryShare(path, loc=None, parentTabBar=None):
	"""Create a new editor with file `path` open, using an open document if possible

	If another editor exists with `path` already open, a new editor is created with :any:`newEditorShare`, else
	a new editor is created with :any:`newEditorOpen`.

	:param path: path of the file to open
	:type path: str
	:param loc: if not None, the editor shall be opened with this line/column shown (starting at 1)
	:type loc: tuple[int, int]
	:param parentTabBar: the parent tab widget where to append the editor.
	                     If None, the currently focused tab widget will be used.
	:type parentTabBar: :any:`eye.widgets.tabs.TabWidget`
	:rtype: eye.widgets.editor.Editor
	"""
	old = findEditor(path)
	if old:
		return newEditorShare(old, loc, parentTabBar)
	else:
		return newEditorOpen(path, loc, parentTabBar)
