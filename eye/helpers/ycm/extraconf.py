# this project is licensed under the WTFPLv2, see COPYING.txt for details

from __future__ import print_function

import os

from PyQt5.QtWidgets import QMessageBox

from ...connector import disabled
from ...pathutils import getConfigFilePath
from ..intent import registerIntentListener


__all__ = ('queryExtraConfUseConf', 'queryExtraConfDialog', 'CONF_ACCEPT', 'CONF_REJECT')


CONF_ACCEPT = 'ycm.extra.accept.conf'
CONF_REJECT = 'ycm.extra.reject.conf'


def isInFile(expected, path):
	if os.path.exists(path):
		with open(path) as fd:
			for line in fd:
				line = line.strip()
				if line.startswith('#'):
					continue
				if line == expected:
					return True
	return False


def addToFile(line, path):
	with open(path, 'a') as fd:
		print(line, file=fd)


@registerIntentListener('queryExtraConf')
@disabled
def queryExtraConfUseConf(source, ev, defaultReject=True):
	ycmpath = ev.info['conf']
	if isInFile(ycmpath, getConfigFilePath(CONF_ACCEPT)):
		ev.accept(True)
		return True

	if defaultReject or isInFile(ycmpath, getConfigFilePath(CONF_REJECT)):
		ev.accept(False)
		return True

	return False


@registerIntentListener('queryExtraConf')
@disabled
def queryExtraConfDialog(source, ev):
	if queryExtraConfUseConf(source, ev, defaultReject=False):
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
			addToFile(ycmpath, getConfigFilePath(CONF_ACCEPT))
		ev.accept(True)
		return True
	elif clicked in (bNoOnce, bNoAlways):
		if clicked is bNoAlways:
			addToFile(ycmpath, getConfigFilePath(CONF_REJECT))
		ev.accept(False)
		return True

	return False
