# this project is licensed under the WTFPLv2, see COPYING.txt for details

"""Helpers for monitoring changes to files.
"""

from logging import getLogger
import os
from weakref import WeakValueDictionary

from PyQt5.QtCore import QFileSystemWatcher, QSignalMapper, QObject

from eye.connector import register_signal, disabled
from eye.qt import Signal, Slot

__all__ = (
	'Monitor', 'MonitorWithRename', 'SingleFileWatcher',
	'on_open', 'on_before_save',
	'MONITOR',
)


LOGGER = getLogger(__name__)


class MonitorWithRename(QFileSystemWatcher):
	"""File monitoring tracking files overwritten by renames.

	Standard :any:`QFileSystemWatcher` tracks modifications to file but if a file is renamed
	over it (like the standard UNIX pseudo-atomic write pattern "write-then-rename"), the file
	is not tracked anymore.

	`MonitorWithRename` can detect this situation and will re-track a file if a renamed file
	has overwritten it.

	The `fileChanged` signal is emitted when a monitored file has been
	touched/modified/renamed/removed.
	"""
	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		self.fileChanged.connect(self._check_retrack)

	def addPath(self, path):
		"""Start monitoring file at `path`.

		See :any:`QFileSystemWatcher.addPath`
		"""
		LOGGER.debug('start monitoring %r', path)
		if not super().addPath(path):
			LOGGER.warning('failed to monitor %r', path)

	def removePath(self, path):
		"""Stop monitoring file at `path`.

		See :any:`QFileSystemWatcher.removePath`
		"""
		LOGGER.debug('stop monitoring %r', path)
		super().removePath(path)

	@Slot(str)
	def _check_retrack(self, path):
		if path not in self.files():
			LOGGER.debug('file has been untracked: %r', path)
			if os.path.exists(path):
				self.addPath(path)


class SingleFileWatcher(QObject):
	"""Watcher for a single file

	The :any:`modified` signal is emitted when the tracked file is modified.

	If the file is overwritten by a rename, the file is still tracked
	(see :any:`MonitorWithRename`)
	"""

	modified = Signal()

	"""modified() signal

	Emitted when the associated file has been touched/modified/renamed/removed.
	"""

	def __init__(self, path, **kwargs):
		super().__init__(**kwargs)

		self.path = path

		"""Path of the watched file"""


class Monitor(QObject):
	"""File monitor

	This monitor can be used to track single files
	"""

	def __init__(self, **kwargs):
		super().__init__(**kwargs)

		self.watched = WeakValueDictionary()
		self.del_mapper = QSignalMapper(self)
		self.del_mapper.mapped[str].connect(self.unmonitor_file)

		self.watcher = MonitorWithRename(parent=self)
		self.watcher.fileChanged.connect(self._on_file_changed)

	def monitor_file(self, path):
		"""Monitor a file and return an object that tracks only `path`

		:rtype: SingleFileWatcher
		:return: an object tracking `path`, the same object is returned if the method is called
		         with the same path.
		"""
		path = os.path.abspath(path)

		self.watcher.addPath(path)

		proxy = self.watched.get(path)
		if not proxy:
			proxy = SingleFileWatcher(path)
			proxy.destroyed.connect(self.del_mapper.map)
			self.del_mapper.setMapping(proxy, path)
			self.watched[path] = proxy

		return proxy

	@Slot(str)
	def unmonitor_file(self, path):
		"""Stop monitoring a file

		Since there is only one :any:`SingleFileWatcher` object per path, all objects monitoring
		`path` will not receive notifications anymore.
		To let only one object stop monitoring the file, simply disconnect its `modified` signal.
		When the :any:`SingleFileWatcher` object returned by method :any:`monitor_file` is
		destroyed, the file is automatically un-monitored.
		"""
		path = os.path.abspath(path)

		self.watcher.removePath(path)
		self.watched.pop(path, None)

	@Slot(str)
	def _on_file_changed(self, path):
		proxy = self.watched.get(path)
		if proxy:
			proxy.modified.emit()


@register_signal('editor', 'file_opened')
@register_signal('editor', 'file_saved_as')
@register_signal('editor', 'file_saved')
@disabled
def on_open(editor, path):
	"""Handler to start monitoring the file edited

	When the file is modified (not by `saveFile`), the
	:any:`eye.widgets.editor.Editor.fileModifiedExterally` signal will be emitted.
	"""
	if getattr(editor, 'file_monitor', None) is not None:
		return

	editor.file_monitor = MONITOR.monitor_file(path)
	editor.file_monitor.modified.connect(editor.file_modified_externally)


@register_signal('editor', 'file_about_to_be_saved')
@disabled
def on_before_save(editor, path):
	"""Handler to (temporarily) pause file monitor associated to `editor`.

	The file monitor created by :any:`on_open` has to be disabled to avoid the editor detecting its
	own saving.
	"""

	if getattr(editor, 'file_monitor', None) is None:
		return

	editor.file_monitor.modified.disconnect(editor.file_modified_externally)
	editor.file_monitor = None


MONITOR = Monitor()

"""Ready-to-use instance of :any:`Monitor`"""
