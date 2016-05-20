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

The shortcut description should be in a string format accepted by :doc:`QKeySequence`. Examples: ``Ctrl+S``, ``Alt+Up``.
Optionnally, the shortcut description can be prefixed to describe the context in which the shortcut is accepted:

* ``widget:`` (the default): the shortcut is only recognized when the widget has focus
* ``children:``: the shortcut is recognized if the widget or a children widget has focus
* ``window:``: the shortcut is recognized when the window has focus
* ``application:``: the shortcut is recognized when the app has focus

.. TODO if "window" context, can shortcut be recognized by a narrower context?

Module contents
---------------
"""

from six.moves.configparser import ConfigParser

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeySequence

from ..three import str
from .actions import registerActionShortcut


__all__ = ('loadKeysConfig',)


def loadKeysConfig(path):
	"""Load keys config file."""
	cfg = ConfigParser()
	cfg.optionxform = str
	cfg.read([path])

	for category in cfg.sections():
		for actionName in cfg.options(category):
			keystr = cfg.get(category, actionName)

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

			registerActionShortcut(category, actionName, qks, context)
