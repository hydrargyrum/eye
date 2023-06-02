# this project is licensed under the WTFPLv2, see COPYING.txt for details

from eye import connector
from eye.app import qApp
from eye.typing import Location
from eye.widgets.helpers import parent_tab_widget
from eye.widgets.window import Window

__all__ = (
	'find_editor', 'open_editor', 'list_editors',
	'new_editor_open', 'new_editor_share', 'new_editor_try_share',
)


def find_editor(path: str):
	"""Get an editor widget which has `path` opened

	Searches in existing `Editor` widgets if one has `path` opened and return it, or `None` if `path` isn't open
	in any editor. Searches with category `"editor"`.

	:returns: an existing editor or None if no widget matches.
	:rtype: eye.widgets.editor.Editor
	"""
	for ed in connector.category_objects('editor'):
		if ed.path == path:
			return ed


def _get_window() -> Window:
	win = qApp().last_window
	if win is None:
		for win in connector.category_objects('window'):
			break
	return win


def create_editor_widget():
	from eye.widgets.window import Window
	return Window.EditorClass()


def _create_editor(path):
	win = _get_window()
	cur = win.current_buffer()
	tabs = parent_tab_widget(cur)

	ed = create_editor_widget()
	ed.open_file(path)
	tabs.add_widget(ed)

	return ed


def open_editor(path: str, loc: Location | None = None):
	"""Open a file in a new editor or focus an existing one.

	If an editor widget already has `path` open, give it focus. Else, create a new editor (in a new
	tab of the currently focused tab widget).

	:param path: path of the file to open in an editor widget
	:type path: str
	:param loc: optional line and column where to focus
	:returns: an editor widget open to the file
	:rtype: :any:`eye.widgets.editor.Editor`
	"""

	ed = find_editor(path)
	if not ed:
		ed = _create_editor(path)

	if loc:
		ed.goto1(*loc)
	ed.give_focus()

	ed.position_jumped.emit(*ed.getCursorPosition())
	return ed


def list_editors():
	"""List all editor widgets

	Uses category `"editor"`.
	"""
	for ed in connector.category_objects('editor'):
		yield ed.path


def current_buffer():
	"""Get currently focused editor"""
	win = _get_window()
	return win.current_buffer()


def _default_tabs():
	win = _get_window()
	cur = win.current_buffer()
	return parent_tab_widget(cur)


def _do_new(ed, loc: Location | None, parent_tab_bar):
	if parent_tab_bar is None:
		parent_tab_bar = _default_tabs()
	if loc:
		ed.goto1(*loc)
	parent_tab_bar.add_widget(ed)


def new_editor_open(path, loc: Location = None, parent_tab_bar=None):
	"""Create a new editor with file `path` open

	An Editor widget is created, with the contents of file at `path`.
	The new widget is attached to either the current tab widget or to `parent_tab_bar` if given. If `loc` is given,
	the widget will display this line-column index by default.

	A new Editor will be created even if another Editor exists with the same file open already exists, and their
	documents won't be shared together, so editing in a widget won't propagate the changes into the other widget.

	.. seealso:: :any:`eye.widgets.editor.Editor.goto1`

	:param path: path of the file to open
	:type path: str
	:param parent_tab_bar: the parent tab widget where to append the editor.
	                       If None, the currently focused tab widget will be used.
	:type parent_tab_bar: :any:`eye.widgets.tabs.TabWidget`
	:param loc: if not None, the editor shall be opened with this line/column shown (starting at 1)
	:returns: the new editor
	:rtype: eye.widgets.editor.Editor
	"""
	ed = create_editor_widget()
	ed.open_file(path)
	_do_new(ed, loc, parent_tab_bar)
	return ed


def new_editor_share(ed, loc: Location | None = None, parent_tab_bar=None):
	"""Create a new editor with same document as `ed` open

	An editor widget is created, with the same document as existing editor `ed`.
	The new widget is attached to either the current tab widget or to `parent_tab_bar` if given. If `loc` is given,
	the widget will display this line-column index by default.

	Since the documents of the new editor widget and `ed` are shared, making an modification in a widget (e.g.
	adding/removing characters, modifying markers/indicators, etc.) will propagate it to the other widget.

	.. seealso:: :any:`new_editor_open` for the `loc` and `parent_tab_bar` parameters.

	:param ed: the editor with which the new editor should share the document
	:type ed: eye.widgets.editor.Editor
	:param loc: if not None, the editor shall be opened with this line/column shown (starting at 1)
	:param parent_tab_bar: the parent tab widget where to append the editor.
	                       If None, the currently focused tab widget will be used.
	:type parent_tab_bar: :any:`eye.widgets.tabs.TabWidget`
	:returns: the new editor
	:rtype: eye.widgets.editor.Editor
	"""
	new = create_editor_widget()
	new.open_document(ed)
	_do_new(new, loc, parent_tab_bar)
	return new


def new_editor_try_share(path, loc=None, parent_tab_bar=None):
	"""Create a new editor with file `path` open, using an open document if possible

	If another editor exists with `path` already open, a new editor is created with :any:`new_editor_share`, else
	a new editor is created with :any:`new_editor_open`.

	:param path: path of the file to open
	:type path: str
	:param loc: if not None, the editor shall be opened with this line/column shown (starting at 1)
	:type loc: tuple[int, int]
	:param parent_tab_bar: the parent tab widget where to append the editor.
	                       If None, the currently focused tab widget will be used.
	:type parent_tab_bar: :any:`eye.widgets.tabs.TabWidget`
	:rtype: eye.widgets.editor.Editor
	"""
	old = find_editor(path)
	if old:
		return new_editor_share(old, loc, parent_tab_bar)
	else:
		return new_editor_open(path, loc, parent_tab_bar)
