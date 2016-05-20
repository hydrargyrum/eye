# this project is licensed under the WTFPLv2, see COPYING.txt for details

"""Editor widget


.. _positions:

Positions
---------

Positions in the text of an editor widget can be expressed in multiple ways.

First, the position of a character can be expressed as "line-index", which is the line and column of that character,
in terms of Unicode codepoints, with the `str` type (see :doc:`eye.three`). Unless specified otherwise, line and
column numbers start at 0 in EYE.

Another way, more low-level, is the byte offset of the byte in the byte text (with type `bytes`, see
:doc:`eye.three`). The internal byte encoding of the editor is UTF-8, regardless of the encoding of the underlying
disk file, which only intervenes when loading/saving.

Module contents
---------------
"""

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from PyQt5.Qsci import QsciScintilla
import sip
Signal = pyqtSignal
Slot = pyqtSlot

import os
import re
import contextlib
from weakref import ref
from logging import getLogger

from ..three import bytes, str
from .helpers import CentralWidgetMixin, acceptIf
from .. import structs
from .. import io

__all__ = ('Editor', 'Marker', 'Indicator', 'Margin', 'BaseEditor')

LOGGER = getLogger(__name__)

class HasWeakEditorMixin(object):
	def __init__(self, **kwargs):
		super(HasWeakEditorMixin, self).__init__(**kwargs)
		self.__editor = None

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
	For example, a marker can be used to indicate a breakpoint is present on a particular line of the file.

	In an editor, a Marker can be set or unset for multiple lines, in which cases the configured symbol will be
	shown in the margin of the lines where the marker has been set.

	Example:

		marker = editor.createMarker('breakpoint', editor.Circle)
		# declare a marker type called 'breakpoint' which will show a circle in the margin
		# the Marker instance can be retrieved if needed
		# marker = editor.markers['breakpoint']
		marker.putAt(2)  # marker is added at 3rd line
		marker.putAt(20)  # marker is added at 21st line

	A `Marker` is associated with an :any:`eye.widgets.editor.Editor`. An `Editor` can have multiple `Marker`s,
	each with an arbitrary name. A `Marker` has a symbol or pixmap configured and can then be put or removed for
	individual lines of the associated `Editor`.

	.. TODO max number, internal id
	"""

	def __init__(self, sym, editor=None, id=-1):
		self.editor = editor
		self.sym = sym
		self.id = id
		if editor:
			self._create()

	def toBit(self):
		"""Return the internal Scintilla marker id in this editor instance"""
		return 1 << self.id

	def _create(self, editor=None):
		if not self.editor:
			self.editor = editor

		if self.id < 0:
			if len(getattr(self.editor, 'freeMarkers', [])):
				self.id = self.editor.freeMarkers.pop()
			self.id = self.editor.markerDefine(self.sym, self.id)
			del self.sym

	def setSymbol(self, param):
		"""Change the visual symbol of the marker"""
		newid = self.editor.markerDefine(param, self.id)
		assert newid == self.id

	def putAt(self, line):
		"""Add a marker symbol of this type at `line`"""
		return self.editor.markerAdd(line, self.id)

	def removeAt(self, line):
		"""Remove marker of this type at `line` if present"""
		self.editor.markerDelete(line, self.id)

	def isAt(self, line):
		"""Return `True` if a marker of this type is present at `line`"""
		return self.toBit() & self.editor.markersAtLine(line)

	def getNext(self, line):
		"""Return the line number of first line having this marker after `line`

		-1 is returned if there is no line with the marker after `line`.
		"""
		return self.editor.getMarkerNext(line, self.toBit())

	def getPrevious(self, line):
		"""Return the line number of first line having this marker before `line`

		-1 is returned if there is no line with the marker before `line`.
		"""
		return self.editor.getMarkerPrevious(line, self.toBit())

	def listAll(self):
		"""List all lines that have this marker set"""
		ln = -1
		while True:
			ln = self.editor.markerFindNext(ln + 1, self.toBit())
			if ln < 0:
				return
			yield ln


class Indicator(HasWeakEditorMixin):
	"""Text indicator

	An indicator styles parts of the text with some particular visual style. It can be used for example by a
	spellchecker to underline misspelled words, or to highlight search results.

	In an editor, an indicator can be set for multiple ranges of characters in the text content, which will then
	be displayed in the configured style.

	Example:

		TODO

	Like :any:`eye.widgets.editor.Marker`, `Indicator`s are associated to an `Editor` and have an arbitrary name.
	"""
	def __init__(self, style, editor=None, id=-1):
		self.editor = editor
		self.style = style
		self.id = id
		if editor:
			self._create()

	def _create(self, editor=None):
		if not self.editor:
			self.editor = editor

		if self.id < 0:
			if len(getattr(self.editor, 'freeIndicators', [])):
				self.id = self.editor.freeIndicators.pop()
			self.id = self.editor.indicatorDefine(self.style, self.id)
			del self.style

	def getAtOffset(self, offset):
		"""Return `True` if the indicator is present at byte `offset`"""
		return self.editor.indicatorValueAt(self.id, offset)

	def getPreviousEdge(self, offset):
		"""Return the offset of the first edge of this indicator before `offset`.

		If `offset` is inside a range of characters with this indicator set, the start of the range is
		returned. If `offset` is outside, the end of the previous range before `offset` is returned.
		If there is no range before, -1 is returned.

		.. TODO -1?

		Example:

			>>> indicator.putAtOffset(4, 10)
			>>> indicator.getPreviousEdge(12)
			10
			>>> indicator.getPreviousEdge(9)
			4
			>>> indicator.getPreviousEdge(4)
			-1
		"""
		if offset > 0:
			offset -= 1
			# in scintilla, 'end' always advances, but 'starts' blocks...
		return self.editor.indicatorStart(self.id, offset)

	def getNextEdge(self, offset):
		"""Return the offset of the first edge of this indicator after `offset`.

		If `offset` is inside a range of characters with this indicator srt, the end of the range is
		returned. If `offset` is outside, the start of the next range after `offset` is returned.
		If there is no range after, -1 is returned.

		Example:

			>>> indicator.putAtOffset(4, 10)
			>>> indicator.getNextEdge(0)
			4
			>>> indicator.getNextEdge(4)
			10
			>>> indicator.getNextEdge(10)
			-1
		"""
		return self.editor.indicatorEnd(self.id, offset)

	def iterRanges(self):
		"""Return (start,end) tuples listing the ranges where the indicator is set.

		Returns an iterator of tuples. The tuples are byte-offset pairs.
		"""
		start = 0
		inrange = bool(self.getAtOffset(0))

		ed_end = self.editor.bytesLength()
		while start < ed_end:
			end = self.getNextEdge(start)
			if inrange:
				yield (start, end)

			inrange = not inrange
			start = end

	def putAt(self, lineFrom, indexFrom, lineTo, indexTo):
		"""Add the indicator to a range of characters (line-index based)"""
		self.editor.fillIndicatorRange(lineFrom, indexFrom, lineTo, indexTo, self.id)

	def putAtOffset(self, start, end):
		"""Add the indicator to a range of characters (byte offset based)"""
		startl, startc = self.editor.lineIndexFromPosition(start)
		endl, endc = self.editor.lineIndexFromPosition(end)
		self.putAt(startl, startc, endl, endc)

	def removeAt(self, lineFrom, indexFrom, lineTo, indexTo):
		"""Remove the indicator from a range of characters (line-index based)"""
		self.editor.clearIndicatorRange(lineFrom, indexFrom, lineTo, indexTo, self.id)

	def removeAtOffset(self, start, end):
		"""Remove the indicator from a range of characters (byte offset based)"""
		startl, startc = self.editor.lineIndexFromPosition(start)
		endl, endc = self.editor.lineIndexFromPosition(end)
		self.removeAt(startl, startc, endl, endc)

	def clear(self):
		"""Remove the indicator from all characters in the editor widget"""
		self.removeAtOffset(0, self.editor.bytesLength())

	def setColor(self, col):
		"""Set the color of the text marked by this indicator"""
		self.editor.setIndicatorForegroundColor(col, self.id)

	def setOutlineColor(self, col):
		"""Set the outline color of the text marked by this indicator"""
		self.editor.setIndicatorOutlineColor(col, self.id)

	def setStyle(self, style):
		"""Set the visual style of the text marked by this indicator"""
		self.id = self.editor.indicatorDefine(style, self.id)


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
		self.editor = editor
		self.id = id
		self.width = 0
		self.visible = True

	def _create(self, editor=None):
		if self.editor is None:
			self.editor = editor
		if self.editor:
			self.width = self.editor.marginWidth(self.id)

	def setWidth(self, w):
		self.width = w
		if self.visible:
			self.show()

	def setMarkerTypes(self, names):
		bits = 0
		for name in names:
			bits |= self.editor.markers[name].toBit()
		self.editor.setMarginMarkerMask(self.id, bits)

	def setAllMarkerTypes(self):
		self.editor.setMarginMarkerMask(self.id, (1 << 32) - 1)

	def setText(self, line, txt):
		if isinstance(txt, (str, bytes)):
			self.setMarginText(self.id, txt, 0)
		else:
			self.setMarginText(self.id, txt)

	def show(self):
		self.visible = True
		self.editor.setMarginWidth(self.id, self.width)

	def hide(self):
		self.visible = False
		self.editor.setMarginWidth(self.id, 0)


def sciProp(prop, expected_args):
	def func(self, *args):
		if len(args) != len(expected_args):
			raise TypeError("this function takes exactly %d argument(s)" % len(expected_args))
		for n, (arg, expected_type) in enumerate(zip(args, expected_args)):
			if not isinstance(arg, expected_type):
				raise TypeError("argument %d has unexpected type %r (expected %r)" %
				                (n + 1, type(arg).__name__, expected_type.__name__))
		return self.SendScintilla(prop, *args)
	return func


def sciProp2(prop):
	def func(self, arg1, arg2):
		return self.SendScintilla(prop, arg1, arg2)
	return func


def sciPropSet(prop):
	def func(self, value):
		return self.SendScintilla(prop, value)
	return func

sciProp1 = sciPropSet


def sciPropGet(prop):
	def func(self):
		return self.SendScintilla(prop)
	return func

sciProp0 = sciPropGet


def sipvoid_as_str(v):
    i = 1
    while True:
        s = v.asstring(i)
        if s[-1] == '\x00':
            return s[:-1]
        i += 1


class BaseEditor(QsciScintilla):
	"""Editor class adding missing Scintilla features

	QsciScintilla is an incomplete wrapper to Scintilla, this class aims to add support for a few of the missing
	editor features.

	.. note:: This class should not be instanciated directly as it exists only to add editor widget features and
	          is thus considered low-level.
	          :any:`eye.widgets.editor.Editor` contains file-related features and should be used instead.

	.. seealso::

		Since QsciScintilla is used as a base, the `QsciScintilla documentation
		<http://pyqt.sourceforge.net/Docs/QScintilla2/classQsciScintilla.html>`_ should also be consulted.
		The more low-level `Scintilla documentation <http://www.scintilla.org/ScintillaDoc.html>`_ can also
		help, though more rarely.
	"""

	# selection

	SelectionStream = QsciScintilla.SC_SEL_STREAM

	"""Select a character stream between two offsets in the text.

	If the start offset and end offset are not on the same lines, the characters from the start offset to the end
	of its line are selected, plus the characters from the end offset to the start of its line, plus the lines in
	between are completely selected.
	"""

	SelectionRectangle = QsciScintilla.SC_SEL_RECTANGLE

	"""Select characters in a rectangle between two offsets in the text.

	On each line from the line of the start offset to the line of the end offset, only characters from the column
	of the start offset to end column of the end offset are selected, thus making a rectangle.
	"""

	SelectionLines = QsciScintilla.SC_SEL_LINES

	"""Select full lines between two offsets in the text.

	All characters of the lines between the start offset and end offset, included, are selected.
	"""

	SelectionThin = QsciScintilla.SC_SEL_THIN

	setSelectionMode = sciPropSet(QsciScintilla.SCI_SETSELECTIONMODE)
	selectionMode = sciPropGet(QsciScintilla.SCI_GETSELECTIONMODE)

	setMultipleSelection = sciPropSet(QsciScintilla.SCI_SETMULTIPLESELECTION)

	"""setMultipleSelection(bool)

	Set if multiple ranges of characters can be selected. All ranges are selected in the same selection mode.
	"""

	multipleSelection = sciPropGet(QsciScintilla.SCI_GETMULTIPLESELECTION)
	"""Return `True` if multiple selection is enabled"""

	setAdditionalSelectionTyping = sciPropSet(QsciScintilla.SCI_SETADDITIONALSELECTIONTYPING)
	additionalSelectionTyping = sciPropGet(QsciScintilla.SCI_GETADDITIONALSELECTIONTYPING)

	selectionsCount = sciPropGet(QsciScintilla.SCI_GETSELECTIONS)

	"""Return the number of selection ranges (if multiple selections are enabled, else 1)"""

	selectionsEmpty = sciPropGet(QsciScintilla.SCI_GETSELECTIONEMPTY)
	clearSelections = sciPropGet(QsciScintilla.SCI_CLEARSELECTIONS)

	setMainSelection = sciPropSet(QsciScintilla.SCI_SETMAINSELECTION)
	mainSelection = sciPropGet(QsciScintilla.SCI_GETMAINSELECTION)

	# virtual space
	VsNone = QsciScintilla.SCVS_NONE

	"""Virtual space after a line's end is not accessible"""

	VsRectangular = QsciScintilla.SCVS_RECTANGULARSELECTION

	"""Virtual space after a line's end is accessible with rectangular selection mode"""

	VsUser = QsciScintilla.SCVS_USERACCESSIBLE

	"""Virtual space after a line's end is accessible by user with cursor"""

	setVirtualSpaceOptions = sciPropSet(QsciScintilla.SCI_SETVIRTUALSPACEOPTIONS)

	"""Set options for virtual space after a line's end

	Should be an or-combination of one or more flags in :any:`VsNone`, :any:`VsRectangular`, :any:`VsUser`.
	"""

	virtualSpaceOptions = sciPropGet(QsciScintilla.SCI_GETVIRTUALSPACEOPTIONS)

	"""Get virtual space options

	See :any:`setVirtualSpaceOptions`.
	"""

	# character representation
	setRepresentation = sciProp2(QsciScintilla.SCI_SETREPRESENTATION)
	getRepresentation = sciPropGet(QsciScintilla.SCI_GETREPRESENTATION)
	clearRepresentation = sciProp1(QsciScintilla.SCI_CLEARREPRESENTATION)

	# fold
	FoldFlagLineBeforeExpanded = QsciScintilla.SC_FOLDFLAG_LINEBEFORE_EXPANDED
	FoldFlagLineBeforeContracted = QsciScintilla.SC_FOLDFLAG_LINEBEFORE_CONTRACTED
	FoldFlagLineAfterExpanded = QsciScintilla.SC_FOLDFLAG_LINEAFTER_EXPANDED
	FoldFlagLineAfterContracted = QsciScintilla.SC_FOLDFLAG_LINEAFTER_CONTRACTED
	FoldFlagLevelNumbers = QsciScintilla.SC_FOLDFLAG_LEVELNUMBERS
	FoldFlagLineState = QsciScintilla.SC_FOLDFLAG_LINESTATE

	setFoldFlags = sciPropSet(QsciScintilla.SCI_SETFOLDFLAGS)
	setFoldLevel = sciProp2(QsciScintilla.SCI_SETFOLDLEVEL)

	"""Set fold level of a line

	Set fold level `arg2` for line `arg1`.
	"""

	getFoldLevel = sciProp1(QsciScintilla.SCI_GETFOLDLEVEL)

	"""Get fold level of line `value`"""

	# macro
	_startMacroRecord = sciProp0(QsciScintilla.SCI_STARTRECORD)
	_stopMacroRecord = sciProp0(QsciScintilla.SCI_STOPRECORD)

	# markers
	_getMarkerPrevious = sciProp2(QsciScintilla.SCI_MARKERPREVIOUS)
	_getMarkerNext = sciProp2(QsciScintilla.SCI_MARKERNEXT)

	# indicators
	indicatorValueAt = sciProp2(QsciScintilla.SCI_INDICATORVALUEAT)
	indicatorStart = sciProp2(QsciScintilla.SCI_INDICATORSTART)
	indicatorEnd = sciProp2(QsciScintilla.SCI_INDICATOREND)

	# search
	setTargetStart = sciPropSet(QsciScintilla.SCI_SETTARGETSTART)
	targetStart = sciPropGet(QsciScintilla.SCI_GETTARGETSTART)
	setTargetEnd = sciPropSet(QsciScintilla.SCI_SETTARGETEND)
	targetEnd = sciPropGet(QsciScintilla.SCI_GETTARGETEND)
	setTargetRange = sciProp2(QsciScintilla.SCI_SETTARGETRANGE)
	_searchInTarget = sciProp(QsciScintilla.SCI_SEARCHINTARGET, (int, bytes))

	setSearchFlags = sciPropSet(QsciScintilla.SCI_SETSEARCHFLAGS)
	searchFlags = sciPropGet(QsciScintilla.SCI_GETSEARCHFLAGS)

	# caret
	CaretStyleInvisible = QsciScintilla.CARETSTYLE_INVISIBLE

	"""Caret is invisible"""

	CaretStyleLine = QsciScintilla.CARETSTYLE_LINE

	"""Caret is a vertical line between two characters"""

	CaretStyleBlock = QsciScintilla.CARETSTYLE_BLOCK

	"""Caret is a block enclosing the next character"""

	setCaretStyle = sciPropSet(QsciScintilla.SCI_SETCARETSTYLE)

	"""Set caret display style

	Should be one of :any:`CaretStyleInvisible`, :any:`CaretStyleLine`, :any:`CaretStyleBlock`.
	"""

	caretStyle = sciPropGet(QsciScintilla.SCI_GETCARETSTYLE)

	"""Get caret display style

	See :any:`setCaretStyle`.
	"""

	setCaretPeriod = sciPropSet(QsciScintilla.SCI_SETCARETPERIOD)

	"""Set caret blinking period in milliseconds"""

	caretPeriod = sciPropGet(QsciScintilla.SCI_GETCARETPERIOD)

	"""Get caret blinking period in milliseconds"""

	# lexer
	setLexerProperty = sciProp(QsciScintilla.SCI_SETPROPERTY, (bytes, bytes))

	"""setLexerProperty(bytes, bytes): set a lexer property (key/value)"""

	# text
	deleteRange = sciProp2(QsciScintilla.SCI_DELETERANGE)

	"""Delete characters in byte offset range"""

	def __init__(self, **kwargs):
		super(BaseEditor, self).__init__(**kwargs)

		self.SCN_MACRORECORD.connect(self.scn_macro)
		self.SCN_MODIFIED.connect(self.scn_modified)

		self.freeMarkers = []
		self.markers = {}
		self.freeIndicators = []
		self.indicators = {}
		self.margins = {}

		self.createMargin('lines', Margin.NumbersMargin())
		self.createMargin('folding', Margin.FoldMargin())
		self.createMargin('symbols', Margin.SymbolMargin())

	## markers, indicators, margins
	def _createMI(self, d, name, obj):
		if name in d:
			return d[name]
		d[name] = obj
		obj._create(editor=self)
		return obj

	def createMarker(self, name, marker):
		"""Create and return a Marker with name `name` and symbol `marker`"""
		if not isinstance(marker, Marker):
			marker = Marker(marker)
		return self._createMI(self.markers, name, marker)

	def createIndicator(self, name, indicator):
		"""Create and return an Indicator with name `name` and style `indicator`"""
		if not isinstance(indicator, Indicator):
			indicator = Indicator(indicator)
		return self._createMI(self.indicators, name, indicator)

	def createMargin(self, name, margin):
		return self._createMI(self.margins, name, margin)

	def _disposeMI(self, d, dfree, name):
		if name not in d:
			return
		dfree.append(d[name].id)
		del d[name]

	def disposeMarker(self, name):
		self._disposeMI(self.markers, self.freeMarkers, name)

	def disposeIndicator(self, name):
		self._disposeMI(self.indicators, self.freeIndicators, name)

	def fillIndicatorRange(self, lineFrom, indexFrom, lineTo, indexTo, i):
		if isinstance(i, (str, bytes)):
			i = self.indicators[i].id
		return QsciScintilla.fillIndicatorRange(self, lineFrom, indexFrom, lineTo, indexTo, i)

	def clearIndicatorRange(self, lineFrom, indexFrom, lineTo, indexTo, i):
		if isinstance(i, (str, bytes)):
			i = self.indicators[i].id
		return QsciScintilla.clearIndicatorRange(self, lineFrom, indexFrom, lineTo, indexTo, i)

	def markerAdd(self, ln, i):
		"""Add marker with name/id `i` at line `ln`"""
		if isinstance(i, (str, bytes)):
			i = self.markers[i].id
		return QsciScintilla.markerAdd(self, ln, i)

	def markerDelete(self, ln, i):
		"""Delete marker with name/id `i` from line `ln`"""
		if isinstance(i, (str, bytes)):
			i = self.markers[i].id
		return QsciScintilla.markerDelete(self, ln, i)

	def setMarkerBackgroundColor(self, c, i):
		"""Set background color `c` to marker with id/name `i`"""
		if isinstance(i, (str, bytes)):
			i = self.markers[i].id
		return QsciScintilla.setMarkerBackgroundColor(self, c, i)

	def setMarkerForegroundColor(self, c, i):
		if isinstance(i, (str, bytes)):
			i = self.markers[i].id
		return QsciScintilla.setMarkerForegroundColor(self, c, i)

	def getMarkerPrevious(self, ln, i):
		if isinstance(i, (str, bytes)):
			i = self.markers[i].id
		return self._getMarkerPrevious(ln, i)

	def getMarkerNext(self, ln, i):
		if isinstance(i, (str, bytes)):
			i = self.markers[i].id
		return self._getMarkerNext(ln, i)

	## macros
	#~ @Slot('uint', 'unsigned long', object)
	def scn_macro(self, msg, lp, wp):
		if isinstance(wp, sip.voidptr):
			self.actionRecorded.emit([msg, lp, sipvoid_as_str(wp)])
		else:
			self.actionRecorded.emit([msg, lp, wp])

	def startMacroRecord(self):
		"""Start recording macro

		Also emits `macroRecordStarted()`
		"""
		self._startMacroRecord()
		self.macroRecordStarted.emit()

	def stopMacroRecord(self):
		"""Stop recording macro

		Also emits `macroRecordStopped()`
		"""
		self._stopMacroRecord()
		self.macroRecordStopped.emit()

	def replayMacroAction(self, action):
		"""Replay a macro action

		"""
		msg, lp, wp = action
		return self.SendScintilla(msg, lp, wp)

	def searchInTarget(self, s):
		if isinstance(s, str):
			s = s.encode('utf-8')
		return self._searchInTarget(len(s), s)

	@Slot(int, int, 'const char*', int, int, int, int, int, int, int)
	def scn_modified(self, *args):
		self.sciModified.emit(args)

	macroRecordStarted = Signal()

	"""Signal macroRecordStarted()

	After this signal is emitted, and until `macroRecordStopped()` is emitted, actions performed by user will be
	recorded and `actionRecorded(object)` will be emitted for each action.
	"""

	macroRecordStopped = Signal()

	"""Signal macroRecordStopped()

	This signal is emitted when macro recording stops. `actionRecorded()` will not be emitted any more after.
	"""

	actionRecorded = Signal(object)

	"""Signal actionRecorded(object): an action was recorded in macro

	The signal argument is the action recorded, and can be passed to `replayMacroAction` to replay this action.
	Internally, the action argument is a tuple suitable for Scintilla to process it.
	"""

	sciModified = Signal(object)

	"""Signal sciModified(object): a modification was done

	The signal argument is a 10-tuple describing the modification. The modifications signalled can be of various
	types.
	"""


class Editor(BaseEditor, CentralWidgetMixin):
	"""Editor widget class

	By default, instances of this class have the "editor" category set (see :doc:`eye.connector` for more info).

	.. seealso::

		Since QsciScintilla is used as a base, the `QsciScintilla documentation
		<http://pyqt.sourceforge.net/Docs/QScintilla2/classQsciScintilla.html>`_ should also be consulted.
	"""

	SmartCaseSensitive = object()

	def __init__(self, **kwargs):
		super(Editor, self).__init__(**kwargs)

		self.path = ''
		self.modificationChanged.connect(self.titleChanged)

		self.saving = structs.PropDict()
		self.saving.trim_whitespace = False
		self.saving.final_newline = True
		self.saving.encoding = 'utf-8'
		self.setUtf8(True)
		# the editor is in utf-8 internally, encoding is done when saving

		self.search = structs.PropDict()
		self.search.incremental = True
		self.search.highlight = False
		self.search.isRe = False
		self.search.caseSensitive = False
		self.search.wrap = True
		self.search.whole = False

		self._lexer = None

		self.addCategory('editor')

	def __repr__(self):
		return '<Editor path=%r>' % self.path

	def title(self):
		t = os.path.basename(self.path) or '<untitled>'
		if self.isModified():
			return '%s*' % t
		else:
			return t

	## file management
	def _getFilename(self):
		if not self.path:
			return ''
		return os.path.basename(self.path)

	@Slot()
	def saveFile(self):
		"""Save edited file

		If no file path is set, a file dialog is shown to ask the user where to save content.
		"""
		path = self.path

		newFile = not path
		if newFile:
			path, qfilter = QFileDialog.getSaveFileName(self, self.tr('Save file'), os.path.expanduser('~'))
			if not path:
				return False
			path = path

		data = self._writeText(self.text())
		self.fileAboutToBeSaved.emit(path)
		try:
			io.writeBytesToFile(path, data)
		except IOError:
			LOGGER.error('cannot write file %r', path, exc_info=True)
			return False

		self.path = path
		self.setModified(False)
		self.titleChanged.emit()
		if newFile:
			self.fileSavedAs.emit(path)
		else:
			self.fileSaved.emit(path)

		return True

	def closeFile(self):
		"""Prepare for closing file and return `True` if modification state is clean

		If editor has no unsaved modifications, returns `True`. Else, ask user if modifications should be
		saved, then return `True` if accepted, else return `False`.
		"""
		ret = True

		if self.isModified():
			file = self._getFilename() or '<untitled>'

			answer = QMessageBox.question(self, self.tr('Unsaved file'), self.tr('%s has been modified, do you want to close it?') % file, QMessageBox.Discard | QMessageBox.Cancel | QMessageBox.Save)
			if answer == QMessageBox.Discard:
				ret = True
			elif answer == QMessageBox.Cancel:
				ret = False
			elif answer == QMessageBox.Save:
				ret = self.saveFile()
		return ret

	def _newlineString(self):
		modes = {QsciScintilla.SC_EOL_LF: '\n', QsciScintilla.SC_EOL_CRLF: '\r\n',
		         QsciScintilla.SC_EOL_CR: '\r'}
		return modes.get(self.eolMode(), '\n')

	def _readText(self, data):
		text = data.decode(self.saving.encoding)
		if self.saving.final_newline and text.endswith(self._newlineString()):
			text = text[:-1]
		return text

	def _removeTrailingWhitespace(self, text):
		return re.sub(r'[ \t]+$', '', text, flags=re.MULTILINE)

	def _writeText(self, text):
		if self.saving.trim_whitespace:
			text = self._removeTrailingWhitespace(text)
		if self.saving.final_newline:
			text += self._newlineString()
		return text.encode(self.saving.encoding)

	def openFile(self, path):
		if not self.closeFile():
			return False
		self.path = path

		try:
			data = io.readBytesFromFile(path)
		except IOError:
			LOGGER.error('cannot read file %r', path, exc_info=True)
			return False
		self.fileAboutToBeOpened.emit(path)

		text = self._readText(data)
		self.setText(text)
		self.setModified(False)
		self.fileOpened.emit(path)
		return True

	@Slot()
	def reloadFile(self):
		"""Reload file contents (losing unsaved modifications)

		Reload file from disk and replace editor contents with updated text.
		If the user made modifications to the editor contents without saving them, calling this method will
		will lose them. However, the replacement can be undone by the user.
		"""
		oldPos = self.getCursorPosition()

		try:
			data = io.readBytesFromFile(self.path)
		except IOError:
			LOGGER.error('cannot reload file %r', self.path, exc_info=True)
			return False
		text = self._readText(data)

		with self.undoGroup():
			# XXX setText would clear the history
			self.clear()
			self.insert(text)
		self.setModified(False)
		self.setCursorPosition(*oldPos)
		return True

	## various props
	def setUseFinalNewline(self, b):
		"""Set whether a final newline should always be added when saving to disk

		If `b` is False, the contents of the editor won't be changed when saving file to disk: the file will
		only contain a final newline if the editor text ends with a newline.

		If `b` is True, a final newline will be added to the file saved on disk, but this final newline won't
		be shown in the editor. When the file is loaded, if it ends with a final newline, it won't be shown
		in the editor either, though will be kept when saving again.

		This does not cause the file to be re-saved.
		"""
		self.saving.final_newline = b

	def useFinalNewline(self):
		return self.saving.final_newline

	def setRemoveTrailingWhitespace(self, b):
		self.saving.trim_whitespace = b

	def doesRemoveTrailingWhitespace(self):
		return self.saving.trim_whitespace

	def setEncoding(self, s):
		"""Set the file data encoding for loading/saving

		When loading file contents from disk or saving file to disk, this encoding will be used. This does
		not change the internal encoding used by the editor widget, which is UTF-8.

		This does not cause the file to be re-saved.
		"""
		u''.encode(s) # ensure it's usable
		self.saving.encoding = s

	def encoding(self):
		"""Return the encoding to use for loading/saving"""
		return self.saving.encoding

	## misc
	@contextlib.contextmanager
	def undoGroup(self):
		self.beginUndoAction()
		try:
			yield
		finally:
			self.endUndoAction()

	@Slot()
	def goto1(self, line, col=None):
		col = col or 1
		line, col = line - 1, col - 1
		self.ensureLineVisible(line)
		self.setCursorPosition(line, col)

	def getLine(self):
		"""Return the line number of the cursor position"""
		return self.getCursorPosition()[0]

	def setLexer(self, lexer):
		QsciScintilla.setLexer(self, lexer)
		self._lexer = lexer
		self.lexerChanged.emit(lexer)

	def lexer(self):
		lexer = QsciScintilla.lexer(self)
		if lexer is None:
			lexer = self._lexer
		return lexer

	def cursorPosition(self):
		"""Return the cursor line-index starting from 0

		.. note:: This function is misnamed in QsciScintilla and the naming is kept here to avoid more
		          confusion.

		See :ref:`positions`.
		"""
		return self.getCursorPosition()

	cursorLineIndex = cursorPosition

	def cursorOffset(self):
		"""Return the cursor position in byte offset

		As this function returns a byte-offset, it should not be used unless necessary.
		See :ref:`positions`.
		"""
		return self.positionFromLineIndex(*self.getCursorPosition())

	def bytesLength(self):
		"""Return the length of the text in bytes"""
		return self.length()

	def textLength(self):
		"""Return the length of the text in Unicode codepoints"""
		return len(self.text())

	## search
	@classmethod
	def _smartCase(cls, txt, cs):
		if cs is cls.SmartCaseSensitive:
			return (txt.lower() != txt)
		else:
			return cs

	def _searchOptionsToRe(self):
		expr = self.search.expr if self.search.isRe else re.escape(self.search.expr)
		if self.search.whole:
			expr = '\b%s\b' % expr
		caseSensitive = self._smartCase(expr, self.search.caseSensitive)
		flags = 0 if caseSensitive else re.I
		return re.compile(expr, flags)

	def _highlightSearch(self):
		txt = self.text()
		reobj = self._searchOptionsToRe()
		for mtc in reobj.finditer(txt):
			self.indicators['searchHighlight'].putAtOffset(mtc.start(), mtc.end())

	def clearSearchHighlight(self):
		self.indicators['searchHighlight'].removeAtOffset(0, self.bytesLength())

	def find(self, expr, caseSensitive=None, isRe=None, whole=None, wrap=None):
		if self.search.highlight:
			self.clearSearchHighlight()

		self.search.expr = expr
		if caseSensitive is not None:
			self.search.caseSensitive = caseSensitive
		if isRe is not None:
			self.search.isRe = isRe
		if whole is not None:
			self.search.whole = whole
		if wrap is not None:
			self.search.wrap = wrap
		self.search.forward = True

		caseSensitive = self._smartCase(expr, self.search.caseSensitive)

		if self.search.highlight:
			self._highlightSearch()

		lfrom, ifrom, lto, ito = self.getSelection()
		self.setCursorPosition(*min([(lfrom, ifrom), (lto, ito)]))

		return self.findFirst(self.search.expr, self.search.isRe, caseSensitive, self.search.whole, self.search.wrap, True)

	def _findInDirection(self, forward):
		if self.search.get('forward') == forward:
			return self.findNext()
		else:
			self.search.forward = forward
			caseSensitive = self._smartCase(self.search.expr, self.search.caseSensitive)
			b = self.findFirst(self.search.expr, self.search.isRe, caseSensitive, self.search.whole, self.search.wrap, self.search.forward)
			if b and not forward:
				# weird behavior when switching from forward to backward
				return self.findNext()
			return b

	def findForward(self):
		return self._findInDirection(True)

	def findBackward(self):
		return self._findInDirection(False)

	def wordAtCursor(self):
		return self.wordAtLineIndex(*self.getCursorPosition())

	## signals
	titleChanged = Signal()

	"""Signal titleChanged()"""

	fileAboutToBeSaved = Signal(str)

	"""Signal fileAboutToBeSaved(str)"""

	fileSaved = Signal(str)

	"""Signal fileSaved(str)"""

	fileSavedAs = Signal(str)

	"""Signal fileSavedAs(str)"""

	fileAboutToBeOpened = Signal(str)

	"""Signal fileAboutToBeOpened(str)"""

	fileOpened = Signal(str)

	"""Signal fileOpened(str)"""

	lexerChanged = Signal(object)

	"""Signal lexerChanged(object)"""

	fileModifiedExternally = Signal()

	"""Signal fileModifiedExternally()"""

	positionJumped = Signal(int, int)

	"""Signal positionJumped(int, int)"""

	## events
	def closeEvent(self, ev):
		acceptIf(ev, self.closeFile())
