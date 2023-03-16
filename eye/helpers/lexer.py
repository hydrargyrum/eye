# this project is licensed under the WTFPLv2, see COPYING.txt for details

"""Automatic syntax coloring plugin

This plugins adds automatic syntax coloring in an editor based on file extension. See :doc:`eye.lexers`.

Simple usage:

	>>> import eye.helpers.lexer
	>>> eye.helpers.lexer.set_enabled(True)
"""

import os

from eye import lexers
from eye.connector import register_signal, disabled

__all__ = ('set_enabled', 'auto_lexer')


@register_signal(['editor'], 'file_opened')
@register_signal(['editor'], 'file_saved')
@disabled
def auto_lexer(editor, path=None):
	"""Enables syntax coloring for an editor

	The correct lexer is determined using file extension. See :any:`eye.lexers.extensionToLexer`.
	"""
	if editor.lexer():
		return

	ext = os.path.splitext(editor.path)[1]
	cls = lexers.extension_to_lexer(ext)
	if cls:
		editor.setLexer(cls())


def set_enabled(enabled=True):
	auto_lexer.enabled = enabled
