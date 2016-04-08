# this project is licensed under the WTFPLv2, see COPYING.txt for details


__all__ = ('registerPlugin', 'SearchPlugin', 'enabledPlugins')


PLUGINS = {}


def registerPlugin(cls):
	PLUGINS[cls.id] = cls()


class SearchPlugin(object):
	def name(self):
		return self.id

	def isAvailable(self, path):
		raise NotImplementedError()

	def searchRootPath(self, path):
		raise NotImplementedError()

	def search(self, root, pattern, **options):
		raise NotImplementedError()


def getPlugin(plugin_id):
	return PLUGINS.get(plugin_id)


def enabledPlugins():
	for plugin in PLUGINS.values():
		if getattr(plugin, 'enabled', True):
			yield plugin
