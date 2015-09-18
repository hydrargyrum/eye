# this project is licensed under the WTFPLv2, see COPYING.txt for details

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.Qsci import *
Signal = pyqtSignal
Slot = pyqtSlot

import re
from weakref import ref

from ..app import qApp
from ..widgets.helpers import WidgetMixin
from ..widgets.minibuffer import openMiniBuffer, getMiniBuffer
from ..connector import registerSignal, disabled
from ..connector import registerShortcut
from ..colorutils import QColorAlpha


@registerSignal('editor', 'connected')
def setupHighlight(editor):
	indic = editor.createIndicator('searchHighlight', editor.StraightBoxIndicator)
	indic.setColor(QColorAlpha('#ff7700', 128))


@registerShortcut('editor', 'ctrl+f')
def searchCreate(ed):
	mb = openMiniBuffer(category='linesearch')

	mb.setText(ed.search.get('expr', ''))
	mb.editor = ref(ed)
	mb.selectAll()


@registerShortcut('linesearch', 'cancelled')
def cancelSearch(ls):
	pass


@registerSignal('linesearch', 'textEdited')
def onSearchTextEdited(ls, text):
	editor = ls.editor()
	if not editor:
		return
	if not editor.search.get('incremental', False):
		return
	searchText(ls, text)


@registerSignal('linesearch', 'textEntered')
def searchText(ls, text):
	editor = ls.editor()
	if not editor:
		return
	if text is None:
		text = ls.text()
	editor.find(text)


@registerShortcut('linesearch', Qt.Key_Up)
def searchPrevious(ls):
	editor = ls.editor()
	if not editor:
		return
	editor.findBackward()


@registerShortcut('linesearch', Qt.Key_Down)
def searchNext(ls):
	editor = ls.editor()
	if not editor:
		return
	editor.findForward()
