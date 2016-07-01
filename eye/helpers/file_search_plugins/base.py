# this project is licensed under the WTFPLv2, see COPYING.txt for details

from PyQt5.QtCore import QObject, pyqtSignal as Signal

from ...three import str
from ...qt import Slot


__all__ = ('registerPlugin', 'SearchPlugin', 'enabledPlugins', 'getPlugin')


PLUGINS = {}


def registerPlugin(cls):
	"""Decorator to register a file_search plugin class

	The plugin class should inherit :any:`SearchPlugin`.
	The plugin class can then be retrieved with :any:`getPlugin`.
	"""
	PLUGINS[cls.id] = cls
	return cls


class SearchPlugin(QObject):
	"""Search plugin abstract class"""

	started = Signal()

	"""Signal started()

	The signal is emitted when the search starts
	"""

	found = Signal(dict)

	"""Signal found(res)

	The signal is emitted when a search result is found.

	:param res: the search a result
	:type res: dict

	`res` must have the following keys:

	* `"path"`: absolute path of the matching file
	* `"line"`: 1-based line number of the match

	The dict can have the following optional keys:

	* `"snippet"`: content of the line matching
	* `"col"`: 1-base column number of the match
	* `"shortpath"`
	"""

	finished = Signal(int)

	"""Signal finished(res)

	The signal is emitted when the search is finished and no more results are emitted.

	:param res: the search exit code, a non-zero value in case errors were encountered
	:type res: int
	"""

	id = None

	"""Class attribute, identifier of the plugin

	The identifier should be unique across plugin classes since this identifier is used for :any:`getPlugin`.
	"""

	enabled = True

	"""Whether the plugin is enabled"""

	@classmethod
	def name(cls):
		"""Get the name of the plugin"""
		return cls.id

	@classmethod
	def isAvailable(cls, path):
		"""Return whether the plugin can search inside a particular path

		Some plugins use an index (like git or etags) and can only search in certain paths.
		"""
		raise NotImplementedError()

	@classmethod
	def searchRootPath(cls, path):
		raise NotImplementedError()

	@Slot()
	def interrupt(self):
		"""Interrupt a running search"""
		pass

	@Slot(str, str)
	def search(self, path, pattern, **options):
		raise NotImplementedError()


def getPlugin(plugin_id):
	"""Get a registered plugin by its identifier

	:rtype: SearchPlugin

	See :any:`SearchPlugin.id` and :any:`registerPlugin`.
	"""
	return PLUGINS.get(plugin_id)


def enabledPlugins():
	"""Iterate on registered and enabled plugins

	:rtype: iter[SearchPlugin]
	"""
	for plugin in PLUGINS.values():
		if getattr(plugin, 'enabled', True):
			yield plugin
