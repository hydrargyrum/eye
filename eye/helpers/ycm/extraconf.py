# this project is licensed under the WTFPLv2, see COPYING.txt for details

from __future__ import print_function

import os

from PyQt5.QtWidgets import QMessageBox

from ...connector import disabled
from ...pathutils import get_config_file_path
from ..intent import register_intent_listener


__all__ = ('query_extra_conf_use_conf', 'query_extra_conf_dialog', 'CONF_ACCEPT', 'CONF_REJECT')


CONF_ACCEPT = 'ycm.extra.accept.conf'
CONF_REJECT = 'ycm.extra.reject.conf'


def is_in_file(expected, path):
	if os.path.exists(path):
		with open(path) as fd:
			for line in fd:
				line = line.strip()
				if line.startswith('#'):
					continue
				if line == expected:
					return True
	return False


def add_to_file(line, path):
	with open(path, 'a') as fd:
		print(line, file=fd)


@register_intent_listener('query_extra_conf')
@disabled
def query_extra_conf_use_conf(source, ev, default_reject=True):
	ycmpath = ev.info['conf']
	if is_in_file(ycmpath, get_config_file_path(CONF_ACCEPT)):
		ev.accept(True)
		return True

	if default_reject or is_in_file(ycmpath, get_config_file_path(CONF_REJECT)):
		ev.accept(False)
		return True

	return False


@register_intent_listener('query_extra_conf')
@disabled
def query_extra_conf_dialog(source, ev):
	if query_extra_conf_use_conf(source, ev, default_reject=False):
		return True

	ycmpath = ev.info['conf']

	title = 'Allow YouCompleteMe extra conf?'
	text = 'Load %r? This may be a security risk if the file comes from an untrusted source.' % ycmpath
	dlg = QMessageBox(QMessageBox.Question, title, text)
	bOkOnce = dlg.addButton('Load once', QMessageBox.AcceptRole)
	bOkAlways = dlg.addButton('Load always', QMessageBox.AcceptRole)
	bNoOnce = dlg.addButton('Reject once', QMessageBox.RejectRole)
	bNoAlways = dlg.addButton('Reject always', QMessageBox.RejectRole)
	dlg.setDefaultButton(bNoOnce)
	dlg.setEscapeButton(bNoOnce)
	dlg.exec_()

	clicked = dlg.clickedButton()
	if clicked in (bOkOnce, bOkAlways):
		if clicked is bOkAlways:
			add_to_file(ycmpath, get_config_file_path(CONF_ACCEPT))
		ev.accept(True)
		return True
	elif clicked in (bNoOnce, bNoAlways):
		if clicked is bNoAlways:
			add_to_file(ycmpath, get_config_file_path(CONF_REJECT))
		ev.accept(False)
		return True

	return False
