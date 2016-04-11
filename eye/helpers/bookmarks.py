# this project is licensed under the WTFPLv2, see COPYING.txt for details

__all__ = ('toggleBookmark', 'listBookmarks', 'nextBookmark', 'previousBookmark')


def toggleBookmark(ed):
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


def listBookmarks(ed):
	return list(ed.markers['bookmark'].listAll())
