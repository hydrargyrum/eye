
import os

from ..connector import registerSignal, disabled, categoryObjects
from . import buffers

from .file_search_plugins.base import enabledPlugins, getPlugin

from ..reutils import csToQtEnum, qtEnumToCs, qreToPattern


__all__ = ('enabledPlugins', 'searchWithPlugin', 'resultActivated', 'searchStart')


@registerSignal('search_results', 'resultActivated')
@disabled
def resultActivated(widget, path, loc):
	buffers.openEditor(path, loc)


@registerSignal('file_search_widget', 'returnPressed')
@disabled
def searchStart(search_widget):
	search_widget.results.clear()
	search_widget.results.setColumns(loc=True, snippet=True)

	qregex = search_widget.regexp()
	plugin_id = search_widget.selectedPlugin()
	find_root = search_widget.shouldFindRoot()

	ed = search_widget.window().lastFocus

	cs = qtEnumToCs(qregex.caseSensitivity())

	it = searchWithPlugin(plugin_id, ed.path, qreToPattern(qregex), find_root=find_root, caseSensitive=cs)
	for res in it:
		search_widget.results.addItem(res[0], loc=res[1], snippet=res[2])


def searchWithPlugin(plugin_id, path, pattern, find_root=False, **options):
	plugin = getPlugin(plugin_id)

	if find_root:
		root = plugin.searchRootPath(path)
	elif os.path.isfile(path):
		root = os.path.dirname(path)
	else:
		root = path

	return plugin.search(root, pattern, **options)
