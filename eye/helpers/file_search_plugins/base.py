# this project is licensed under the WTFPLv2, see COPYING.txt for details

from PyQt5.QtCore import QObject, pyqtSignal as Signal

__all__ = ('registerPlugin', 'SearchPlugin', 'enabledPlugins')


PLUGINS = {}


def registerPlugin(cls):
	PLUGINS[cls.id] = cls
	return cls


class SearchPlugin(QObject):
	found = Signal(dict)
	finished = Signal(int)

	@classmethod
	def name(cls):
		return cls.id

	@classmethod
	def isAvailable(cls, path):
		raise NotImplementedError()

	@classmethod
	def searchRootPath(cls, path):
		raise NotImplementedError()

	def interrupt(self):
		pass

	def search(self, path, pattern, **options):
		raise NotImplementedError()


def getPlugin(plugin_id):
	return PLUGINS.get(plugin_id)


def enabledPlugins():
	for plugin in PLUGINS.values():
		if getattr(plugin, 'enabled', True):
			yield plugin
