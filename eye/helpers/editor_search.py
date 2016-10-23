# this project is licensed under the WTFPLv2, see COPYING.txt for details

from contextlib import contextmanager
import logging
import re

from PyQt5.QtCore import QObject, QTimer, QElapsedTimer

from eye import structs
from eye.connector import register_signal, CategoryMixin
from eye.helpers import buffers
from eye.qt import Signal, Slot
from eye.widgets import minibuffer
from eye.widgets.editor import HasWeakEditorMixin, SciModification

__all__ = (
	'open_search_line', 'search_forward', 'search_backward',
	'SearchObject', 'SearchProps', 'perform_search'
)


LOGGER = logging.getLogger(__name__)


class SearchProps(structs.PropDict):
	def __init__(self, *, expr, is_re=False, case_sensitive=False, whole=False):
		super().__init__(
			expr=expr, is_re=is_re, case_sensitive=case_sensitive, whole=whole,
		)


def props_to_re(props):
	re_flags = 0
	if not props.case_sensitive:
		re_flags |= re.I

	if props.is_re:
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

	def __init__(self, editor=None, indicator_name=None, props=None, **kwargs):
		super().__init__(**kwargs)
		self.editor = editor
		self.props = props

		self.indicator = editor.indicators.get(indicator_name)
		if not self.indicator:
			self.indicator = editor.create_indicator(indicator_name, 0)

		self.timer = QTimer(self)
		self.timer.timeout.connect(self._search_batch)

		self.start_line = 0
		self.reobj = None

		self.editor.sci_modified.connect(self.on_modify)

		self.add_category('search_object')

	@contextmanager
	def safe_batch(self):
		try:
			yield
		except Exception:
			self.timer.stop()
			self.finished.emit(0)
			raise

	def search_all_py(self, need_one=False):
		if not self.props.expr:
			return

		self.reobj = props_to_re(self.props)
		self.start_line = 0

		self.started.emit()

		with self.safe_batch():
			self.indicator.clear()
			self.timer.start()
			if need_one:
				self._search_batch(need_one=True)

	@Slot()
	def _search_batch(self, need_one=False):
		with self.safe_batch():
			start_time = QElapsedTimer()
			start_time.start()

			for self.start_line in range(self.start_line, self.editor.lines()):
				if not need_one and start_time.hasExpired(10):
					return

				matched = self.search_in_line(self.start_line)
				if matched:
					need_one = False

			self.timer.stop()
			self.finished.emit(0)

	def search_in_line(self, lineno, erase_indicator=False):
		if erase_indicator:
			self.indicator.remove_at(lineno, 0, lineno + 1, 0)

		matched = False
		linetext = self.editor.text(lineno)
		for mtc in self.reobj.finditer(linetext):
			offset_start = self.editor.positionFromLineIndex(lineno, mtc.start())
			offset_end = self.editor.positionFromLineIndex(lineno, mtc.end())
			self.indicator.put_at_offset(offset_start, offset_end)
			self.found.emit(offset_start, offset_end)
			matched = True
		return matched

	def search_all(self):
		self.indicator.clear()

		end = self.editor.bytes_length()
		self.editor.setTargetRange(0, end)

		self.started.emit()
		while True:
			if self.editor.searchInTarget(self.pops.expr) < 0:
				break

			self.indicator.put_at_offset(self.editor.targetStart(), self.editor.targetEnd())
			self.found.emit(self.editor.targetStart(), self.editor.targetEnd())
			self.editor.setTargetRange(self.editor.targetEnd(), end)
		self.finished.emit()

	@Slot(SciModification)
	def on_modify(self, modif):
		if modif.modificationType & (self.editor.SC_MOD_INSERTTEXT | self.editor.SC_MOD_DELETETEXT):
			line_start, _ = self.editor.lineIndexFromPosition(modif.position)
			line_end, _ = self.editor.lineIndexFromPosition(modif.position + modif.length)
			for line in range(line_start, line_end + 1):
				self.search_in_line(line, erase_indicator=True)

	def get_ranges(self):
		return list(self.indicator.iter_ranges())

	def _seek_forward(self, start, wrap):
		r = self.indicator.get_next_range(start)

		if r is None:
			if wrap:
				self._seek_forward(0, wrap=False)
			return

		start, end, _ = r
		startl, startc = self.editor.lineIndexFromPosition(start)
		endl, endc = self.editor.lineIndexFromPosition(end)
		self.editor.setSelection(startl, startc, endl, endc)

	def _seek_backward(self, end, wrap):
		r = self.indicator.get_previous_range(end)

		if r is None:
			if wrap:
				self._seek_backward(self.editor.bytes_length(), wrap=False)
			return

		start, end, _ = r
		startl, startc = self.editor.lineIndexFromPosition(start)
		endl, endc = self.editor.lineIndexFromPosition(end)
		self.editor.setSelection(endl, endc, startl, startc)

	def seek_select(self, start=0, forward=True, wrap=True):
		if forward:
			self._seek_forward(start, wrap)
		else:
			self._seek_backward(start, wrap)

	def replace_selection(self, expr, is_re=False):
		sl, sc, el, ec = self.editor.getSelection()
		if sl < 0 or sl != el:
			LOGGER.debug('aborting replace on an empty or multiline selection')
			return False

		linetext = self.editor.text(sl)

		mtc = self.reobj.match(linetext[sc:ec])
		if not mtc:
			LOGGER.debug("aborting replace on a selection that doesn't match")
			return False

		if is_re:
			replacement = mtc.expand(expr)
		else:
			replacement = expr

		self.editor.replaceSelectedText(replacement)
		self.editor.setSelection(sl, sc, sl, sc + len(replacement))
		return True

	def replace_all(self, expr, is_re=False):
		#for start, end in self.g
		pass


def open_search_line():
	ls = minibuffer.open_mini_buffer(category='linesearch')

	editor = buffers.current_buffer()
	if not editor:
		return

	editor.inc_search_start = editor.cursor_offset()

	prev_expr = None
	if editor.hasSelectedText():
		prev_expr = editor.selectedText()
	else:
		if getattr(editor, "search_obj", None):
			# TODO: even better, keep other options
			prev_expr = editor.search_obj.props.expr

	if prev_expr:
		ls.setText(prev_expr)
		ls.selectAll()


@register_signal('linesearch', 'textEdited')
def on_search_text_edited(ls, text):
	editor = buffers.current_buffer()
	if not editor:
		return
	if not editor.search.get('incremental', False):
		return

	perform_search(editor, SearchProps(expr=text), need_one=True)
	if not hasattr(editor, 'inc_search_start'):
		editor.inc_search_start = editor.cursor_offset()
	editor.search_obj.seek_select(editor.inc_search_start)


def perform_search(editor, props, need_one=False):
	editor.search_obj = SearchObject(editor=editor, indicator_name='search', props=props)
	editor.search_obj.search_all_py(need_one=need_one)


def perform_search_seek(editor, props):
	perform_search(editor, props, need_one=True)
	editor.search_obj.seek_select(editor.cursor_offset())
	editor.inc_search_start = editor.cursor_offset()


@register_signal('linesearch', 'text_entered')
def search_text(ls, text):
	if text is None:
		text = ls.text()

	editor = buffers.current_buffer()
	if not editor:
		return

	perform_search_seek(editor, SearchProps(expr=text))


def _search_next(editor, forward):
	if not hasattr(editor, 'search_obj'):
		return

	editor.search_obj.seek_select(editor.cursor_offset(), forward=forward)
	editor.inc_search_start = editor.cursor_offset()


def search_forward(editor):
	_search_next(editor, True)


def search_backward(editor):
	_search_next(editor, False)
