# this project is licensed under the WTFPLv2, see COPYING.txt for details

"""Line bookmarks

This plugin allows to set bookmark on lines. It's possible to navigate between bookmarked lines in a file.
Bookmarks do not persist when file is closed.

These bookmarks use a :any:`eye.widgets.editor.Marker` called "bookmark", which can be customized.

Here's a sample customization::

	@defaultEditorConfig
	def setupBookmarks(ed):
        ed.createMarker('bookmark', Marker(ed.Circle))
		ed.setMarkerBackgroundColor(QColor('#0000ff') , 'bookmark')
		ed.setMarkerForegroundColor(QColor('#cccccc') , 'bookmark')

"""


from eye.connector import defaultEditorConfig, disabled
from eye.helpers.actions import registerAction

__all__ = ('toggleBookmark', 'nextBookmark', 'previousBookmark', 'listBookmarks',
           'createMarker', 'setEnabled')


@registerAction('editor', 'toggleBookmark')
def toggleBookmark(ed):
	"""Toggle bookmark state of current line of editor."""

	if 'bookmark' not in ed.markers:
		createMarker(ed)

	ln = ed.getCursorPosition()[0]

	marker = ed.markers['bookmark']
	if marker.isAt(ln):
		marker.removeAt(ln)
	else:
		marker.putAt(ln)


def nextBookmark(ed):
	"""Jump to next bookmarked line in editor."""

	ln = ed.getCursorPosition()[0]

	ln = ed.markers['bookmark'].getNext(ln)
	if ln < 0:
		ln = ed.markers['bookmark'].getNext(0)
	ed.setCursorPosition(ln, 0)


def previousBookmark(ed):
	"""Jump to previous bookmarked line in editor."""

	ln = ed.getCursorPosition()[0]

	ln = ed.markers['bookmark'].getPrevious(ln)
	if ln < 0:
		ln = ed.markers['bookmark'].getPrevious(ed.lines())


def listBookmarks(ed):
	"""Return bookmarked lines numbers in editor."""

	return list(ed.markers['bookmark'].listAll())


@defaultEditorConfig
@disabled
def createMarker(ed):
	"""Default handler to create a marker style for bookmarks.

	The default marker style is a circle without colors set.
	"""

	ed.createMarker('bookmark', ed.Circle)


def setEnabled(enabled):
	createMarker.enabled = enabled
