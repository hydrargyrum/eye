# this project is licensed under the WTFPLv2, see COPYING.txt for details

import mimetypes
import os

from PyQt5.QtCore import QTimer

from ...app import qApp
from ...structs import PropDict
from ...connector import register_signal, disabled, category_objects
from .daemon import get_daemon, is_daemon_available


__all__ = ('ycm_filetype', 'feed_on_load', 'feed_on_save', 'feed_on_daemon_ready', 'feed_on_change')


MIME_YCMFILETYPE = {
	'application/javascript': 'js',
	'text/x-chdr': 'c',
	'text/x-csrc': 'c',
	'text/x-c++hdr': 'cpp',
	'text/x-c++src': 'cpp',
	'text/x-python': 'python',
}

EXT_YCMFILETYPE = {
	'c': 'c',
	'cc': 'cpp',
	'cpp': 'cpp',
	'cs': 'cs',
	'go': 'go',
	'h': 'cpp',
	'hh': 'cpp',
	'hpp': 'cpp',
	'js': 'js',
	'py': 'python',
}

FEED_ON_EDIT_PAUSE_MS = 1000


def ycm_filetype(path):
	mime, _ = mimetypes.guess_type(path)
	try:
		return MIME_YCMFILETYPE[mime]
	except KeyError:
		pass

	_, dotext = os.path.splitext(path)
	ext = dotext[1:]
	try:
		return EXT_YCMFILETYPE[ext]
	except KeyError:
		return 'general'


@register_signal('editor', 'file_opened')
@register_signal('editor', 'file_saved_as')
@disabled
def feed_on_load(editor, path):
	if not is_daemon_available():
		return

	editor.ycm = PropDict()
	editor.ycm.filetype = ycm_filetype(path)
	get_daemon().send_parse(path, editor.ycm.filetype, editor.text())


@register_signal('editor', 'file_saved')
@disabled
def feed_on_save(editor, path):
	if not is_daemon_available():
		return
	if not getattr(editor, "ycm", None):
		return

	get_daemon().send_parse(path, editor.ycm.filetype, editor.text())


def _timeout_feed():
	if not is_daemon_available():
		return

	editor = qApp().sender().parent()
	get_daemon().send_parse(editor.path, editor.ycm.filetype, editor.text())


@register_signal('editor', 'textChanged')
@disabled
def feed_on_change(editor):
	if not is_daemon_available() or not editor.path:
		return

	if not hasattr(editor, 'ycm_feed_timer'):
		editor.ycm_feed_timer = QTimer(editor)
		editor.ycm_feed_timer.setSingleShot(True)
		editor.ycm_feed_timer.timeout.connect(_timeout_feed)
	# reboot timer
	editor.ycm_feed_timer.start(FEED_ON_EDIT_PAUSE_MS)


@register_signal('ycm_control', 'ready')
@disabled
def feed_on_daemon_ready(ycm):
	for editor in category_objects('editor'):
		if editor.path:
			feed_on_load(editor, editor.path)
