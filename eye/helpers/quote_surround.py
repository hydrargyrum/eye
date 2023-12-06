# this project is licensed under the WTFPLv2, see COPYING.txt for details

"""Module for surrounding selected text with quotes or other chars.

When enabled, in an editor, if some text is selected and a quote character is typed, the selected
text will be surrounded with the quote character instead of being replaced by the character.
It can also surround with parentheses and other characters.

Using the raw :any:`trySurroundSelectionEvent` and :any:`trySurroundSelection` helpers, it's
possible to implement different surrounding mappings depending on the edited file type.
"""

from PyQt5.QtCore import QEvent, Qt

from eye.connector import register_event_filter, disabled

__all__ = (
	'set_enabled', 'auto_surround_selection',
	'try_surround_selection', 'try_surround_selection_event',
	'BASE_SURROUND_MAPPING',
)


BASE_SURROUND_MAPPING = {
	"'": "'",
	'"': '"',
	'`': '`',
	'{': '}',
	'(': ')',
	'[': ']',
	'<': '>',
}

"""Default surround mapping.

A surround mapping should have the same format: a dict mapping characters to a template string
using '%'-formatting. If a char is not present in such a table, no surrounding will be performed
and it will simply replace the selected text.
"""


def try_surround_selection_event(editor, event, map_table):
	"""Try to do char-surrounding using a mapping table.

	Will not do any surrounding if a keyboard modifier key (e.g. Ctrl) is in pressed state.
	If the editor has multiple selections, each selection will be surrounded separately.
	Calls :any:`trySurroundSelection`.

	.. seealso:: :any:`BASE_SURROUND_MAPPING`

	:param editor: editor where to try to do surrounding
	:type editor: :any:`eye.widgets.editor.Editor`
	:param event: typing event containing the char to do the surrounding
	:type event: :any:`QKeyEvent`
	:param map_table: mapping table listing chars and their replacement
	:type map_table: dict[str, str]
	:returns: True if a char surrounding was performed, else False. The value can be used for
	          returning from an event filter function.
	:rtype: bool
	"""

	if editor.selections_empty():
		return False
	elif event.modifiers() == Qt.KeyboardModifiers:
		return False

	char = event.text()
	return try_surround_selection(editor, char, map_table)


def try_surround_selection(editor, char, map_table):
	"""Try to do char-surrounding using a mapping table.

	Will not do any surrounding if a keyboard modifier key (e.g. Ctrl) is in pressed state.
	If the editor has multiple selections, each selection will be surrounded separately.

	:param editor: editor where to try to do surrounding
	:type editor: :any:`eye.widgets.editor.Editor`
	:param char: the character to do the surrounding
	:type char: str
	:param map_table: mapping table listing chars and their replacement
	:type map_table: dict[str, str]
	:returns: True if a char surrounding was performed, else False. The value can be used for
	          returning from an event filter function.
	:rtype: bool
	"""

	if char not in map_table:
		return False

	# when a surrounding is done, it will shift (invalidate) all line-indexes after it
	# doing in reverse order avoids having to compute shifting
	sels = reversed([editor.get_selection_n(n) for n in range(editor.selections_count())])
	with editor.undo_group(True):
		for lfrom, ifrom, lto, ito in sels:
			if (lfrom, ifrom) > (lto, ito):
				lfrom, ifrom, lto, ito = lto, ito, lfrom, ifrom
			editor.insertAt(map_table[char], lto, ito)
			editor.insertAt(char, lfrom, ifrom)

	return True


@register_event_filter('editor', [QEvent.KeyPress])
@disabled
def auto_surround_selection(editor, event):
	"""Event-filter performing default char surrounding.

	Calls :any:`try_surround_selection_event` and uses :any:`BASE_SURROUND_MAPPING` as mapping table.
	If surrounding was performed, the event is filtered so it's not caught by the editor widget.
	"""

	return try_surround_selection_event(editor, event, BASE_SURROUND_MAPPING)


def set_enabled(b):
	"""Enables :any:`auto_surround_selection`."""

	auto_surround_selection.enabled = b
