# this project is licensed under the WTFPLv2, see COPYING.txt for details

from six.moves.configparser import ConfigParser

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeySequence

from ..three import str
from .actions import registerActionShortcut


__all__ = ('loadKeysConfig',)


def loadKeysConfig(path):
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
