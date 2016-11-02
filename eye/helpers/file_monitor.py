# this project is licensed under the WTFPLv2, see COPYING.txt for details

from logging import getLogger
import os

from PyQt5.QtCore import QFileSystemWatcher

from ..three import str
from ..qt import Slot
from ..connector import registerSignal, disabled

__all__ = ('Monitor', 'onOpen', 'onBeforeSave')


LOGGER = getLogger(__name__)


class MonitorWithRename(QFileSystemWatcher):
	def __init__(self, **kwargs):
		super(MonitorWithRename, self).__init__(**kwargs)
		self.fileChanged.connect(self._checkRetrack)

	def addFile(self, path):
		LOGGER.debug('start monitoring %r', path)
		if not self.addPath(path):
			LOGGER.warning('failed to monitor %r', path)

	def removeFile(self, path):
		LOGGER.debug('stop monitoring %r', path)
		self.removePath(path)

	@Slot(str)
	def _checkRetrack(self, path):
		if path not in self.files():
			LOGGER.debug('file has been untracked: %r', path)
			if os.path.exists(path):
				self.addFile(path)


class Monitor(MonitorWithRename):
	def __init__(self, **kwargs):
		super(Monitor, self).__init__(**kwargs)
		self.fileChanged.connect(self.onFileChanged)
		# TODO WeakValueDictionary is enough? use signal instead of cb?
		self.watched = {}

	def addFileCallback(self, path, cb):
		self.addFile(path)
		self.watched[path] = cb
		# FIXME removePath when editor is closed

	def removeFile(self, path):
		super(Monitor, self).removeFile(path)
		del self.watched[path]

	@Slot(str)
	def onFileChanged(self, path):
		cb = self.watched.get(path)
		if cb:
			cb()


@registerSignal('editor', 'fileOpened')
@registerSignal('editor', 'fileSavedAs')
@registerSignal('editor', 'fileSaved')
@disabled
def onOpen(editor, path):
	MONITOR.addFileCb(path, editor.fileModifiedExternally.emit)


@registerSignal('editor', 'fileAboutToBeSaved')
@disabled
def onBeforeSave(editor, path):
	if editor.path:
		MONITOR.delFile(editor.path)


MONITOR = Monitor()
