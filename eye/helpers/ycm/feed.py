# this project is licensed under the WTFPLv2, see COPYING.txt for details

import mimetypes
import os

from ...structs import PropDict
from ...connector import registerSignal, disabled, categoryObjects
from .daemon import getDaemon, isDaemonAvailable


__all__ = ('ycmFiletype', 'feedOnLoad', 'feedOnSave', 'feedOnDaemonReady')


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


@registerSignal('ycm_control', 'ready')
@disabled
def feedOnDaemonReady(ycm):
	for editor in categoryObjects('editor'):
		if editor.path:
			feedOnLoad(editor, editor.path)
