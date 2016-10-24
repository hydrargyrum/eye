# this project is licensed under the WTFPLv2, see COPYING.txt for details

import mimetypes
import os

from PyQt5.QtCore import QTimer

from ...app import qApp
from ...structs import PropDict
from ...connector import registerSignal, disabled, categoryObjects
from .daemon import getDaemon, isDaemonAvailable


__all__ = ('ycmFiletype', 'feedOnLoad', 'feedOnSave', 'feedOnDaemonReady', 'feedOnChange')


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


def ycmFiletype(path):
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


@registerSignal('editor', 'fileOpened')
@registerSignal('editor', 'fileSavedAs')
@disabled
def feedOnLoad(editor, path):
	if not isDaemonAvailable():
		return

	editor.ycm = PropDict()
	editor.ycm.filetype = ycmFiletype(path)
	getDaemon().sendParse(path, editor.ycm.filetype, editor.text())


@registerSignal('editor', 'fileSaved')
@disabled
def feedOnSave(editor, path):
	if not isDaemonAvailable():
		return

	getDaemon().sendParse(path, editor.ycm.filetype, editor.text())


def _timeoutFeed():
	if not isDaemonAvailable():
		return

	editor = qApp().sender().parent()
	getDaemon().sendParse(editor.path, editor.ycm.filetype, editor.text())


@registerSignal('editor', 'textChanged')
@disabled
def feedOnChange(editor):
	if not isDaemonAvailable() or not editor.path:
		return

	if not hasattr(editor, 'ycmFeedTimer'):
		editor.ycmFeedTimer = QTimer(editor)
		editor.ycmFeedTimer.setSingleShot(True)
		editor.ycmFeedTimer.timeout.connect(_timeoutFeed)
	# reboot timer
	editor.ycmFeedTimer.start(FEED_ON_EDIT_PAUSE_MS)


@registerSignal('ycm_control', 'ready')
@disabled
def feedOnDaemonReady(ycm):
	for editor in categoryObjects('editor'):
		if editor.path:
			feedOnLoad(editor, editor.path)
