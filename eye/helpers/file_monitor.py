# this project is licensed under the WTFPLv2, see COPYING.txt for details

from PyQt5.QtCore import QFileSystemWatcher, pyqtSignal, pyqtSlot
Signal = pyqtSignal
Slot = pyqtSlot

from logging import getLogger

from ..three import str
from ..connector import registerSignal, disabled

__all__ = ('Monitor', 'onOpen', 'onBeforeSave')


LOGGER = getLogger(__name__)

class Monitor(QFileSystemWatcher):
	def __init__(self, **kwargs):
		super(Monitor, self).__init__(**kwargs)
		self.fileChanged.connect(self.onFileChanged)
		# TODO WeakValueDictionary is enough? use signal instead of cb?
		self.watched = {}

	def addFile(self, path, cb):
		LOGGER.debug('start monitoring %r', path)
		self.addPath(path)
		self.watched[path] = cb
		# FIXME removePath when editor is closed

	def delFile(self, path):
		LOGGER.debug('stop monitoring %r', path)
		self.removePath(path)
		del self.watched[path]

	@Slot(str)
	def onFileChanged(self, path):
		#~ os.path.exists(path)
		# modification vs deletion/rename?
		cb = self.watched.get(path)
		if cb:
			cb()


@registerSignal('editor', 'fileOpened')
@registerSignal('editor', 'fileSavedAs')
@registerSignal('editor', 'fileSaved')
@disabled
def onOpen(editor, path):
	MONITOR.addFile(path, editor.fileModifiedExternally.emit)


@registerSignal('editor', 'fileAboutToBeSaved')
@disabled
def onBeforeSave(editor, path):
	if editor.path:
		MONITOR.delFile(editor.path)


MONITOR = Monitor()
