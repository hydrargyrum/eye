# this project is licensed under the WTFPLv2, see COPYING.txt for details

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot
Signal = pyqtSignal
Slot = pyqtSlot

import bisect
import re
import unittest

from ..connector import registerSignal, CategoryMixin
from ..widgets.editor import HasWeakEditorMixin
from ..widgets import minibuffer
from . import buffers


__all__ = ('SearchObject', 'openSearchLine')


class SearchObject(QObject, HasWeakEditorMixin, CategoryMixin):
	started = Signal()
	found = Signal(int, int)
	finished = Signal()

	def __init__(self, editor=None, indicatorName=None, **kwargs):
		super(SearchObject, self).__init__(**kwargs)
		self.editor = editor

		self.indicator = editor.indicators.get(indicatorName)
		if not self.indicator:
			self.indicator = editor.createIndicator(indicatorName, 0)

		self.addCategory('search_object')

	def searchAllPy(self, text):
		reobj = re.compile(text)

		cache = TextCache(self.editor.text())

		self.indicator.clear()
		self.started.emit()
		for mtc in reobj.finditer(cache.text):
			startl, startc = cache.lineIndexFromOffset(mtc.start())
			endl, endc = cache.lineIndexFromOffset(mtc.end())
			self.indicator.putAt(startl, startc, endl, endc)
			self.found.emit(mtc.start(), mtc.end())
		self.finished.emit()

	def searchAll(self, text):
		self.indicator.clear()

		end = self.editor.bytesLength()
		self.editor.setTargetRange(0, end)

		self.started.emit()
		while True:
			if self.editor.searchInTarget(text) < 0:
				break

			self.indicator.putAtOffset(self.editor.targetStart(), self.editor.targetEnd())
			self.found.emit(self.editor.targetStart(), self.editor.targetEnd())
			self.editor.setTargetRange(self.editor.targetEnd(), end)
		self.finished.emit()

	def getRanges(self):
		return list(self.indicator.iterRanges())

	def _seekForward(self, start, wrap):
		r = self.indicator.getNextRange(start)

		if r is None:
			if wrap:
				self._seekForward(0, wrap=False)
			return

		start, end, _ = r
		startl, startc = self.editor.lineIndexFromPosition(start)
		endl, endc = self.editor.lineIndexFromPosition(end)
		self.editor.setSelection(startl, startc, endl, endc)

	def _seekBackward(self, end, wrap):
		r = self.indicator.getPreviousRange(end)

		if r is None:
			if wrap:
				self._seekBackward(self.editor.bytesLength(), wrap=False)
			return

		start, end, _ = r
		startl, startc = self.editor.lineIndexFromPosition(start)
		endl, endc = self.editor.lineIndexFromPosition(end)
		self.editor.setSelection(endl, endc, startl, startc)

	def seekSelect(self, start=0, forward=True, wrap=True):
		if forward:
			self._seekForward(start, wrap)
		else:
			self._seekBackward(start, wrap)


class TextCache(object):
	def __init__(self, text):
		self.text = text
		self.lines = [0]

	def lineIndexFromOffset(self, pos):
		line = bisect.bisect(self.lines, pos) - 1
		if line + 1 >= len(self.lines):
			while pos > self.lines[-1]:
				newpos = self.text.find('\n', self.lines[-1])
				if newpos < 0:
					newpos = len(self.text)
				else:
					newpos += 1
				self.lines.append(newpos)

			line = bisect.bisect(self.lines, pos) - 1

		line_pos = self.lines[line]
		index = pos - line_pos
		return line, index


def openSearchLine():
	mb = minibuffer.openMiniBuffer(category='linesearch')

	editor = buffers.currentBuffer()
	if not editor:
		return
	editor.incSearchStart = editor.cursorOffset()


@registerSignal('linesearch', 'textEdited')
def onSearchTextEdited(ls, text):
	editor = buffers.currentBuffer()
	if not editor:
		return
	if not editor.search.get('incremental', False):
		return

	performSearch(editor, text)
	if not hasattr(editor, 'incSearchStart'):
		editor.incSearchStart = editor.cursorOffset()
	editor.searchObj.seekSelect(editor.incSearchStart)


def performSearch(editor, text):
	if not hasattr(editor, 'searchObj'):
		editor.searchObj = SearchObject(editor=editor, indicatorName='search')
	editor.searchObj.searchAllPy(text)


@registerSignal('linesearch', 'textEntered')
def searchText(ls, text):
	if text is None:
		text = ls.text()

	editor = buffers.currentBuffer()
	if not editor:
		return

	performSearch(editor, text)
	editor.searchObj.seekSelect(editor.cursorOffset())
	editor.incSearchStart = editor.cursorOffset()


class CacheTests(unittest.TestCase):
	def test_base(self):
		cache = TextCache(
"""01
3456
890
23
5
78
0""")
		self.assertEquals((0, 0), cache.lineIndexFromOffset(0))
		self.assertEquals((0, 1), cache.lineIndexFromOffset(1))
		self.assertEquals((1, 0), cache.lineIndexFromOffset(3))
		self.assertEquals((1, 2), cache.lineIndexFromOffset(5))
		self.assertEquals((2, 0), cache.lineIndexFromOffset(8))
		self.assertEquals((2, 1), cache.lineIndexFromOffset(9))
		self.assertEquals((2, 1), cache.lineIndexFromOffset(9))
		self.assertEquals((3, 0), cache.lineIndexFrom(Offset12))
		#~ self.assertEquals((3, 1), cache.lineIndexFromCp(0xD))
		self.assertEquals((4, 0), cache.lineIndexFromOffset(15))
		self.assertEquals((4, 0), cache.lineIndexFromOffset(15))
		self.assertEquals((6, 0), cache.lineIndexFromOffset(20))


if __name__ == '__main__':
	unittest.main()
