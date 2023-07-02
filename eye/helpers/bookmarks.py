# this project is licensed under the WTFPLv2, see COPYING.txt for details

"""Line bookmarks

This plugin allows to set bookmark on lines. It's possible to navigate between bookmarked lines in a file.
Bookmarks do not persist when file is closed.

These bookmarks use a :any:`eye.widgets.editor.Marker` called "bookmark", which can be customized.

Here's a sample customization::

	@default_editor_config
	def setup_bookmarks(ed):
		ed.create_marker('bookmark', Marker(ed.Circle))
		ed.setMarkerBackgroundColor(QColor('#0000ff') , 'bookmark')
		ed.setMarkerForegroundColor(QColor('#cccccc') , 'bookmark')

"""


from eye.connector import default_editor_config, disabled
from eye.helpers.actions import register_action

__all__ = (
	'toggle_bookmark', 'next_bookmark', 'previous_bookmark', 'list_bookmarks',
	'create_marker', 'set_enabled',
)


@register_action('editor', 'toggle_bookmark')
def toggle_bookmark(ed):
	"""Toggle bookmark state of current line of editor."""

	if 'bookmark' not in ed.markers:
		create_marker(ed)

	ln = ed.getCursorPosition()[0]

	marker = ed.markers['bookmark']
	if marker.is_at(ln):
		marker.remove_at(ln)
	else:
		marker.put_at(ln)


def next_bookmark(ed):
	"""Jump to next bookmarked line in editor."""

	ln = ed.getCursorPosition()[0]

	ln = ed.markers['bookmark'].get_next(ln)
	if ln < 0:
		ln = ed.markers['bookmark'].get_next(0)
	ed.setCursorPosition(ln, 0)


def previous_bookmark(ed):
	"""Jump to previous bookmarked line in editor."""

	ln = ed.getCursorPosition()[0]

	ln = ed.markers['bookmark'].get_previous(ln)
	if ln < 0:
		ln = ed.markers['bookmark'].get_previous(ed.lines())


def list_bookmarks(ed):
	"""Return bookmarked lines numbers in editor."""

	return list(ed.markers['bookmark'].list_all())


@default_editor_config
@disabled
def create_marker(ed):
	"""Default handler to create a marker style for bookmarks.

	The default marker style is a circle without colors set.
	"""

	ed.create_marker('bookmark', ed.Circle)


def set_enabled(enabled):
	create_marker.enabled = enabled
