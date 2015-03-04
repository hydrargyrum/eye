
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.Qsci import *
Signal = pyqtSignal
Slot = pyqtSlot

import os

from app import qApp
from .helpers import CategoryMixin, acceptIf
import utils

__all__ = 'Editor'.split()


class Editor(QsciScintilla, CategoryMixin):
	def __init__(self, *a):
		QsciScintilla.__init__(self, *a)
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
