# this project is licensed under the WTFPLv2, see COPYING.txt for details

"""Automatic syntax coloring plugin

This plugins adds automatic syntax coloring in an editor based on file extension. See :doc:`eye.lexers`.

Simple usage:

	>>> import eye.helpers.lexer
	>>> eye.helpers.lexer.setEnabled(True)
"""

import os

from eye import lexers
from eye.connector import registerSignal, disabled

__all__ = ('setEnabled', 'autoLexer')

@registerSignal(['editor'], 'fileOpened')
@registerSignal(['editor'], 'fileSaved')
@disabled
def autoLexer(editor, path=None):
	"""Enables syntax coloring for an editor

	The correct lexer is determined using file extension. See :any:`eye.lexers.extensionToLexer`.
	"""
	if editor.lexer():
		return

	ext = os.path.splitext(editor.path)[1]
	cls = lexers.extensionToLexer(ext)
	if cls:
		editor.setLexer(cls())



def setEnabled(enabled=True):
	autoLexer.enabled = enabled
