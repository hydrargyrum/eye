
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.Qsci import *
import sip
Signal = pyqtSignal
Slot = pyqtSlot

import os

from app import qApp
from .helpers import CategoryMixin, UtilsMixin, acceptIf
import utils

__all__ = 'Editor Marker Indicator Margin'.split()


class Marker(object):
	def __init__(self, sym, editor=None, id=-1):
		self.editor = editor
		self.sym = sym
		self.id = id
		if editor:
			self._create()

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


class Indicator(object):
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


class Margin(object):
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
			bits |= 1 << self.editor.markers[name].id
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

	startMacroRecord = sciPropSet(QsciScintilla.SCI_STARTRECORD, 0)
	stopMacroRecord = sciPropSet(QsciScintilla.SCI_STOPRECORD, 0)

	def __init__(self, *args):
		QsciScintilla.__init__(self, *args)

		self.freeMarkers = []
		self.markers = {}
		self.freeIndicators = []
		self.indicators = {}
		self.margins = {}

		self.createMargin('lines', Margin.NumbersMargin())
		self.createMargin('folding', Margin.FoldMargin())
		self.createMargin('symbols', Margin.SymbolMargin())

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
			marker = Indicator(indicator)
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
			return self.indicators[i].putAt(lineFrom, indexFrom, lineTo, indexTo)
		else:
			return QsciScintilla.fillIndicatorRange(self, lineFrom, indexFrom, lineTo, indexTo, i)

	def clearIndicatorRange(self, lineFrom, indexFrom, lineTo, indexTo, i):
		if isinstance(i, (str, unicode)):
			return self.indicators[i].removeAt(lineFrom, indexFrom, lineTo, indexTo)
		else:
			return QsciScintilla.clearIndicatorRange(self, lineFrom, indexFrom, lineTo, indexTo, i)

	def markerAdd(self, ln, i):
		if isinstance(i, (str, unicode)):
			return self.markers[i].putAt(ln)
		else:
			return QsciScintilla.markerAdd(self, ln, i)

	def markerDelete(self, ln, i):
		if isinstance(i, (str, unicode)):
			return self.markers[i].removeAt(ln)
		else:
			return QsciScintilla.markerDelete(self, ln, i)

	@Slot(int, int, object)
	def scn_macro(self, msg, lp, obj):
		if isinstance(p2, sip.voidptr):
			self.actionRecorded.emit(msg, p1, sipvoid_as_str(p2))
		else:
			self.actionRecorded.emit(msg, p1, p2)

	actionRecorded = Signal(int, int, object)


class Editor(BaseEditor, CategoryMixin, UtilsMixin):
	def __init__(self, *a):
		BaseEditor.__init__(self, *a)
		CategoryMixin.__init__(self)

		self.path = ''
		self.addCategory('editor')
		self.modificationChanged.connect(self.titleChanged)

	def title(self):
		t = os.path.basename(self.path) or '<untitled>'
		if self.isModified():
			return '%s*' % t
		else:
			return t

	def _getFilename(self):
		if not self.path:
			return ''
		return os.path.basename(self.path)

	def saveFile(self):
		path = self.path
		if not path:
			path = QFileDialog.getSaveFileName(self, self.tr('Save file'), os.path.expanduser('~'))
			if not path:
				return False
			path = unicode(path)
		data = str(self.text().toUtf8())
		try:
			utils.writeBytesToFile(path, data)
		except IOError, e:
			return False
		self.path = path
		self.setModified(False)
		self.titleChanged.emit()
		self.fileSaved.emit()
		return True

	def closeFile(self):
		ret = True

		if self.isModified():
			file = self._getFilename() or '<untitled>'

			answer = QMessageBox.question(self, self.tr('Unsaved file'), self.tr('%1 has been modified, do you want to close it?').arg(file), QMessageBox.Discard | QMessageBox.Cancel | QMessageBox.Save)
			if answer == QMessageBox.Discard:
				ret = True
			elif answer == QMessageBox.Cancel:
				ret = False
			elif answer == QMessageBox.Save:
				ret = self.saveFile()
		return ret

	def openFile(self, path):
		if not self.closeFile():
			return False
		self.path = path
		try:
			data = utils.readBytesFromFile(path)
			self.setText(data.decode('utf-8'))
		except IOError, e:
			qApp().logger.exception(e)
			return False
		self.setModified(False)
		self.fileOpened.emit()
		return True

	def goto1(self, row, col=None):
		col = col or 0
		row, col = row - 1, col - 1
		self.ensureLineVisible(row)
		self.setCursorPosition(row, col)

	def setLexer(self, lexer):
		QsciScintilla.setLexer(self, lexer)
		self.lexerChanged.emit(lexer)

	titleChanged = Signal()
	fileSaved = Signal()
	fileOpened = Signal()
	lexerChanged = Signal(QObject)

	# events
	def closeEvent(self, ev):
		acceptIf(ev, self.closeFile())
