# this project is licensed under the WTFPLv2, see COPYING.txt for details

"""Helper for searching in multiple files, like recursive grep.

The `file_search` plugins allow to perform pattern search in multiple files and directories.

.. seealso::

	The abstract plugin is in :any:`eye.helpers.file_search_plugins.base`.
"""

import os

from eye.app import qApp
from eye.connector import register_signal, disabled
from eye.helpers.file_search_plugins.base import enabled_plugins, get_plugin
from eye.helpers.intent import send_intent
from eye.reutils import qtEnumToCs, qreToPattern

__all__ = (
	'enabled_plugins', 'searchWithPlugin', 'searchStart',
	'setupLocationList', 'searchAndOpenFirstResult',
	'pluginOpenFirstResult',
)


@register_signal('file_search_widget', 'returnPressed')
@disabled
def searchStart(search_widget):
	search_widget.results.clear()
	search_widget.results.setColumns(loc=True, snippet=True)

	qregex = search_widget.regexp()
	plugin_id = search_widget.selected_plugin()
	find_root = search_widget.shouldFindRoot()

	ed = search_widget.window().current_buffer()

	cs = qtEnumToCs(qregex.caseSensitivity())

	it = searchWithPlugin(plugin_id, ed.path, qreToPattern(qregex), find_root=find_root, caseSensitive=cs)
	for res in it:
		search_widget.results.addItem(res[0], loc=res[1], snippet=res[2])


def searchWithPlugin(plugin_id, path, pattern, find_root=False, **options):
	plugin = get_plugin(plugin_id)

	if find_root:
		root = plugin.search_root_path(path)
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
	plugin = get_plugin(plugin_id)(parent=qApp())
	pluginOpenFirstResult(plugin)

	if os.path.isfile(path):
		root = os.path.dirname(path)
	else:
		root = path

	plugin.search(root, pattern)


def pluginOpenFirstResult(plugin):
	"""Connect a SearchPlugin to open automatically the first result

	When the :any:`plugin` has found a result, an `open_editor` intent is sent to
	open the first result.
	This function must be called before starting the search.
	"""

	def onFound(res):
		loc = (res['line'], res.get('col', 1))
		send_intent(None, 'open_editor', path=res['path'], loc=loc, reason='file_search')

	plugin.found.connect(onFound)
	plugin.found.connect(plugin.interrupt)
	plugin.found.connect(plugin.found.disconnect)
	plugin.finished.connect(plugin.deleteLater)
