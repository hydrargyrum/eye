# this project is licensed under the WTFPLv2, see COPYING.txt for details

from ..connector import registerSignal, disabled
from .. import lexers

import os

__all__ = ('autoLexer',)

@registerSignal(['editor'], 'fileOpened')
@registerSignal(['editor'], 'fileSaved')
@disabled
def autoLexer(ed, path):
	if ed.lexer():
		return

	ext = os.path.splitext(ed.path)[1]
	cls = lexers.extensionToLexer(ext)
	if cls:
		ed.setLexer(cls())
