# this project is licensed under the WTFPLv2, see COPYING.txt for details

"""Plugin to save/restore session

The plugin will save open windows positions, splitters dispositions and open tabs and restore them.
"""

from binascii import hexlify, unhexlify
import json
import os

from ..connector import categoryObjects
from ..pathutils import getConfigFilePath
from ..widgets.window import Window
from ..widgets.splitter import Splitter
from ..widgets.tabs import TabWidget
from ..widgets.editor import Editor


__all__ = ('saveSession', 'restoreSession')


SESSION_FILE = 'last.session'


def bin_to_json(b):
	return hexlify(bytes(b)).decode('ascii')


def json_to_bin(j):
	return unhexlify(j)


def serializeSession():
	return {
		'windows': [serializeWindow(win) for win in categoryObjects('window')]
	}


def serializeWindow(win):
	return {
		'type': 'window',
		'qgeometry': bin_to_json(bytes(win.saveGeometry())),
		'qstate': bin_to_json(bytes(win.saveState())),
		'splitter': serializeSplitter(win.splitter.root),
	}


def serializeSplitter(splitter):
	assert isinstance(splitter, Splitter)

	items = [serializeSplitterEntry(splitter.widget(i)) for i in range(splitter.count())]
	return {
		'type': 'splitter',
		'orientation': splitter.orientation(),
		'qstate': bin_to_json(bytes(splitter.saveState())),
		'items': items,
	}


def serializeSplitterEntry(widget):
	if isinstance(widget, Splitter):
		return serializeSplitter(widget)
	elif isinstance(widget, TabWidget):
		return serializeTabs(widget)


def serializeTabs(tabwidget):
	assert isinstance(tabwidget, TabWidget)

	return {
		'type': 'tabwidget',
		'items': [serializeTab(tabwidget.widget(i)) for i in range(tabwidget.count())],
		'current': tabwidget.currentIndex(),
	}


def serializeTab(widget):
	if isinstance(widget, Editor):
		return {
			'type': 'editor',
			'path': widget.path,
			'cursor': list(widget.cursorLineIndex()),
			'contractedFolds': widget.contractedFolds(),
		}


def saveSession():
	obj = serializeSession()
	buf = json.dumps(obj)

	with open(getConfigFilePath(SESSION_FILE), 'w') as fd:
		fd.write(buf)


def respawnSessionObject(session):
	for dwin in session['windows']:
		win = Window()

		# restoreGeometry can fail with multiscreens if the window was maximized by a conf script
		win.showNormal()

		if 'qgeometry' in dwin:
			win.restoreGeometry(json_to_bin(dwin['qgeometry']))
		if 'qstate' in dwin:
			win.restoreState(json_to_bin(dwin['qstate']))

		respawnSplitter(dwin.get('splitter'), win.splitter.root)
		win.splitter.root.widget(0).setParent(None)
		resizeSplitter(dwin.get('splitter'), win.splitter.root)


def resizeSplitter(dsplitter, splitter):
	assert dsplitter['type'] == 'splitter'

	#splitter.setSizes(list(ditem['size'] for ditem in dsplitter['items']))
	if 'qstate' in dsplitter:
		splitter.restoreState(json_to_bin(dsplitter['qstate']))

	for i, ditem in enumerate(dsplitter['items']):
		if ditem['type'] == 'splitter':
			resizeSplitter(ditem, splitter.widget(i))


def respawnSplitter(dsplitter, splitter):
	assert dsplitter['type'] == 'splitter'
	assert isinstance(splitter, Splitter)

	splitter.setOrientation(dsplitter['orientation'])
	for ditem in dsplitter['items']:
		respawnSplitterItem(ditem, splitter)


def respawnSplitterItem(ditem, parent):
	if ditem['type'] == 'splitter':
		new = Splitter()
		parent.addWidget(new)
		respawnSplitter(ditem, new)
	elif ditem['type'] == 'tabwidget':
		new = TabWidget()
		parent.addWidget(new)
		respawnTabs(ditem, new)


def respawnTabs(dtabs, tabwidget):
	assert dtabs['type'] == 'tabwidget'

	for ditem in dtabs['items']:
		respawnTab(ditem, tabwidget)
	tabwidget.setCurrentIndex(dtabs.get('current', 0))


def respawnTab(dtab, tabwidget):
	if dtab['type'] == 'editor':
		new = Editor()
		tabwidget.addWidget(new)
		if dtab.get('path'):
			new.openFile(dtab['path'])
		if 'contractedFolds' in dtab:
			new.setContractedFolds(dtab['contractedFolds'])
		if 'cursor' in dtab:
			new.setCursorPosition(*dtab['cursor'])

def restoreSession():
	path = getConfigFilePath(SESSION_FILE)
	if not os.path.isfile(path):
		return

	with open(path) as fd:
		obj = json.load(fd)
	respawnSessionObject(obj)
