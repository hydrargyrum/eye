# this project is licensed under the WTFPLv2, see COPYING.txt for details

import logging

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QAction

from ..connector import registerSignal


__all__ = ('registerActionSlot', 'registerActionShortcut')


LOGGER = logging.getLogger(__name__)


def setupActionSlot(obj, slotName):
	slot = getattr(obj, slotName)

	action = QAction(obj)
	action.setObjectName(slotName)
	obj.addAction(action)
	action.triggered.connect(slot)
	LOGGER.debug('registered action %r for %r', slotName, obj)

	return action


def registerActionSlot(categories, slotName):
	@registerSignal(categories, 'connected')
	def onObject(obj):
		action = obj.findChild(QAction, actionName, Qt.FindDirectChildrenOnly)
		if action:
			LOGGER.debug('%r (requested categories: %r) has already registered action %r', obj, categories, slotName)
		else:
			setupActionSlot(obj, slotName)


def registerActionShortcut(categories, actionName, keyseq, context=Qt.WidgetShortcut):
	@registerSignal(categories, 'connected')
	def onObject(obj):
		action = obj.findChild(QAction, actionName, Qt.FindDirectChildrenOnly)
		if not action:
			if hasattr(obj, actionName):
				action = setupActionSlot(obj, actionName)
			else:
				LOGGER.warning('%r (requested categories: %r) has no action %r', obj, categories, actionName)
				return

		qkeyseq = QKeySequence(keyseq)

		# disable actions with the same shortcut
		for child in obj.children():
			if isinstance(child, QAction):
				if child.shortcut() == qkeyseq:
					child.setShortcut(QKeySequence())

		action.setShortcut(qkeyseq)
		action.setShortcutContext(context)
