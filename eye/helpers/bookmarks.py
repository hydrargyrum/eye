# this project is licensed under the WTFPLv2, see COPYING.txt for details

"""Line bookmarks

This plugin allows to set bookmark on lines. It's possible to navigate between bookmarked lines in a file.
Bookmarks do not persist when file is closed.

These bookmarks use a :any:`eye.widgets.editor.Marker` called "bookmark", which can be customized.
"""

__all__ = ('toggleBookmark', 'nextBookmark', 'previousBookmark', 'listBookmarks',
           'createMarker', 'setEnabled')


from ..connector import defaultEditorConfig, disabled
from .actions import registerAction


@registerAction('editor', 'toggleBookmark')
def toggleBookmark(ed):
	if 'bookmark' not in ed.markers:
		createMarker(ed)

	ln = ed.getCursorPosition()[0]

	marker = ed.markers['bookmark']
	if marker.isAt(ln):
		marker.removeAt(ln)
	else:
		marker.putAt(ln)


def nextBookmark(ed):
        ln = ed.getCursorPosition()[0]

        ln = ed.markers['bookmark'].getNext(ln)
        if ln < 0:
                ln = ed.markers['bookmark'].getNext(0)
        ed.setCursorPosition(ln, 0)


def previousBookmark(ed):
        ln = ed.getCursorPosition()[0]

        ln = ed.markers['bookmark'].getPrevious(ln)
        if ln < 0:
                ln = ed.markers['bookmark'].getPrevious(ed.lines())


def listBookmarks(ed):
	return list(ed.markers['bookmark'].listAll())


@defaultEditorConfig
@disabled
def createMarker(ed):
	ed.createMarker('bookmark', ed.Circle)


def setEnabled(enabled):
	createMarker.enabled = enabled
