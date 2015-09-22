# this project is licensed under the WTFPLv2, see COPYING.txt for details

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.Qsci import *
import sip
Signal = pyqtSignal
Slot = pyqtSlot

import os
import re
import contextlib
from weakref import ref
from logging import getLogger

from ..app import qApp
from .helpers import CentralWidgetMixin, acceptIf
from .. import structs
from .. import io

__all__ = ('Editor', 'Marker', 'Indicator', 'Margin')


LOGGER = getLogger(__name__)

class HasWeakEditorMixin(object):
	@property
	def editor(self):
		if self._editor is not None:
			return self._editor()

	@editor.setter
	def editor(self, value):
		if value is None:
			self._editor = None
		else:
			self._editor = ref(value)


class Marker(HasWeakEditorMixin):
	def __init__(self, sym, editor=None, id=-1):
		self.editor = editor
		self.sym = sym
		self.id = id
		if editor:
			self._create()

	def toBit(self):
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
		newid = self.editor.markerDefine(param, self.id)
		assert newid == self.id

	def putAt(self, line):
		return self.editor.markerAdd(line, self.id)

	def removeAt(self, line):
		self.editor.markerDelete(line, self.id)

	def isAt(self, line):
		return self.toBit() & self.editor.markersAtLine(line)

	def getNext(self, line):
		return self.editor.getMarkerNext(line, self.toBit())

	def getPrevious(self, line):
		return self.editor.getMarkerPrevious(line, self.toBit())


class Indicator(HasWeakEditorMixin):
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

	def putAt(self, lineFrom, indexFrom, lineTo, indexTo):
		self.editor.fillIndicatorRange(lineFrom, indexFrom, lineTo, indexTo, self.id)

	def putAtPos(self, start, end):
		startLi = self.editor.lineIndexFromPosition(start)
		endLi = self.editor.lineIndexFromPosition(end)
		self.putAt(*(startLi + endLi))

	def removeAt(self, lineFrom, indexFrom, lineTo, indexTo):
		self.editor.clearIndicatorRange(lineFrom, indexFrom, lineTo, indexTo, self.id)

	def removeAtPos(self, start, end):
		startLi = self.editor.lineIndexFromPosition(start)
		endLi = self.editor.lineIndexFromPosition(end)
		self.removeAt(*(startLi + endLi))

	def setColor(self, col):
		self.editor.setIndicatorForegroundColor(col, self.id)

	def setOutlineColor(self, col):
		self.editor.setIndicatorOutlineColor(col, self.id)


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
		if isinstance(txt, (str, unicode)):
			self.setMarginText(self.id, txt, 0)
		else:
			self.setMarginText(self.id, txt)

	def show(self):
		self.visible = True
		self.editor.setMarginWidth(self.id, self.width)

	def hide(self):
		self.visible = False
		self.editor.setMarginWidth(self.id, 0)


def factory_factory(default_expected_args):
	def factory(prop, expected_args=default_expected_args):
		def func(self, *args):
			if len(args) != expected_args:
				raise TypeError("this function takes %d argument(s)" % expected_args)
			return self.SendScintilla(prop, *args)
		return func
	return factory

sciPropSet = factory_factory(1)
sciPropGet = factory_factory(0)

def sipvoid_as_str(v):
    i = 1
    while True:
        s = v.asstring(i)
        if s[-1] == '\x00':
            return s[:-1]
        i += 1

class BaseEditor(QsciScintilla):
	SelectionStream = QsciScintilla.SC_SEL_STREAM
	SelectionRectangle = QsciScintilla.SC_SEL_RECTANGLE
	SelectionLines = QsciScintilla.SC_SEL_LINES
	SelectionThin = QsciScintilla.SC_SEL_THIN

	setSelectionMode = sciPropSet(QsciScintilla.SCI_SETSELECTIONMODE)
	selectionMode = sciPropGet(QsciScintilla.SCI_GETSELECTIONMODE)

	setMultipleSelection = sciPropSet(QsciScintilla.SCI_SETMULTIPLESELECTION)
	multipleSelection = sciPropGet(QsciScintilla.SCI_GETMULTIPLESELECTION)

	setAdditionalSelectionTyping = sciPropSet(QsciScintilla.SCI_SETADDITIONALSELECTIONTYPING)
	additionalSelectionTyping = sciPropGet(QsciScintilla.SCI_GETADDITIONALSELECTIONTYPING)

	VsNone = QsciScintilla.SCVS_NONE
	VsRectangular = QsciScintilla.SCVS_RECTANGULARSELECTION
	VsUser = QsciScintilla.SCVS_USERACCESSIBLE

	setVirtualSpaceOptions = sciPropSet(QsciScintilla.SCI_SETVIRTUALSPACEOPTIONS)
	virtualSpaceOptions = sciPropGet(QsciScintilla.SCI_GETVIRTUALSPACEOPTIONS)

	selectionsCount = sciPropGet(QsciScintilla.SCI_GETSELECTIONS)
	selectionsEmpty = sciPropGet(QsciScintilla.SCI_GETSELECTIONEMPTY)
	clearSelections = sciPropSet(QsciScintilla.SCI_CLEARSELECTIONS, 0)

	setMainSelection = sciPropSet(QsciScintilla.SCI_SETMAINSELECTION)
	mainSelection = sciPropGet(QsciScintilla.SCI_GETMAINSELECTION)

	setRepresentation = sciPropSet(QsciScintilla.SCI_SETREPRESENTATION, 2)
	getRepresentation = sciPropGet(QsciScintilla.SCI_GETREPRESENTATION)
	clearRepresentation = sciPropSet(QsciScintilla.SCI_CLEARREPRESENTATION)

	setFoldLevel = sciPropGet(QsciScintilla.SCI_SETFOLDLEVEL, 2)
	getFoldLevel = sciPropGet(QsciScintilla.SCI_GETFOLDLEVEL, 1)

	_startMacroRecord = sciPropSet(QsciScintilla.SCI_STARTRECORD, 0)
	_stopMacroRecord = sciPropSet(QsciScintilla.SCI_STOPRECORD, 0)

	_getMarkerPrevious = sciPropGet(QsciScintilla.SCI_MARKERPREVIOUS, 2)
	_getMarkerNext = sciPropGet(QsciScintilla.SCI_MARKERNEXT, 2)

	def __init__(self, *args):
		QsciScintilla.__init__(self, *args)

		self.SCN_MACRORECORD.connect(self.scn_macro)

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
		if not isinstance(marker, Marker):
			marker = Marker(marker)
		return self._createMI(self.markers, name, marker)

	def createIndicator(self, name, indicator):
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
		if isinstance(i, (str, unicode)):
			i = self.indicators[i].id
		return QsciScintilla.fillIndicatorRange(self, lineFrom, indexFrom, lineTo, indexTo, i)

	def clearIndicatorRange(self, lineFrom, indexFrom, lineTo, indexTo, i):
		if isinstance(i, (str, unicode)):
			i = self.indicators[i].id
		return QsciScintilla.clearIndicatorRange(self, lineFrom, indexFrom, lineTo, indexTo, i)

	def markerAdd(self, ln, i):
		if isinstance(i, (str, unicode)):
			i = self.markers[i].id
		return QsciScintilla.markerAdd(self, ln, i)

	def markerDelete(self, ln, i):
		if isinstance(i, (str, unicode)):
			i = self.markers[i].id
		return QsciScintilla.markerDelete(self, ln, i)

	def setMarkerBackgroundColor(self, c, i):
		if isinstance(i, (str, unicode)):
			i = self.markers[i].id
		return QsciScintilla.setMarkerBackgroundColor(self, c, i)

	def setMarkerForegroundColor(self, c, i):
		if isinstance(i, (str, unicode)):
			i = self.markers[i].id
		return QsciScintilla.setMarkerForegroundColor(self, c, i)

	def getMarkerPrevious(self, ln, i):
		if isinstance(i, (str, unicode)):
			i = self.markers[i].id
		return self._getMarkerPrevious(ln, i)

	def getMarkerNext(self, ln, i):
		if isinstance(i, (str, unicode)):
			i = self.markers[i].id
		return self._getMarkerNext(ln, i)

	## macros
	@Slot(int, int, object)
	def scn_macro(self, msg, lp, wp):
		if isinstance(wp, sip.voidptr):
			self.actionRecorded.emit([msg, lp, sipvoid_as_str(wp)])
		else:
			self.actionRecorded.emit([msg, lp, wp])

	def startMacroRecord(self):
		self._startMacroRecord()
		self.macroRecordStarted.emit()

	def stopMacroRecord(self):
		self._stopMacroRecord()
		self.macroRecordStopped.emit()

	def replayMacroAction(self, action):
		msg, lp, wp = action
		return self.SendScintilla(msg, lp, wp)

	macroRecordStarted = Signal()
	macroRecordStopped = Signal()
	actionRecorded = Signal(object)


class Editor(BaseEditor, CentralWidgetMixin):
	SmartCaseSensitive = object()

	def __init__(self, *a):
		BaseEditor.__init__(self, *a)
		CentralWidgetMixin.__init__(self)

		self.path = ''
		self.modificationChanged.connect(self.titleChanged)

		self.saving = structs.PropDict()
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

	def saveFile(self):
		path = self.path

		newFile = not path
		if newFile:
			path = QFileDialog.getSaveFileName(self, self.tr('Save file'), os.path.expanduser('~'))
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

	def _writeText(self, text):
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

	def reloadFile(self):
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

	## misc
	@contextlib.contextmanager
	def undoGroup(self):
		self.beginUndoAction()
		try:
			yield
		finally:
			self.endUndoAction()

	def goto1(self, line, col=None):
		col = col or 1
		line, col = line - 1, col - 1
		self.ensureLineVisible(line)
		self.setCursorPosition(line, col)

	def getLine(self):
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
			self.indicators['searchHighlight'].putAtPos(mtc.start(), mtc.end())

	def clearSearchHighlight(self):
		self.indicators['searchHighlight'].removeAtPos(0, self.length())

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
	fileAboutToBeSaved = Signal(unicode)
	fileSaved = Signal(unicode)
	fileSavedAs = Signal(unicode)
	fileAboutToBeOpened = Signal(unicode)
	fileOpened = Signal(unicode)
	lexerChanged = Signal(QObject)
	fileModifiedExternally = Signal()
	positionJumped = Signal(int, int)

	## events
	def closeEvent(self, ev):
		acceptIf(ev, self.closeFile())
