# this project is licensed under the WTFPLv2, see COPYING.txt for details

"""Helper for searching in multiple files, like recursive grep.

The `file_search` plugins allow to perform pattern search in multiple files and directories.

.. seealso::

	The abstract plugin is in :any:`eye.helpers.file_search_plugins.base`.
"""

import os

from ..connector import registerSignal, disabled
from ..reutils import qtEnumToCs, qreToPattern
from ..app import qApp
from .file_search_plugins.base import enabledPlugins, getPlugin
from .intent import sendIntent


__all__ = ('enabledPlugins', 'searchWithPlugin', 'searchStart',
           'setupLocationList', 'searchAndOpenFirstResult',
           'pluginOpenFirstResult')


@registerSignal('file_search_widget', 'returnPressed')
@disabled
def searchStart(search_widget):
	search_widget.results.clear()
	search_widget.results.setColumns(loc=True, snippet=True)

	qregex = search_widget.regexp()
	plugin_id = search_widget.selectedPlugin()
	find_root = search_widget.shouldFindRoot()

	ed = search_widget.window().currentBuffer()

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


def setupLocationList(plugin, loclist):
	plugin.started.connect(loclist.clear)
	plugin.found.connect(loclist.addItem)
	plugin.finished.connect(loclist.resizeAllColumns)


def searchAndOpenFirstResult(plugin_id, path, pattern):
	plugin = getPlugin(plugin_id)(parent=qApp())
	pluginOpenFirstResult(plugin)

	if os.path.isfile(path):
		root = os.path.dirname(path)
	else:
		root = path

	plugin.search(root, pattern)


def pluginOpenFirstResult(plugin):
	"""Connect a SearchPlugin to open automatically the first result

	When the :any:`plugin` has found a result, an `openEditor` intent is sent to
	open the first result.
	This function must be called before starting the search.
	"""

	def onFound(res):
		loc = (res['line'], res.get('col', 1))
		sendIntent(None, 'openEditor', path=res['path'], loc=loc, reason='file_search')

	plugin.found.connect(onFound)
	plugin.found.connect(plugin.interrupt)
	plugin.found.connect(plugin.found.disconnect)
	plugin.finished.connect(plugin.deleteLater)
