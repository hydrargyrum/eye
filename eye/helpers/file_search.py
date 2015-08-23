
import os

from .file_search_plugins.base import enabledPlugins, getPlugin

from ..reutils import csToQtEnum, qtEnumToCs, qreToPattern


def searchWithPlugin(plugin_id, path, pattern, find_root=False, **options):
	plugin = getPlugin(plugin_id)

	if find_root:
		root = plugin.searchRootPath(path)
	elif os.path.isfile(path):
		root = os.path.dirname(path)
	else:
		root = path

	return plugin.search(root, pattern, **options)
