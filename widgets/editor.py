
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.Qsci import *
import sip
Signal = pyqtSignal
Slot = pyqtSlot

import os

from app import qApp
from .helpers import CategoryMixin, acceptIf
import utils

__all__ = 'Editor'.split()


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

	@Slot(int, int, object)
	def scn_macro(self, msg, lp, obj):
		if isinstance(p2, sip.voidptr):
			self.actionRecorded.emit(msg, p1, sipvoid_as_str(p2))
		else:
			self.actionRecorded.emit(msg, p1, p2)

	actionRecorded = Signal(int, int, object)


class Editor(BaseEditor, CategoryMixin):
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
