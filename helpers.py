
from connector import registerSignal, disabled
import lexers
import os

__all__ = 'autoLexer linesMarginWidth'


@registerSignal(['editor'], 'fileOpened')
@registerSignal(['editor'], 'fileSaved')
@disabled
def autoLexer(ed):
	if ed.lexer():
		return
		
	ext = os.path.splitext(ed.path)[1]
	cls = lexers.extensionToLexer(ext)
	if cls:
		ed.setLexer(cls())

@registerSignal(['editor'], 'linesChanged')
@disabled
def linesMarginWidth(ed):
	if 'lines' in ed.margins:
		# add one character width as it may be truncated
		ed.margins['lines'].setWidth('0%d' % ed.lines())

