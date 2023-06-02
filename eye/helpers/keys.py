# this project is licensed under the WTFPLv2, see COPYING.txt for details

"""
Shortcut keys file format
-------------------------

The format is based on INI format (parsed by :doc:`configparser`). The file describes shortcuts
for triggering actions or slots of objects belonging to categories (see :doc:`eye.connector`
for a description of categories).

The config file should contain sections, each section describing a category (named like the section).
Within a section, each key is an action name, and the value is the description of the shortcut triggering the action.

Shortcut description
''''''''''''''''''''

The shortcut description should be in a string format accepted by :doc:`QKeySequence`.
Examples:

* ``Ctrl+S``: a simple keyboard shortcut where the S key is pressed while the Control key is held
* ``Alt+Up``: another shortcut where the up arrow key is pressed while Alt is held
* ``Ctrl+G,B``: a more complex shortcut, where G should be pressed while Ctrl is held, then B is
  pressed with no other key held

Optionally, the shortcut description can be prefixed to describe the context in which the shortcut is accepted:

* ``widget:`` (the default): the shortcut is only recognized when the widget has focus
* ``children:``: the shortcut is recognized if the widget or a children widget has focus
* ``window:``: the shortcut is recognized when the window has focus
* ``application:``: the shortcut is recognized when the app has focus

.. TODO if "window" context, can shortcut be recognized by a narrower context?

File example
''''''''''''

Here's an example of a suitable ``keyboard.ini`` (see :any:`DEFAULT_KEYS_FILE`)::

	# this is a comment

	[editor]
	# when Ctrl+S is pressed while a widget with "editor" category has focus,
	# the saveFile slot of the editor is triggered
	save_file = Ctrl+S

	[location_list]
	# when Ctrl+P is pressed in the same window as a widget with the "location_list" widget,
	# the activateNext slot of the location_list is triggered
	activate_next = window:Ctrl+P
	activate_previous = window:Ctrl+Shift+P

	[window]
	# when Ctrl+N is pressed in any child or grandchild of a widget with "window" category,
	# the bufferNew slot of the window is triggered
	buffer_new = children:Ctrl+N
	buffer_close = children:Ctrl+W

Module contents
---------------
"""

from configparser import ConfigParser

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeySequence

from eye.helpers.actions import register_action_shortcut
from eye.pathutils import get_config_file_path

__all__ = ('load_keys_config', 'DEFAULT_KEYS_FILE')


DEFAULT_KEYS_FILE = 'keyboard.ini'

"""Default filename used by `loadKeysConfig`."""


def load_keys_config(path: str | None = None) -> None:
	"""Load keys config file.

	If path is ``None``, a file named :any:`DEFAULT_KEYS_FILE` will be looked for in the config
	directory.

	:param path: path of the keyboard configuration file
	"""

	if path is None:
		path = get_config_file_path(DEFAULT_KEYS_FILE)

	cfg = ConfigParser()
	cfg.optionxform = str
	cfg.read([path])

	for category in cfg.sections():
		for action_name in cfg.options(category):
			keystr = cfg.get(category, action_name)

			context = Qt.WidgetShortcut
			if keystr.startswith('widget:'):
				keystr = keystr.split(':', 1)[1]
			elif keystr.startswith('window:'):
				keystr = keystr.split(':', 1)[1]
				context = Qt.WindowShortcut
			elif keystr.startswith('children:'):
				keystr = keystr.split(':', 1)[1]
				context = Qt.WidgetWithChildrenShortcut
			elif keystr.startswith('application:'):
				keystr = keystr.split(':', 1)[1]
				context = Qt.ApplicationShortcut
			qks = QKeySequence(keystr)

			register_action_shortcut(category, action_name, qks, context)
