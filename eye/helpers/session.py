# this project is licensed under the WTFPLv2, see COPYING.txt for details

"""Plugin to save/restore session

The plugin will save open windows positions, splitters dispositions and open tabs and restore them.
"""

from binascii import hexlify, unhexlify
import json
import os

from eye.connector import category_objects
from eye.pathutils import get_config_file_path
from eye.widgets.editor import Editor
from eye.widgets.splitter import Splitter
from eye.widgets.tabs import TabWidget
from eye.widgets.window import Window

__all__ = ('save_session', 'restore_session')


SESSION_FILE = 'last.session'


def bin_to_json(b):
	return hexlify(bytes(b)).decode('ascii')


def json_to_bin(j):
	return unhexlify(j)


def serialize_session():
	return {
		'windows': [serialize_window(win) for win in category_objects('window')]
	}


def serialize_window(win):
	return {
		'type': 'window',
		'qgeometry': bin_to_json(bytes(win.saveGeometry())),
		'qstate': bin_to_json(bytes(win.saveState())),
		'splitter': serialize_splitter(win.splitter.root),
	}


def serialize_splitter(splitter):
	assert isinstance(splitter, Splitter)

	items = [serialize_splitter_entry(splitter.widget(i)) for i in range(splitter.count())]
	return {
		'type': 'splitter',
		'orientation': splitter.orientation(),
		'qstate': bin_to_json(bytes(splitter.saveState())),
		'items': items,
	}


def serialize_splitter_entry(widget):
	if isinstance(widget, Splitter):
		return serialize_splitter(widget)
	elif isinstance(widget, TabWidget):
		return serialize_tabs(widget)


def serialize_tabs(tabwidget):
	assert isinstance(tabwidget, TabWidget)

	return {
		'type': 'tabwidget',
		'items': [serialize_tab(tabwidget.widget(i)) for i in range(tabwidget.count())],
		'current': tabwidget.currentIndex(),
	}


def serialize_tab(widget):
	if hasattr(widget, "editor"):
		widget = widget.editor

	if isinstance(widget, Editor):
		return {
			'type': 'editor',
			'path': widget.path,
			'cursor': list(widget.cursorLineIndex()),
			'contractedFolds': widget.contractedFolds(),
		}


def save_session():
	obj = serialize_session()
	buf = json.dumps(obj)

	with open(get_config_file_path(SESSION_FILE), 'w') as fd:
		fd.write(buf)


def respawn_session_object(session):
	for dwin in session['windows']:
		win = Window()

		# restoreGeometry can fail with multiscreens if the window was maximized by a conf script
		win.showNormal()

		if 'qgeometry' in dwin:
			win.restoreGeometry(json_to_bin(dwin['qgeometry']))
		if 'qstate' in dwin:
			win.restoreState(json_to_bin(dwin['qstate']))

		respawn_splitter(dwin.get('splitter'), win.splitter.root)
		win.splitter.root.widget(0).setParent(None)
		resize_splitter(dwin.get('splitter'), win.splitter.root)


def resize_splitter(dsplitter, splitter):
	assert dsplitter['type'] == 'splitter'

	#splitter.setSizes(list(ditem['size'] for ditem in dsplitter['items']))
	if 'qstate' in dsplitter:
		splitter.restore_state(json_to_bin(dsplitter['qstate']))

	for i, ditem in enumerate(dsplitter['items']):
		if ditem['type'] == 'splitter':
			resize_splitter(ditem, splitter.widget(i))


def respawn_splitter(dsplitter, splitter):
	assert dsplitter['type'] == 'splitter'
	assert isinstance(splitter, Splitter)

	splitter.setOrientation(dsplitter['orientation'])
	for ditem in dsplitter['items']:
		respawn_splitter_item(ditem, splitter)


def respawn_splitter_item(ditem, parent):
	if ditem['type'] == 'splitter':
		new = Splitter()
		parent.addWidget(new)
		respawn_splitter(ditem, new)
	elif ditem['type'] == 'tabwidget':
		new = TabWidget()
		parent.add_widget(new)
		respawn_tabs(ditem, new)


def respawn_tabs(dtabs, tabwidget):
	assert dtabs['type'] == 'tabwidget'

	for ditem in dtabs['items']:
		respawn_tab(ditem, tabwidget)
	tabwidget.setCurrentIndex(dtabs.get('current', 0))


def respawn_tab(dtab, tabwidget):
	if dtab['type'] == 'editor':
		new = Editor()
		tabwidget.add_widget(new)
		if dtab.get('path'):
			new.open_file(dtab['path'])
		if 'contractedFolds' in dtab:
			new.setContractedFolds(dtab['contractedFolds'])
		if 'cursor' in dtab:
			new.setCursorPosition(*dtab['cursor'])


def restore_session():
	path = get_config_file_path(SESSION_FILE)
	if not os.path.isfile(path):
		return

	with open(path) as fd:
		obj = json.load(fd)
	respawn_session_object(obj)
