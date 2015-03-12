
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

def addBookmark(ed):
	ln = ed.getCursorPosition()[0]

	marker = ed.markers['bookmark']  
	if marker.isAt(ln):
		marker.removeAt(ln)
	else:
		marker.putAt(ln)

def nextBookmark(ed):
        ln = ed.getCursorPosition()[0]

        ln = ed.markers['bookmark'].getNext(ln + 1)
        if ln < 0:
                ln = ed.markers['bookmark'].getNext(0)
        ed.setCursorPosition(ln, 0)

def previousBookmark(ed):
        ln = ed.getCursorPosition()[0]

        ln = ed.markers['bookmark'].getPrevious(ln - 1)
        if ln < 0:
                ln = ed.markers['bookmark'].getPrevious(ed.lines())
