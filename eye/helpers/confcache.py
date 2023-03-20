# this project is licensed under the WTFPLv2, see COPYING.txt for details

from weakref import WeakValueDictionary

from PyQt5.QtCore import QObject

from eye.helpers.file_monitor import MonitorWithRename
from eye.qt import Slot


class ConfCache(QObject):
	def __init__(self, weak=True):
		super().__init__()

		if weak:
			self.cache = WeakValueDictionary()
		else:
			self.cache = {}  # pylint: disable=redefined-variable-type

		self.monitor = MonitorWithRename(parent=self)
		self.monitor.fileChanged.connect(self.on_file_changed)

	@Slot(str)
	def on_file_changed(self, path):
		"""Method called when a monitored file changes

		This method should be reimplemented by subclasses to reload a configuration object.

		When the cache stores weak-references, config objects may be deleted at anytime, but the associated
		file will stay monitored.
		A method reimplementation should check if the config still exists in cache before performing a costly
		file reload. See :any:`unmonitor_collected`.
		"""
		pass

	def unmonitor_collected(self, path=None):
		"""Stop monitoring file if the config object was garbage-collected.

		:param path: if None, verifies all monitored files
		:returns: True if `path` was unmonitored, else False. Meaningless if `path` is None.
		"""

		if path is None:
			for f in self.monitor.files():
				self.unmonitor_collected(f)
			return False
		else:
			if path in self.cache:
				return False
			self.monitor.removePath(path)
			return True

	def add_conf(self, path, conf):
		"""Add a config object to cache

		The config file `path` will be monitored for changes and the `conf` object will be added to cache.

		:param path: path of the config
		:param conf: the
		"""
		self.cache[path] = conf
		self.monitor.addPath(path)

	def del_conf(self, path):
		"""Remove a config from cache.

		The config file at `path` is also unmonitored.
		"""
		self.monitor.removePath(path)
		self.cache.pop(path, None)

	def get(self, path):
		"""Get the config object for path

		:returns: the config object in cache, or None if not found or the object was garbage-collected.
		"""
		return self.cache.get(path)

	# what about file (or parent dir) deletion monitoring?

# use cases: .editorconfig, builder config
# other: file list for filechooser?

# when to delete from cache? let users of confcache decide?
