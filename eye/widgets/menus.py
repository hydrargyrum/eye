# this project is licensed under the WTFPLv2, see COPYING.txt for details

import re

from PyQt5.QtWidgets import QAction, QMenu, QMenuBar

__all__ = (
	"create_menu", "get_menu", "find_action",
	"text_without_mnemonics",
)


MenuType = QMenu | QMenuBar


def text_without_mnemonics(text: str) -> str:
	# &Foo -> Foo, F&&oo -> F&oo
	return re.sub("&(.)", r"\1", text)


def find_action(widget, text: str) -> QAction | None:
	text = text_without_mnemonics(text)

	for action in widget.actions():
		# TODO what about i18n?
		if text_without_mnemonics(action.text()) == text:
			return action


def create_menu(qmenu: MenuType, path: list[str]) -> QMenu:
	for title in path:
		action = find_action(qmenu, title)
		if not action:
			action = qmenu.addMenu(title).menuAction()

		qmenu = action.menu()

	return qmenu


def get_menu(qmenu: MenuType, path: list[str]) -> MenuType | None:
	for title in path:
		action = find_action(qmenu, title)
		if not action:
			return None

		qmenu = action.menu()

	return qmenu
