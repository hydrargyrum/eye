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
from eye.reutils import qt_enum_to_cs, qre_to_pattern

__all__ = (
	'enabled_plugins', 'search_with_plugin', 'search_start',
	'setup_location_list', 'search_and_open_first_result',
	'plugin_open_first_result',
)


@register_signal('file_search_widget', 'returnPressed')
@disabled
def search_start(search_widget):
	search_widget.results.clear()
	search_widget.results.set_columns(loc=True, snippet=True)

	qregex = search_widget.regexp()
	plugin_id = search_widget.selected_plugin()
	find_root = search_widget.should_find_root()

	ed = search_widget.window().current_buffer()

	cs = qt_enum_to_cs(qregex.caseSensitivity())

	it = search_with_plugin(plugin_id, ed.path, qre_to_pattern(qregex), find_root=find_root, caseSensitive=cs)
	for res in it:
		search_widget.results.addItem(res[0], loc=res[1], snippet=res[2])


def search_with_plugin(plugin_id, path, pattern, find_root=False, **options):
	plugin = get_plugin(plugin_id)

	if find_root:
		root = plugin.search_root_path(path)
	elif os.path.isfile(path):
		root = os.path.dirname(path)
	else:
		root = path

	return plugin.search(root, pattern, **options)


def setup_location_list(plugin, loclist):
	plugin.started.connect(loclist.clear)
	plugin.found.connect(loclist.add_item)
	plugin.finished.connect(loclist.resize_all_columns)


def search_and_open_first_result(plugin_id, path, pattern):
	plugin = get_plugin(plugin_id)(parent=qApp())
	pluginOpenFirstResult(plugin)

	if os.path.isfile(path):
		root = os.path.dirname(path)
	else:
		root = path

	plugin.search(root, pattern)


def plugin_open_first_result(plugin):
	"""Connect a SearchPlugin to open automatically the first result

	When the :any:`plugin` has found a result, an `open_editor` intent is sent to
	open the first result.
	This function must be called before starting the search.
	"""

	def on_found(res):
		loc = (res['line'], res.get('col', 1))
		send_intent(None, 'open_editor', path=res['path'], loc=loc, reason='file_search')

	plugin.found.connect(on_found)
	plugin.found.connect(plugin.interrupt)
	plugin.found.connect(plugin.found.disconnect)
	plugin.finished.connect(plugin.deleteLater)
