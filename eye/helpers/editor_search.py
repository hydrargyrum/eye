# this project is licensed under the WTFPLv2, see COPYING.txt for details

from contextlib import contextmanager
import re

from PyQt5.QtCore import QObject, QTimer, QElapsedTimer

from eye import structs
from eye.connector import registerSignal, CategoryMixin
from eye.helpers import buffers
from eye.qt import Signal, Slot
from eye.widgets import minibuffer
from eye.widgets.editor import HasWeakEditorMixin, SciModification

__all__ = ('openSearchLine', 'searchForward', 'searchBackward',
           'SearchObject', 'SearchProps', 'performSearch')


class SearchProps(structs.PropDict):
	def __init__(self, *, expr, isRe=False, caseSensitive=False, whole=False):
		super(SearchProps, self).__init__(
			expr=expr, isRe=isRe, caseSensitive=caseSensitive, whole=whole,
		)


def props_to_re(props):
	re_flags = 0
	if not props.caseSensitive:
		re_flags |= re.I

	if props.isRe:
		return re.compile(props.expr, re_flags)
	else:
		re_text = re.escape(props.expr)
		if props.whole:
			re_text = r'\b%s\b' % re_text
		return re.compile(re_text, re_flags)


class SearchObject(QObject, HasWeakEditorMixin, CategoryMixin):
	started = Signal()
	found = Signal(int, int)
	finished = Signal(int)

	def __init__(self, editor=None, indicatorName=None, props=None, **kwargs):
		super(SearchObject, self).__init__(**kwargs)
		self.editor = editor
		self.props = props

		self.indicator = editor.indicators.get(indicatorName)
		if not self.indicator:
			self.indicator = editor.createIndicator(indicatorName, 0)

		self.timer = QTimer(self)
		self.timer.timeout.connect(self._searchBatch)

		self.start_line = 0
		self.reobj = None

		self.editor.sciModified.connect(self.onModify)

		self.addCategory('search_object')

	@contextmanager
	def safeBatch(self):
		try:
			yield
		except:
			self.timer.stop()
			self.finished.emit(0)
			raise

	def searchAllPy(self, needOne=False):
		if not self.props.expr:
			return

		self.reobj = props_to_re(self.props)
		self.start_line = 0

		self.started.emit()

		with self.safeBatch():
			self.indicator.clear()
			self.timer.start()
			if needOne:
				self._searchBatch(needOne=True)

	@Slot()
	def _searchBatch(self, needOne=False):
		with self.safeBatch():
			start_time = QElapsedTimer()
			start_time.start()

			for self.start_line in range(self.start_line, self.editor.lines()):
				if not needOne and start_time.hasExpired(10):
					return

				matched = self.searchInLine(self.start_line)
				if matched:
					needOne = False

			self.timer.stop()
			self.finished.emit(0)

	def searchInLine(self, lineno, erase_indicator=False):
		if erase_indicator:
			self.indicator.removeAt(lineno, 0, lineno + 1, 0)

		matched = False
		linetext = self.editor.text(lineno)
		for mtc in self.reobj.finditer(linetext):
			offset_start = self.editor.positionFromLineIndex(lineno, mtc.start())
			offset_end = self.editor.positionFromLineIndex(lineno, mtc.end())
			self.indicator.putAtOffset(offset_start, offset_end)
			self.found.emit(offset_start, offset_end)
			matched = True
		return matched

	def searchAll(self):
		self.indicator.clear()

		end = self.editor.bytesLength()
		self.editor.setTargetRange(0, end)

		self.started.emit()
		while True:
			if self.editor.searchInTarget(self.pops.expr) < 0:
				break

			self.indicator.putAtOffset(self.editor.targetStart(), self.editor.targetEnd())
			self.found.emit(self.editor.targetStart(), self.editor.targetEnd())
			self.editor.setTargetRange(self.editor.targetEnd(), end)
		self.finished.emit()

	@Slot(SciModification)
	def onModify(self, modif):
		if modif.modificationType & (self.editor.SC_MOD_INSERTTEXT | self.editor.SC_MOD_DELETETEXT):
			line_start, _ = self.editor.lineIndexFromPosition(modif.position)
			line_end, _ = self.editor.lineIndexFromPosition(modif.position + modif.length)
			for line in range(line_start, line_end + 1):
				self.searchInLine(line, erase_indicator=True)

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


def openSearchLine():
	minibuffer.openMiniBuffer(category='linesearch')

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

	performSearch(editor, SearchProps(expr=text), needOne=True)
	if not hasattr(editor, 'incSearchStart'):
		editor.incSearchStart = editor.cursorOffset()
	editor.searchObj.seekSelect(editor.incSearchStart)


def performSearch(editor, props, needOne=False):
	editor.searchObj = SearchObject(editor=editor, indicatorName='search', props=props)
	editor.searchObj.searchAllPy(needOne=needOne)


def performSearchSeek(editor, props):
	performSearch(editor, props, needOne=True)
	editor.searchObj.seekSelect(editor.cursorOffset())
	editor.incSearchStart = editor.cursorOffset()


@registerSignal('linesearch', 'textEntered')
def searchText(ls, text):
	if text is None:
		text = ls.text()

	editor = buffers.currentBuffer()
	if not editor:
		return

	performSearchSeek(editor, SearchProps(expr=text))


def _searchNext(editor, forward):
	if not hasattr(editor, 'searchObj'):
		return

	editor.searchObj.seekSelect(editor.cursorOffset(), forward=forward)
	editor.incSearchStart = editor.cursorOffset()


def searchForward(editor):
	_searchNext(editor, True)


def searchBackward(editor):
	_searchNext(editor, False)
