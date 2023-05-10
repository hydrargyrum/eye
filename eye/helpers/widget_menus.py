# this project is licensed under the WTFPLv2, see COPYING.txt for details

from logging import getLogger

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QAction, QMenu

from eye.connector import register_signal, register_setup


__all__ = (
	"make_entry", "make_separator", "make_submenu",
	"register_menu",
)


LOGGER = getLogger(__name__)

MENUS = {}


def make_separator(title=""):
	action = QAction()
	action.setSeparator(True)
	action.setText(title)
	return action


def make_entry(action_name, *, icon=None, title=None, checkable=False, data=None, shortcut=None):
	action = QAction(title or action_name)
	action.setObjectName(action_name)
	if icon:
		action.setIcon(icon or QIcon())
	if checkable:
		action.setCheckable(checkable)
	return action


def make_submenu(title, entries, *, icon=None):
	menu = QMenu()
	menu.setTitle(title)
	menu.setIcon(icon or QIcon())
	for entry in entries:
		menu.addAction(entry)
		entry.setParent(menu)

	# return the QMenu, not its menuAction(), because the reference to the QMenu would be lost
	# and the object would be deleted
	return menu


def merge_actions(widget_action, desc_action):
	result = QAction()
	result.setText(desc_action.text() or widget_action.text())
	result.setIcon(desc_action.icon() or widget_action.icon())
	result.setData(desc_action.data() or widget_action.data())
	result.setStatusTip(desc_action.statusTip() or widget_action.statusTip())
	result.setToolTip(desc_action.toolTip() or widget_action.toolTip())
	result.setWhatsThis(desc_action.whatsThis() or widget_action.whatsThis())
	result.setCheckable(widget_action.isCheckable())
	# don't do shortcut: it will be caught by widgetaction
	return result


def menu_desc_to_menu(menu_desc, widget, qmenu):
	for entry in menu_desc:
		if isinstance(entry, QMenu):
			# if setting the parent afterwards, the menu is not attached properly
			sub = QMenu(qmenu)

			sub.setTitle(entry.title())
			qmenu.addMenu(sub)
			menu_desc_to_menu(entry.actions(), widget, sub)
			continue

		if entry.isSeparator():
			if entry.text():
				qmenu.addSection(entry.text())
			else:
				qmenu.addSeparator()
			continue

		original_action = widget.findChild(QAction, entry.objectName())
		if original_action:
			target_slot = original_action.trigger
		else:
			target_slot = getattr(widget, entry.objectName(), None)
			if not target_slot:
				LOGGER.warning("no action or slot named %r", entry.objectName())
				continue

		new_action = merge_actions(original_action or QAction(), entry)
		new_action.triggered.connect(target_slot)

		qmenu.addAction(new_action)
		new_action.setParent(qmenu)


def show_context_menu(widget, pos):
	menu_desc = MENUS[next(iter(widget.categories()))]
	qmenu = QMenu()
	menu_desc_to_menu(menu_desc, widget, qmenu)
	widget.context_menu_pos = pos  # this may be useful in actions
	qmenu.exec(widget.mapToGlobal(pos))


def register_menu(category, description, stackoffset=0):
	decorator = register_signal(category, "customContextMenuRequested", stackoffset=1 + stackoffset)
	decorator(show_context_menu)

	@register_setup(category, stackoffset=1 + stackoffset)
	def use_custom_menu(widget):
		widget.setContextMenuPolicy(Qt.CustomContextMenu)

	MENUS[category] = description
