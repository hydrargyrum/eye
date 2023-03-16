# this project is licensed under the WTFPLv2, see COPYING.txt for details

"""Editor widget


.. _positions:

Positions
---------

Positions in the text of an editor widget can be expressed in multiple ways.

First, the position of a character can be expressed as "line-index", which is the line and column of
that character, in terms of Unicode codepoints, with the `str` type.
Unless specified otherwise, line and column numbers start at 0 in EYE.

Another way, more low-level, is the byte offset of the byte in the byte text (with type `bytes`).
The internal byte encoding of the editor is UTF-8, regardless of the encoding of
the underlying disk file, which only intervenes when loading/saving.

Module contents
---------------
"""

from collections import namedtuple
import contextlib
from logging import getLogger
import os
import re
import unicodedata
from weakref import ref

from PyQt5.Qsci import QsciScintilla, QsciStyledText
from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QFileDialog, QMessageBox
import sip

from eye import structs, io
from eye.connector import disabled, register_event_filter
from eye.qt import Slot, Signal, override
from eye.widgets.helpers import CentralWidgetMixin, accept_if

__all__ = (
	'Editor', 'Marker', 'Indicator', 'Margin', 'BaseEditor', 'QsciScintilla', 'SciModification',
	'zoom_on_wheel'
)


LOGGER = getLogger(__name__)


class HasWeakEditorMixin:
	def __init__(self, editor=None, **kwargs):
		super().__init__(**kwargs)
		self.editor = editor

	@property
	def editor(self):
		if self.__editor is not None:
			return self.__editor()

	@editor.setter
	def editor(self, value):
		if value is None:
			self.__editor = None
		else:
			self.__editor = ref(value)


class Marker(HasWeakEditorMixin):
	"""Margin marker of an editor

	Markers are graphical symbols that can be added in the margin of editor widgets.
	For example, a marker can be used to indicate a breakpoint is present on a particular line of
	the file.

	In an editor, a Marker can be set or unset for multiple lines, in which cases the configured
	symbol will be shown in the margin of the lines where the marker has been set.

	Example::

		marker = editor.create_marker('breakpoint', editor.Circle)
		# declare a marker type called 'breakpoint' which will show a circle in the margin
		# the Marker instance can be retrieved if needed
		# marker = editor.markers['breakpoint']
		marker.putAt(2)  # marker is added at 3rd line
		marker.putAt(20)  # marker is added at 21st line

	A `Marker` is associated with an :any:`eye.widgets.editor.Editor`. An `Editor` can have multiple
	`Marker`s, each with an arbitrary name. A `Marker` has a symbol or pixmap configured and can
	then be put or removed for individual lines of the associated `Editor`.

	.. TODO max number, internal id
	"""

	def __init__(self, sym, editor=None, id=-1):
		super().__init__(editor=editor)
		self.sym = sym
		self.id = id
		if editor:
			self._create()

	def to_bit(self):
		"""Return the internal Scintilla marker id in this editor instance"""
		return 1 << self.id

	def _create(self, editor=None):
		if not self.editor:
			self.editor = editor

		if self.id < 0:
			if len(getattr(self.editor, 'free_markers', [])):
				self.id = self.editor.free_markers.pop()
			self.id = self.editor.markerDefine(self.sym, self.id)
			del self.sym

	def set_symbol(self, param):
		"""Change the visual symbol of the marker"""
		newid = self.editor.markerDefine(param, self.id)
		assert newid == self.id

	def put_at(self, line):
		"""Add a marker symbol of this type at `line`"""
		return self.editor.markerAdd(line, self.id)

	def remove_at(self, line):
		"""Remove marker of this type at `line` if present"""
		self.editor.markerDelete(line, self.id)

	def toggle_at(self, line):
		"""Toggle marker of this type at `line`"""
		if self.is_at(line):
			self.remove_at(line)
		else:
			self.put_at(line)

	def is_at(self, line):
		"""Return `True` if a marker of this type is present at `line`"""
		return self.to_bit() & self.editor.markersAtLine(line)

	def get_next(self, line):
		"""Return the line number of first line having this marker after `line`

		-1 is returned if there is no line with the marker after `line`.
		"""
		return self.editor.get_marker_next(line + 1, self.to_bit())

	def get_previous(self, line):
		"""Return the line number of first line having this marker before `line`

		-1 is returned if there is no line with the marker before `line`.
		"""
		return self.editor.get_marker_previous(line - 1, self.to_bit())

	def list_all(self):
		"""List all lines that have this marker set"""
		ln = -1
		while True:
			ln = self.editor.marker_find_next(ln + 1, self.to_bit())
			if ln < 0:
				return
			yield ln

	def set_background_color(self, color):
		"""Set background color of this marker type"""
		self.editor.setMarkerBackgroundColor(color, self.id)

	def set_color(self, color):
		"""Set foreground color of this marker type"""
		self.editor.setMarkerForegroundColor(color, self.id)


class Indicator(HasWeakEditorMixin):
	"""Text indicator

	An indicator styles parts of the text with some particular visual style. It can be used for
	example by a spellchecker to underline misspelled words, or to highlight search results.

	In an editor, an indicator can be set for multiple ranges of characters in the text content,
	which will then be displayed in the configured style.

	Additionally, a numeric value can be associated when putting the indicator on a range. This
	allows to do some kind of sub-indicators. Where the indicator is not set, the value is always 0.
	The default value where an indicator is set is 1.

	Example:

		indic = editor.create_indicator('highlight', editor.BoxIndicator)
		# declare an indicator named 'highlight' with a "box" style (the text will be surrounded by a box)
		# the Indicator instance can be retrieved later:
		# indic = editor.indicators['highlight']
		indic.putAt(0, 0, 1, 0) # the first line will be styled with this indicator

	Like :any:`eye.widgets.editor.Marker`, `Indicator`s are associated to an `Editor` and have an
	arbitrary name.
	There can be at most 40 different indicator types per editor widget.
	"""
	def __init__(self, style, editor=None, id=-1):
		super().__init__(editor=editor)
		self.style = style
		self.id = id
		if editor:
			self._create()

	def _create(self, editor=None):
		if not self.editor:
			self.editor = editor

		if self.id < 0:
			if len(getattr(self.editor, 'free_indicators', [])):
				self.id = self.editor.free_indicators.pop()
			self.id = self.editor.indicatorDefine(self.style, self.id)
			del self.style

	def get_at_offset(self, offset):
		"""Return the value of the indicator is present at byte `offset`

		If the indicator is not set at byte `offset`, 0 is returned, else the value of the indicator
		at this offset is returned.
		"""
		return self.editor.indicator_value_at(self.id, offset)

	def is_on_edge(self, offset):
		if offset == 0:
			return bool(self.get_at_offset(offset))
		else:
			return self.get_at_offset(offset) != self.get_at_offset(offset - 1)

	def get_previous_edge(self, offset):
		"""Return the offset of the first edge of this indicator before `offset`.

		If `offset` is inside a range of characters with this indicator set, the start of the range
		is returned. The returned start is inclusive: it is the first offset in the range.

		If `offset` is outside, the end of the previous range before `offset` is returned.
		The returned end is exclusive: it's the first offset outside the range.

		If there is no range before, -1 is returned.

		Example::

			>>> indicator.put_at_offset(4, 10)
			>>> indicator.get_previous_edge(12)
			10
			>>> indicator.get_previous_edge(10)
			4
			>>> indicator.get_previous_edge(4)
			-1
		"""
		if offset > 0:
			offset -= 1
			# in scintilla, 'end' always advances, but 'start' blocks...

		res = self.editor.indicator_start(self.id, offset)
		if res == 0 and not self.get_at_offset(0):
			return -1
		return res

	def get_previous_range(self, offset, expected=None):
		end = self.get_previous_edge(offset)
		if end < 0:
			return None

		while True:
			start = self.get_previous_edge(end)
			if start < 0:
				return None

			value = self.get_at_offset(start)
			if value and (expected is None or expected == value):
				return (start, end, value)

			end = start

	def get_next_edge(self, offset):
		"""Return the offset of the first edge of this indicator after `offset`.

		If `offset` is inside a range of characters with this indicator set, the end of the range is
		returned. The returned end is exclusive: it's the first offset outside the range.

		If `offset` is outside a range, the start of the next range after `offset` is returned.
		The returned start is inclusive: it is the first offset in the range.

		If there is no range after, -1 is returned.

		Example::

			>>> indicator.put_at_offset(4, 10)
			>>> indicator.get_next_edge(0)
			4
			>>> indicator.get_next_edge(4)
			10
			>>> indicator.get_next_edge(10)
			-1
		"""
		blen = self.editor.bytes_length()
		if offset == blen:
			return -1

		res = self.editor.indicator_end(self.id, offset)
		if res == 0:
			# 0 is returned when indicator is never set
			return -1
		elif res == blen and not self.get_at_offset(offset):
			# bytes_length() is returned after last range
			return -1
		return res

	def get_next_range(self, offset, expected=None):
		start = self.get_next_edge(offset)
		if start < 0:
			return None

		while True:
			end = self.get_next_edge(start)
			if end < 0:
				return None

			value = self.get_at_offset(start)
			if value and (expected is None or expected == value):
				return (start, end, value)

			start = end

	def get_current_range(self, offset):
		val = self.get_at_offset(offset)
		prev = self.get_previous_edge(offset)
		if self.get_at_offset(prev) != val:
			prev = offset
		next = self.get_next_edge(offset)
		return (prev, next, val)

	def iter_ranges(self):
		"""Return (start, end, value) tuples listing the ranges where the indicator is set.

		Returns an iterator of `(start, end, value)` range tuple. For each tuple, `start` (inclusive) and
		`end` (exclusive) are byte offsets. `value` is the value of the indicator in this range.
		"""
		ed_end = self.editor.bytes_length()

		start = 0
		value = self.get_at_offset(start)
		while start < ed_end:
			end = self.editor.indicator_end(self.id, start)
			if value > 0:
				yield (start, end, value)

			if end == 0:
				# the indicator is set nowhere
				break

			start = end
			value = self.get_at_offset(start)

	def iter_lines(self):
		ed_end = self.editor.bytes_length()

		start = 0
		value = self.get_at_offset(start)
		while start < ed_end:
			end = self.editor.indicator_end(self.id, start)
			if end == 0:
				# the indicator is set nowhere
				break

			if value > 0:
				linestart, _ = self.editor.lineIndexFromPosition(start)
				lineend, _ = self.editor.lineIndexFromPosition(end)
				yield from range(linestart, lineend + 1)

				start = self.editor.positionFromLineIndex(lineend + 1, 0)
			else:
				start = end
			value = self.get_at_offset(start)

	def put_at(self, line_from, index_from, line_to, index_to, value=1):
		"""Add the indicator to a range of characters (line-index based)

		The indicator is set from `(line_from, index_from)` (inclusive) to `(line_to, index_to)` (exclusive).
		In this range, the indicator will have `value`.
		"""
		self.editor.fillIndicatorRange(line_from, index_from, line_to, index_to, self.id, value)

	def put_at_offset(self, start, end, value=1):
		"""Add the indicator to a range of characters (byte offset based)

		:param start: start offset (inclusive)
		:param end: end offset (exclusive)
		:param value: in the range, indicator will have this value
		"""
		startl, startc = self.editor.lineIndexFromPosition(start)
		endl, endc = self.editor.lineIndexFromPosition(end)
		self.put_at(startl, startc, endl, endc, value)

	def remove_at(self, line_from, index_from, line_to, index_to):
		"""Remove the indicator from a range of characters (line-index based)

		The indicator is unset from `(lineFrom, indexFrom)` (inclusive) to `(lineTo, indexTo)`
		(exclusive).
		In this range, the indicator value will be reset to 0.
		"""
		self.editor.clearIndicatorRange(line_from, index_from, line_to, index_to, self.id)

	def remove_at_offset(self, start, end):
		"""Remove the indicator from a range of characters (byte offset based)

		In this range, the indicator value will be reset to 0.

		:param start: start offset (inclusive)
		:param end: end offset (exclusive)
		"""
		startl, startc = self.editor.lineIndexFromPosition(start)
		endl, endc = self.editor.lineIndexFromPosition(end)
		self.remove_at(startl, startc, endl, endc)

	def clear(self):
		"""Remove the indicator from all characters in the editor widget"""
		self.remove_at_offset(0, self.editor.bytes_length())

	def set_color(self, col):
		"""Set the color of the text marked by this indicator"""
		self.editor.setIndicatorForegroundColor(col, self.id)

	def set_outline_color(self, col):
		"""Set the outline color of the text marked by this indicator"""
		self.editor.setIndicatorOutlineColor(col, self.id)

	def set_style(self, style):
		"""Set the visual style of the text marked by this indicator

		:param style: the new visual style to use
		:type style: QsciScintilla.IndicatorStyle
		"""
		self.id = self.editor.indicatorDefine(style, self.id)

	def set_flags(self, flags):
		self.editor.set_indicator_flags(self.id, flags)

	def get_flags(self):
		return self.editor.indicator_flags(self.id)


class Margin(HasWeakEditorMixin):
	@staticmethod
	def NumbersMargin(editor=None):
		return Margin(editor, id=0)

	@staticmethod
	def SymbolMargin(editor=None):
		return Margin(editor, id=1)

	@staticmethod
	def FoldMargin(editor=None):
		return Margin(editor, id=2)

	def __init__(self, editor=None, id=3):
		super().__init__(editor=editor)
		self.id = id
		self.width = 0
		self.visible = True

	def _create(self, editor=None):
		if self.editor is None:
			self.editor = editor
		if self.editor:
			self.width = self.editor.marginWidth(self.id)

	def set_width(self, w):
		self.width = w
		if self.visible:
			self.show()

	def set_marker_types(self, names):
		bits = 0
		for name in names:
			bits |= self.editor.markers[name].to_bit()
		self.editor.setMarginMarkerMask(self.id, bits)

	def set_all_marker_types(self):
		self.editor.setMarginMarkerMask(self.id, (1 << 32) - 1)

	def set_text(self, line, txt):
		if isinstance(txt, (str, bytes)):
			self.editor.setMarginText(self.id, txt, 0)
		else:
			self.editor.setMarginText(self.id, txt)

	def show(self):
		self.visible = True
		self.editor.setMarginWidth(self.id, self.width)

	def hide(self):
		self.visible = False
		self.editor.setMarginWidth(self.id, 0)


def sci_prop(prop, expected_args):
	def func(self, *args):
		if len(args) != len(expected_args):
			raise TypeError("this function takes exactly %d argument(s)" % len(expected_args))
		for n, (arg, expected_type) in enumerate(zip(args, expected_args)):
			if not isinstance(arg, expected_type):
				raise TypeError("argument %d has unexpected type %r (expected %r)" %
				                (n + 1, type(arg).__name__, expected_type.__name__))
		return self.SendScintilla(prop, *args)
	return func


def sci_prop_2(prop):
	def func(self, arg1, arg2):
		return self.SendScintilla(prop, arg1, arg2)
	return func


def sci_prop_set(prop):
	def func(self, value):
		return self.SendScintilla(prop, value)
	return func

sci_prop_1 = sci_prop_set


def sci_prop_get(prop):
	def func(self):
		return self.SendScintilla(prop)
	return func

sci_prop_0 = sci_prop_get


def sipvoid_as_str(v):
	i = 1
	while True:
		s = v.asstring(i)
		if s[-1] == '\x00':
			return s[:-1]
		i += 1


SciModification = namedtuple(
	'SciModification',
	(
		'position', 'modificationType', 'text', 'length', 'linesAdded',
		'line', 'foldLevelNow', 'foldLevelPrev', 'token', 'annotationLinesAdded'
	)
)


_SelectionTuple = namedtuple(
	'Selection', ('anchor_line', 'anchor_index', 'caret_line', 'caret_index')
)

class Selection(_SelectionTuple):
	@property
	def anchor(self):
		return (self.anchor_line, self.anchor_index)

	@property
	def caret(self):
		return (self.caret_line, self.caret_index)

	@property
	def start(self):
		return min(self.anchor, self.caret)

	@property
	def end(self):
		return max(self.anchor, self.caret)


class BaseEditor(QsciScintilla):
	"""Editor class adding missing Scintilla features

	QsciScintilla is an incomplete wrapper to Scintilla, this class aims to add support for a few of
	the missing editor features.

	.. note:: This class should not be instanciated directly as it exists only to add editor widget
	          features and is thus considered low-level.
	          :any:`eye.widgets.editor.Editor` contains file-related features and should be used
	          instead.

	.. seealso::

		Since QsciScintilla is used as a base, the `QsciScintilla documentation
		<http://pyqt.sourceforge.net/Docs/QScintilla2/classQsciScintilla.html>`_ should also be
		consulted.
		The more low-level `Scintilla documentation <http://www.scintilla.org/ScintillaDoc.html>`_
		can also help, though more rarely.
	"""

	# selection

	SelectionStream = QsciScintilla.SC_SEL_STREAM

	"""Select a character stream between two offsets in the text.

	If the start offset and end offset are not on the same lines, the characters from the start
	offset to the end of its line are selected, plus the characters from the end offset to the start
	of its line, plus the lines in between are completely selected.
	"""

	SelectionRectangle = QsciScintilla.SC_SEL_RECTANGLE

	"""Select characters in a rectangle between two offsets in the text.

	On each line from the line of the start offset to the line of the end offset, only characters
	from the column of the start offset to end column of the end offset are selected, thus making a
	rectangle.
	"""

	SelectionLines = QsciScintilla.SC_SEL_LINES

	"""Select full lines between two offsets in the text.

	All characters of the lines between the start offset and end offset, included, are selected.
	"""

	SelectionThin = QsciScintilla.SC_SEL_THIN

	set_selection_mode = sci_prop_set(QsciScintilla.SCI_SETSELECTIONMODE)
	selection_mode = sci_prop_get(QsciScintilla.SCI_GETSELECTIONMODE)

	set_multiple_selection = sci_prop_set(QsciScintilla.SCI_SETMULTIPLESELECTION)

	"""setMultipleSelection(bool)

	Set if multiple ranges of characters can be selected. All ranges are selected in the same
	selection mode.
	"""

	multiple_selection = sci_prop_0(QsciScintilla.SCI_GETMULTIPLESELECTION)
	"""Return `True` if multiple selection is enabled"""

	set_additional_selection_typing = sci_prop(QsciScintilla.SCI_SETADDITIONALSELECTIONTYPING, (bool,))

	"""Set whether typing in a multi-selection should type in all selections.

	If set to `True`, when multiple regions are selected, typing or removing characters will act on
	all selections instead of the main selection only.
	"""

	additional_selection_typing = sci_prop_0(QsciScintilla.SCI_GETADDITIONALSELECTIONTYPING)

	"""Return True if typing operates on all selections.

	See :any:`set_additional_selection_typing`.
	"""

	selections_count = sci_prop_get(QsciScintilla.SCI_GETSELECTIONS)

	"""Return the number of selection ranges (if multiple selections are enabled, else 1)"""

	selections_empty = sci_prop_0(QsciScintilla.SCI_GETSELECTIONEMPTY)

	"""Return True if all selections are empty."""

	clear_selections = sci_prop_0(QsciScintilla.SCI_CLEARSELECTIONS)

	"""Deselect all selections."""

	set_main_selection = sci_prop(QsciScintilla.SCI_SETMAINSELECTION, (int,))

	"""Set the index of the main selection.

	When there are multiple selections, set the main selection to be the n-th selection.
	"""

	main_selection = sci_prop_0(QsciScintilla.SCI_GETMAINSELECTION)

	"""Return the main selection index."""

	def add_selection(self, line_from, index_from, line_to, index_to):
		"""Add a new selection (line-index based).

		The first selection should be set with :any:`setSelection`, and the next ones with this method.
		"""
		offset_from = self.positionFromLineIndex(line_from, index_from)
		offset_to = self.positionFromLineIndex(line_to, index_to)
		self.add_selection_offsets(offset_from, offset_to)

	add_selection_offsets = sci_prop_2(QsciScintilla.SCI_ADDSELECTION)

	"""Add a new selection (offset based).

	See :any:`add_selection`.
	"""

	drop_selection_n = sci_prop(QsciScintilla.SCI_DROPSELECTIONN, (int,))

	"""Deselect the n-th selection."""

	selection_n_caret = sci_prop(QsciScintilla.SCI_GETSELECTIONNCARET, (int,))

	"""Get the offset of the n-th selection's caret."""

	selection_nAnchor = sci_prop(QsciScintilla.SCI_GETSELECTIONNANCHOR, (int,))

	"""Get the offset of the n-th selection's anchor."""

	def get_selection_n(self, n):
		"""Get line-indexes of the n-th selection.

		Returns a 4-tuple with line-index of the anchor and line-index of the caret.
		Note that the caret may be before or after the anchor.

		:param n: index of the selection
		:type n: int
		:rtype: tuple[int, int, int, int]
		"""
		anchor = self.lineIndexFromPosition(self.selection_n_anchor(n))
		caret = self.lineIndexFromPosition(self.selection_n_caret(n))
		return Selection(anchor[0], anchor[1], caret[0], caret[1])

	set_multi_paste = sci_prop_1(QsciScintilla.SCI_SETMULTIPASTE)

	"""Set whether pasting in a multi-selection should paste in all selections

	If set to `True`, when multiple regions are selected, pasting will paste in all selections
	instead of the main selection only.
	"""

	multi_paste = sci_prop_0(QsciScintilla.SCI_GETMULTIPASTE)

	"""Return True if pasting operates on all selections.

	See :any:`setMultiPaste`.
	"""

	# virtual space
	VsNone = QsciScintilla.SCVS_NONE

	"""Virtual space after a line's end is not accessible"""

	VsRectangular = QsciScintilla.SCVS_RECTANGULARSELECTION

	"""Virtual space after a line's end is accessible with rectangular selection mode"""

	VsUser = QsciScintilla.SCVS_USERACCESSIBLE

	"""Virtual space after a line's end is accessible by user with cursor"""

	set_virtual_space_options = sci_prop_set(QsciScintilla.SCI_SETVIRTUALSPACEOPTIONS)

	"""Set options for virtual space after a line's end

	Should be an or-combination of one or more flags in :any:`VsNone`, :any:`VsRectangular`,
	:any:`VsUser`.
	"""

	virtual_space_options = sci_prop_get(QsciScintilla.SCI_GETVIRTUALSPACEOPTIONS)

	"""Get virtual space options

	See :any:`setVirtualSpaceOptions`.
	"""

	# character representation
	set_representation = sci_prop_2(QsciScintilla.SCI_SETREPRESENTATION)

	def get_representation(self, s):
		bufsize = self.SendScintilla(self.SCI_GETREPRESENTATION, s, b'') + 1
		if not bufsize:
			return []

		res = bytearray(bufsize)
		self.SendScintilla(self.SCI_GETREPRESENTATION, s, res)
		return bytes(res[:-1])

	def clear_representation(self, s):
		# for unknown reasons, s is passed as lParam instead of wParam, so force it
		self.SendScintilla(QsciScintilla.SCI_CLEARREPRESENTATION, s, b'')

	# fold
	FoldFlagLineBeforeExpanded = QsciScintilla.SC_FOLDFLAG_LINEBEFORE_EXPANDED
	FoldFlagLineBeforeContracted = QsciScintilla.SC_FOLDFLAG_LINEBEFORE_CONTRACTED
	FoldFlagLineAfterExpanded = QsciScintilla.SC_FOLDFLAG_LINEAFTER_EXPANDED
	FoldFlagLineAfterContracted = QsciScintilla.SC_FOLDFLAG_LINEAFTER_CONTRACTED
	FoldFlagLevelNumbers = QsciScintilla.SC_FOLDFLAG_LEVELNUMBERS
	FoldFlagLineState = QsciScintilla.SC_FOLDFLAG_LINESTATE

	set_fold_flags = sci_prop_set(QsciScintilla.SCI_SETFOLDFLAGS)
	set_fold_level = sci_prop(QsciScintilla.SCI_SETFOLDLEVEL, (int, int))

	"""Set fold level of a line

	Set fold level `arg2` for line `arg1`.
	"""

	get_fold_level = sci_prop(QsciScintilla.SCI_GETFOLDLEVEL, (int,))

	"""Get fold level of line `value`"""

	# macro
	_start_macro_record = sci_prop_0(QsciScintilla.SCI_STARTRECORD)
	_stop_macro_record = sci_prop_0(QsciScintilla.SCI_STOPRECORD)

	# undo
	def set_undo_collection(self, b):
		"""set_undo_collection(bool): set whether editing actions are collected in the undo buffer"""
		self.SendScintilla(QsciScintilla.SCI_SETUNDOCOLLECTION, int(b))

	undo_collection = sci_prop_0(QsciScintilla.SCI_GETUNDOCOLLECTION)

	"""undo_collection(): return whether editing actions are collected in the undo buffer"""

	empty_undo_buffer = sci_prop_0(QsciScintilla.SCI_EMPTYUNDOBUFFER)

	"""empty_undo_buffer(): empty the undo buffer"""

	add_undo_action = sci_prop_2(QsciScintilla.SCI_ADDUNDOACTION)

	"""add_undo_action(int, int): add a custom action to the undo buffer"""

	# markers
	_get_marker_previous = sci_prop(QsciScintilla.SCI_MARKERPREVIOUS, (int, int))
	_get_marker_next = sci_prop(QsciScintilla.SCI_MARKERNEXT, (int, int))

	# indicators
	indicator_value_at = sci_prop(QsciScintilla.SCI_INDICATORVALUEAT, (int, int))
	indicator_start = sci_prop(QsciScintilla.SCI_INDICATORSTART, (int, int))
	indicator_end = sci_prop(QsciScintilla.SCI_INDICATOREND, (int, int))
	_set_indicator_value = sci_prop(QsciScintilla.SCI_SETINDICATORVALUE, (int,))
	_set_indicator_current = sci_prop(QsciScintilla.SCI_SETINDICATORCURRENT, (int,))
	_fill_indicator_range = sci_prop(QsciScintilla.SCI_INDICATORFILLRANGE, (int, int))
	setIndicatorFlags = sci_prop_2(QsciScintilla.SCI_INDICSETFLAGS)
	indicatorFlags = sci_prop_1(QsciScintilla.SCI_INDICGETFLAGS)

	IndicatorFlagValueFore = getattr(QsciScintilla, 'SC_INDICFLAG_VALUEFORE', 1)

	# search
	set_target_start = sci_prop(QsciScintilla.SCI_SETTARGETSTART, (int,))
	target_start = sci_prop_0(QsciScintilla.SCI_GETTARGETSTART)
	set_target_end = sci_prop(QsciScintilla.SCI_SETTARGETEND, (int,))
	target_end = sci_prop_0(QsciScintilla.SCI_GETTARGETEND)
	set_target_range = sci_prop(QsciScintilla.SCI_SETTARGETRANGE, (int, int))
	_search_in_target = sci_prop(QsciScintilla.SCI_SEARCHINTARGET, (int, bytes))
	replace_target = sci_prop_2(QsciScintilla.SCI_REPLACETARGET)

	set_search_flags = sci_prop_set(QsciScintilla.SCI_SETSEARCHFLAGS)
	search_flags = sci_prop_0(QsciScintilla.SCI_GETSEARCHFLAGS)

	# caret
	CaretStyleInvisible = QsciScintilla.CARETSTYLE_INVISIBLE

	"""Caret is invisible"""

	CaretStyleLine = QsciScintilla.CARETSTYLE_LINE

	"""Caret is a vertical line between two characters"""

	CaretStyleBlock = QsciScintilla.CARETSTYLE_BLOCK

	"""Caret is a block enclosing the next character"""

	set_caret_style = sci_prop_set(QsciScintilla.SCI_SETCARETSTYLE)

	"""Set caret display style

	Should be one of :any:`CaretStyleInvisible`, :any:`CaretStyleLine`, :any:`CaretStyleBlock`.
	"""

	caret_style = sci_prop_get(QsciScintilla.SCI_GETCARETSTYLE)

	"""Get caret display style

	See :any:`set_caret_style`.
	"""

	set_caret_period = sci_prop_set(QsciScintilla.SCI_SETCARETPERIOD)

	"""Set caret blinking period in milliseconds"""

	caret_period = sci_prop_get(QsciScintilla.SCI_GETCARETPERIOD)

	"""Get caret blinking period in milliseconds"""

	# lexer
	set_lexer_property = sci_prop(QsciScintilla.SCI_SETPROPERTY, (bytes, bytes))

	"""set_lexer_property(bytes, bytes): set a lexer property (key/value)"""

	def lexer_property(self, prop):
		bufsize = self.SendScintilla(QsciScintilla.SCI_GETPROPERTY, prop, None) + 1
		if not bufsize:
			return []

		res = bytearray(bufsize)
		self.SendScintilla(QsciScintilla.SCI_GETPROPERTY, prop, res)
		return bytes(res[:-1])

	# text
	delete_range = sci_prop_2(QsciScintilla.SCI_DELETERANGE)

	"""Delete characters in byte offset range"""

	insert_bytes = sci_prop(QsciScintilla.SCI_INSERTTEXT, (int, bytes))

	"""Insert byte characters at byte offset"""

	position_relative = sci_prop(QsciScintilla.SCI_POSITIONRELATIVE, (int, int))

	"""Get byte-offset from byte-offset + number of characters"""

	# style

	def set_style_hotspot(self, style_id, b):
		"""setStyleHotspot(int, bool): set whether a style is a hotspot (like a link)"""
		self.SendScintilla(QsciScintilla.SCI_STYLESETHOTSPOT, style_id, int(b))

	get_style_hotspot = sci_prop(QsciScintilla.SCI_STYLEGETHOTSPOT, (int,))

	"""get_style_hotspot(int): get whether a style is a hotspot"""

	get_style_at = sci_prop_1(QsciScintilla.SCI_GETSTYLEAT)

	"""get_style_at(int): get style number at given byte position"""

	def __init__(self, **kwargs):
		super().__init__(**kwargs)

		self.SCN_MACRORECORD.connect(self.scn_macro)
		self.SCN_AUTOCCANCELLED.connect(self.scn_autoccancelled)

		self.free_markers = []
		self.markers = {}
		self.free_indicators = []
		self.indicators = {}
		self.margins = {}
		self.auto_comp_list_id = 0
		self._counter_sci_modified = 0

		self.create_margin('lines', Margin.NumbersMargin())
		self.create_margin('folding', Margin.FoldMargin())
		self.create_margin('symbols', Margin.SymbolMargin())

	## markers, indicators, margins
	def _create_mi(self, d, name, obj):
		if name in d:
			return d[name]
		d[name] = obj
		obj._create(editor=self)
		return obj

	def create_marker(self, name, marker=QsciScintilla.Circle):
		"""Create and return a Marker with name `name` and symbol `marker`"""
		if not isinstance(marker, Marker):
			marker = Marker(marker)
		return self._create_mi(self.markers, name, marker)

	def create_indicator(self, name, indicator=QsciScintilla.PlainIndicator):
		"""Create and return an Indicator with name `name` and style `indicator`"""
		if not isinstance(indicator, Indicator):
			indicator = Indicator(indicator)
		return self._create_mi(self.indicators, name, indicator)

	def create_margin(self, name, margin):
		return self._create_mi(self.margins, name, margin)

	def _dispose_mi(self, d, dfree, name):
		if name not in d:
			return
		dfree.append(d[name].id)
		del d[name]

	def dispose_marker(self, name):
		self._dispose_mi(self.markers, self.free_markers, name)

	def dispose_indicator(self, name):
		self._dispose_mi(self.indicators, self.free_indicators, name)

	## indicators
	def _indicator_to_id(self, indicator):
		if isinstance(indicator, Indicator):
			return indicator.id
		elif isinstance(indicator, (str, bytes)):
			return self.indicators[indicator].id
		return indicator

	def fillIndicatorRange(self, line_from, index_from, line_to, index_to, indic, value=1):
		indic = self._indicator_to_id(indic)
		if indic < 0:
			return QsciScintilla.fillIndicatorRange(self, line_from, index_from, line_to, index_to, indic)

		offset_start = self.positionFromLineIndex(line_from, index_from)
		offset_end = self.positionFromLineIndex(line_to, index_to)

		self._set_indicator_current(indic)
		self._set_indicator_value(value)
		self._fill_indicator_range(offset_start, offset_end - offset_start)

	def clearIndicatorRange(self, line_from, index_from, line_to, index_to, indic):
		indic = self._indicator_to_id(indic)
		return QsciScintilla.clearIndicatorRange(self, line_from, index_from, line_to, index_to, indic)

	## markers
	def _marker_to_id(self, marker):
		if isinstance(marker, (str, bytes)):
			return self.markers[marker].id
		elif isinstance(marker, Marker):
			return marker.id
		return marker

	def markerAdd(self, line, marker):
		"""Add marker with name/id `i` at line `ln`"""
		marker = self._marker_to_id(marker)
		return QsciScintilla.markerAdd(self, line, marker)

	def markerDelete(self, line, marker):
		"""Delete marker with name/id `i` from line `ln`"""
		marker = self._marker_to_id(marker)
		return QsciScintilla.markerDelete(self, line, marker)

	def setMarkerBackgroundColor(self, color, marker):
		"""Set background color `c` to marker with id/name `i`"""
		marker = self._marker_to_id(marker)
		return QsciScintilla.setMarkerBackgroundColor(self, color, marker)

	def setMarkerForegroundColor(self, color, marker):
		marker = self._marker_to_id(marker)
		return QsciScintilla.setMarkerForegroundColor(self, color, marker)

	def get_marker_previous(self, line, marker):
		marker = self._marker_to_id(marker)
		return self._get_marker_previous(line, marker)

	def get_marker_next(self, line, marker):
		marker = self._marker_to_id(marker)
		return self._get_marker_next(line, marker)

	## macros
	#~ @Slot('uint', 'unsigned long', object)
	def scn_macro(self, msg, lp, wp):
		if isinstance(wp, sip.voidptr):
			self.action_recorded.emit([msg, lp, sipvoid_as_str(wp)])
		else:
			self.action_recorded.emit([msg, lp, wp])

	def start_macro_record(self):
		"""Start recording macro

		Also emits `macro_record_started()`
		"""
		self._start_macro_record()
		self.macro_record_started.emit()

	def stop_macro_record(self):
		"""Stop recording macro

		Also emits `macro_record_stopped()`
		"""
		self._stop_macro_record()
		self.macro_record_stopped.emit()

	def replay_macro_action(self, action):
		"""Replay a macro action

		"""
		msg, lp, wp = action
		return self.SendScintilla(msg, lp, wp)

	def search_in_target(self, s):
		if isinstance(s, str):
			s = s.encode('utf-8')
		return self._search_in_target(len(s), s)

	## annotations
	def annotation_styled_text(self, line):
		"""Return styled text annotations of a line

		Each line can have annotations compound of multiple pieces of text styled differently.
		This method retrieves all text parts along with their styles of the annotations of `line`.

		It can be seen as the "get" counterpart of the :any:`annotate` function taking a list of
		:any:`QsciStyledText`.

		:rtype: list of `QsciStyledText`
		"""
		bufsize = self.SendScintilla(self.SCI_ANNOTATIONGETTEXT, line, 0)
		if not bufsize:
			return []

		text = bytearray(bufsize)
		self.SendScintilla(self.SCI_ANNOTATIONGETTEXT, line, text)

		styles = bytearray(bufsize)
		self.SendScintilla(self.SCI_ANNOTATIONGETSTYLES, line, styles)

		oldn = 0
		oldst = styles[0]
		res = []
		for n, st in enumerate(styles):
			if oldst != st:
				part = text[oldn:n].decode('utf-8')
				res.append(QsciStyledText(part, oldst))
				oldn = n
				oldst = st
		part = text[oldn:].decode('utf-8')
		res.append(QsciStyledText(part, oldst))

		return res

	@Slot(int, int, 'const char*', int, int, int, int, int, int, int)
	def scn_modified(self, *args):
		self.sci_modified.emit(SciModification(*args))

	def connectNotify(self, sig):
		super().connectNotify(sig)
		if sig.name() == b'sciModified':
			self._counter_sci_modified += 1
			try:
				self.SCN_MODIFIED.connect(self.scn_modified, Qt.UniqueConnection)
			except TypeError: # prevent duplicating connection
				pass

	def disconnectNotify(self, sig):
		super().disconnectNotify(sig)
		if not sig.isValid():
			return
		if sig.name() == b'sciModified':
			self._counter_sci_modified -= 1
			assert self._counter_sci_modified >= 0
			if not self._counter_sci_modified:
				self.SCN_MODIFIED.disconnect(self.scn_modified)

	@Slot()
	def scn_autoccancelled(self):
		self.autoCompListId = 0

	def showUserList(self, id, items):
		self.autoCompListId = id
		super().showUserList(id, items)

	macro_record_started = Signal()

	"""Signal macro_record_started()

	After this signal is emitted, and until `macro_record_stopped()` is emitted, actions performed by
	user will be recorded and `action_recorded(object)` will be emitted for each action.
	"""

	macro_record_stopped = Signal()

	"""Signal macro_record_stopped()

	This signal is emitted when macro recording stops. `action_recorded()` will not be emitted any
	more after.
	"""

	action_recorded = Signal(object)

	"""Signal action_recorded(object): an action was recorded in macro

	The signal argument is the action recorded, and can be passed to `replay_macro_action` to replay
	this action.
	Internally, the action argument is a tuple suitable for Scintilla to process it.
	"""

	sci_modified = Signal(object)

	"""Signal sci_modified(object): a modification was done

	The signal argument is a 10-tuple describing the modification. The modifications signalled can
	be of various types.
	"""


class Editor(BaseEditor, CentralWidgetMixin):
	"""Editor widget class

	By default, instances of this class have the "editor" category set (see :doc:`eye.connector`
	for more info).

	.. seealso::

		Since QsciScintilla is used as a base, the `QsciScintilla documentation
		<http://pyqt.sourceforge.net/Docs/QScintilla2/classQsciScintilla.html>`_ should also be
		consulted.
	"""

	SmartCaseSensitive = object()

	def __init__(self, **kwargs):
		super().__init__(**kwargs)

		self.path = ''
		self.modificationChanged.connect(self.setWindowModified)
		self.modificationChanged.connect(self._update_title)
		self._update_title()

		self.saving = structs.PropDict()
		self.saving.trim_whitespace = False
		self.saving.final_newline = True
		self.saving.encoding = 'utf-8'
		self.setUtf8(True)
		# the editor is in utf-8 internally, encoding is done when saving

		self.search = structs.PropDict()
		self.search.incremental = True
		self.search.highlight = False
		self.search.is_re = False
		self.search.case_sensitive = False
		self.search.wrap = True
		self.search.whole = False

		self._lexer = None

		self.setWindowIcon(QIcon())

		self.add_category('editor')

	def __repr__(self):
		return '<Editor path=%r>' % self.path

	def _update_title(self):
		t = os.path.basename(self.path) or '<untitled>'
		if self.isModified():
			t = '%s*' % t

		self.setWindowTitle(t)
		self.setToolTip(self.path or '<untitled>')

	## file management
	def _get_filename(self):
		if not self.path:
			return ''
		return os.path.basename(self.path)

	@Slot()
	def save_file(self):
		"""Save edited file

		If no file path is set, a file dialog is shown to ask the user where to save content.
		"""
		path = self.path

		new_file = not path
		if new_file:
			path, qfilter = QFileDialog.getSaveFileName(self, self.tr('Save file'), os.path.expanduser('~'))
			if not path:
				return False
			path = path

		data = self._write_text(self.text())
		self.file_about_to_be_saved.emit(path)
		try:
			io.write_bytes_to_file(path, data)
		except OSError:
			LOGGER.error('cannot write file %r', path, exc_info=True)
			return False

		self.path = path
		self.setModified(False)
		if new_file:
			self.file_saved_as.emit(path)
		else:
			self.file_saved.emit(path)

		return True

	def close_file(self):
		"""Prepare for closing file and return `True` if modification state is clean

		If editor has no unsaved modifications, returns `True`. Else, ask user if modifications should be
		saved, then return `True` if accepted, else return `False`.
		"""
		ret = True

		if self.isModified():
			file = self.windowTitle()

			answer = QMessageBox.question(self, self.tr('Unsaved file'), self.tr('%s has been modified, do you want to close it?') % file, QMessageBox.Discard | QMessageBox.Cancel | QMessageBox.Save)
			if answer == QMessageBox.Discard:
				ret = True
			elif answer == QMessageBox.Cancel:
				ret = False
			elif answer == QMessageBox.Save:
				ret = self.save_file()
		return ret

	def _newline_string(self):
		modes = {
			QsciScintilla.SC_EOL_LF: '\n',
			QsciScintilla.SC_EOL_CR: '\r',
			QsciScintilla.SC_EOL_CRLF: '\r\n',
		}

		return modes.get(self.eolMode(), '\n')

	def _read_text(self, data):
		text = data.decode(self.saving.encoding)
		if self.saving.final_newline and text.endswith(self._newline_string()):
			text = text[:-1]
		return text

	def _remove_trailing_whitespace(self, text):
		return re.sub(r'[ \t]+$', '', text, flags=re.MULTILINE)

	def _write_text(self, text):
		if self.saving.trim_whitespace:
			text = self._remove_trailing_whitespace(text)
		if self.saving.final_newline:
			text += self._newline_string()
		return text.encode(self.saving.encoding)

	def open_file(self, path):
		if not self.close_file():
			return False

		path = os.path.abspath(path)
		self.path = path

		try:
			data = io.read_bytes_from_file(path)
		except OSError:
			LOGGER.error('cannot read file %r', path, exc_info=True)
			return False
		self.file_about_to_be_opened.emit(path)

		text = self._read_text(data)
		self.setText(text)
		self.setModified(False)
		self.file_opened.emit(path)
		return True

	def open_document(self, other):
		if not self.close_file():
			return False

		self.path = other.path
		self.setDocument(other.document())
		self.modificationChanged.emit(self.isModified())
		return True

	@Slot()
	def reload_file(self):
		"""Reload file contents (losing unsaved modifications)

		Reload file from disk and replace editor contents with updated text.
		If the user made modifications to the editor contents without saving them, calling this
		method will will lose them. However, the replacement can be undone by the user.
		"""
		old_pos = self.get_cursor_position()

		try:
			data = io.read_bytes_from_file(self.path)
		except OSError:
			LOGGER.error('cannot reload file %r', self.path, exc_info=True)
			return False
		text = self._read_text(data)

		with self.undo_group():
			# XXX setText would clear the history
			self.clear()
			self.insert(text)
		self.setModified(False)
		self.set_cursor_position(*old_pos)
		return True

	## various props
	def set_use_final_newline(self, b):
		"""Set whether a final newline should always be added when saving to disk

		If `b` is False, the contents of the editor won't be changed when saving file to disk: the
		file will only contain a final newline if the editor text ends with a newline.

		If `b` is True, a final newline will be added to the file saved on disk, but this final
		newline won't be shown in the editor. When the file is loaded, if it ends with a final
		newline, it won't be shown in the editor either, though will be kept when saving again.

		This does not cause the file to be re-saved.
		"""
		self.saving.final_newline = b

	def use_final_newline(self):
		"""Return True if always adding a final newline when saving.

		See :any:`set_use_final_newline`.
		"""
		return self.saving.final_newline

	def set_remove_trailing_whitespace(self, b):
		"""Set whether trailing whitespace should be trimmed when saving to disk

		If `b` is True, trailing whitespace will be removed from each line on the the file saved to
		disk. It is still kept in the editor though (but this behavior may change in the future).

		This does not cause the file to be re-saved.
		"""
		self.saving.trim_whitespace = b

	def does_remove_trailing_whitespace(self):
		"""Return True if always trimming trailing whitespace when saving.

		See :any:`set_remove_trailing_whitespace`.
		"""
		return self.saving.trim_whitespace

	def set_encoding(self, s):
		"""Set the file data encoding for loading/saving

		When loading file contents from disk or saving file to disk, this encoding will be used.
		This does not change the internal encoding used by the editor widget, which is utf-8.

		This does not cause the file to be re-saved.
		"""
		''.encode(s) # ensure it's usable
		self.saving.encoding = s

	def encoding(self):
		"""Return the encoding to use for loading/saving"""
		return self.saving.encoding

	## misc
	@contextlib.contextmanager
	def undo_group(self, undo_on_error=False):
		"""Context-manager to run actions in an undo-group.

		Operations done in this context manager are put in an undo-group: :any:`undo` and :any:`redo`
		will do them all-at-once. The undo-group is opened at the beginning of the context and
		automatically closed at the end of the context.
		For example, removing a whole word will appear the same, undo-wise, as removing the word
		character-by-character, if all characters are removed while an undo-group was open.

		:param undo_on_error: if an exception is raised inside the context, operations done in the group
		                    are undone
		:type undo_on_error: bool
		"""
		self.begin_undo_action()
		try:
			yield
		except Exception:
			self.end_undo_action()
			if undo_on_error:
				self.undo()
			raise
		self.end_undo_action()

	@Slot()
	def goto1(self, line, col=None):
		col = col or 1
		line, col = line - 1, col - 1
		self.ensureLineVisible(line)
		self.setCursorPosition(line, col)

	def cursor_line(self):
		"""Return the line number of the cursor position (starting from 0)"""
		return self.get_cursor_position()[0]

	def cursor_column(self):
		"""Return the column number of the cursor position (starting from 0)

		Note the column number is the number of Unicode codepoints since the start of the line.
		For example, a tab character will count for 1 column only, see :any:`cursor_visual_column`.
		"""
		return self.getCursorPosition()[1]

	def cursor_visual_column(self):
		lineno, colno = self.getCursorPosition()
		line = self.text(lineno)[:colno]
		line = line.expandtabs(self.tabWidth())
		# warning: scintilla seems to have bugs when using decomposed unicode
		return iterlen(c for c in line if not unicodedata.combining(c))

	def setLexer(self, lexer):
		QsciScintilla.setLexer(self, lexer)
		self._lexer = lexer
		self.lexer_changed.emit(lexer)

	def lexer(self):
		lexer = QsciScintilla.lexer(self)
		if lexer is None:
			lexer = self._lexer
		return lexer

	def cursor_position(self):
		"""Return the cursor line-index starting from 0

		.. note:: This function is misnamed in QsciScintilla and the naming is kept here to avoid more
		          confusion.

		See :ref:`positions`.
		"""
		return self.getCursorPosition()

	def cursor_line_index(self):
		"""Return the cursor line-index starting from 0

		See :ref:`positions`.
		"""
		return self.getCursorPosition()

	def cursor_offset(self):
		"""Return the cursor position in byte offset

		As this function returns a byte-offset, it should not be used unless necessary.
		See :ref:`positions`.
		"""
		return self.positionFromLineIndex(*self.getCursorPosition())

	def bytes_length(self):
		"""Return the length of the text in bytes"""
		return self.length()

	def text_length(self):
		"""Return the length of the text in Unicode codepoints"""
		return len(self.text())

	## search
	@classmethod
	def _smart_case(cls, txt, cs):
		if cs is cls.SmartCaseSensitive:
			return (txt.lower() != txt)
		else:
			return cs

	def _search_options_to_re(self):
		expr = self.search.expr if self.search.is_re else re.escape(self.search.expr)
		if self.search.whole:
			expr = '\b%s\b' % expr
		case_sensitive = self._smart_case(expr, self.search.case_sensitive)
		flags = 0 if case_sensitive else re.I
		return re.compile(expr, flags)

	def _highlight_search(self):
		txt = self.text()
		reobj = self._search_options_to_re()
		for mtc in reobj.finditer(txt):
			self.indicators['search_highlight'].put_at_offset(mtc.start(), mtc.end())

	def clear_search_highlight(self):
		self.indicators['search_highlight'].remove_at_offset(0, self.bytes_length())

	def find(self, expr, case_sensitive=None, is_re=None, whole=None, wrap=None):
		if self.search.highlight:
			self.clear_search_highlight()

		self.search.expr = expr
		if case_sensitive is not None:
			self.search.case_sensitive = case_sensitive
		if is_re is not None:
			self.search.is_re = is_re
		if whole is not None:
			self.search.whole = whole
		if wrap is not None:
			self.search.wrap = wrap
		self.search.forward = True

		case_sensitive = self._smart_case(expr, self.search.case_sensitive)

		if self.search.highlight:
			self._highlight_search()

		lfrom, ifrom, lto, ito = self.getSelection()
		self.setCursorPosition(*min([(lfrom, ifrom), (lto, ito)]))

		return self.findFirst(self.search.expr, self.search.is_re, case_sensitive, self.search.whole, self.search.wrap, True)

	def _find_in_direction(self, forward):
		if self.search.get('forward') == forward:
			return self.findNext()
		else:
			self.search.forward = forward
			case_sensitive = self._smart_case(self.search.expr, self.search.case_sensitive)
			b = self.findFirst(self.search.expr, self.search.is_re, case_sensitive, self.search.whole, self.search.wrap, self.search.forward)
			if b and not forward:
				# weird behavior when switching from forward to backward
				return self.findNext()
			return b

	def find_forward(self):
		return self._find_in_direction(True)

	def find_backward(self):
		return self._find_in_direction(False)

	def word_at_cursor(self):
		return self.wordAtLineIndex(*self.getCursorPosition())

	def word_at_pos(self, pos):
		return self.word_at_line_index(*self.line_index_from_position(pos))

	## annotations
	def annotate_append(self, line, item, style=None):
		"""Append a new annotation

		Add an annotation for `line`. If there was an existing annotation at this line, unlike
		:any:`annotate`, the old annotation is not overwritten, but the new annotation is appended
		to the old one.

		If `item` is a string, it should be the text of the annotation to add, and `style` argument
		must be given.
		`item` can be a `QsciStyledText` object, which comprises both the text and the style, so the
		`style` argument should not be passed.

		:param line: the line of the editor where to add the annotation
		:type line: int
		"""
		annotations = self.annotation_styled_text(line)

		if isinstance(item, bytes):
			item = [QsciStyledText(item.decode('utf-8'), style)]
		elif isinstance(item, str):
			item = [QsciStyledText(item, style)]
		elif isinstance(item, QsciStyledText):
			assert style is None
			item = [item]

		self.annotate(line, annotations + item)

	def annotate_append_line(self, line, item, style=None):
		"""Append a new annotation on a line

		"""
		current = self.annotation(line)
		if len(current) and not current.endswith('\n'):
			self.annotate_append(line, '\n', 0)
		return self.annotate_append(line, item, style)

	## signals
	file_about_to_be_saved = Signal(str)

	"""Signal file_about_to_be_saved(str)"""

	file_saved = Signal(str)

	"""Signal file_saved(str)"""

	file_saved_as = Signal(str)

	"""Signal file_saved_as(str)"""

	file_about_to_be_opened = Signal(str)

	"""Signal file_about_to_be_opened(str)"""

	file_opened = Signal(str)

	"""Signal file_opened(str)"""

	lexer_changed = Signal(object)

	"""Signal lexer_changed(object)"""

	file_modified_externally = Signal()

	"""Signal file_modified_externally()"""

	position_jumped = Signal(int, int)

	"""Signal position_jumped(int, int)"""

	## events
	@override
	def closeEvent(self, ev):
		accept_if(ev, self.close_file())


def iterlen(iterable):
	return sum(1 for _ in iterable)


@register_event_filter('editor', [QEvent.Wheel])
@disabled
def zoom_on_wheel(ed, ev):
	if ev.modifiers() == Qt.ControlModifier:
		delta = ev.angleDelta()
		if delta.y() > 0:
			ed.zoomIn()
			return True
		elif delta.y() < 0:
			ed.zoomOut()
			return True
	return False
