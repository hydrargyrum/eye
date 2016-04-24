# this project is licensed under the WTFPLv2, see COPYING.txt for details

from PyQt5.QtCore import QObject, QTimer, pyqtSignal as Signal, pyqtSlot as Slot
from PyQt5.Qsci import QsciScintilla

import re

from ..connector import disabled, defaultLexerConfig
from ..widgets.editor import HasWeakEditorMixin


__all__ = ('MarkerFolder', 'disableLexerFolding')


@defaultLexerConfig
@disabled
def disableLexerFolding(ed, *args):
	ed.setLexerProperty(b'fold', b'0')


class MarkerFolder(QObject, HasWeakEditorMixin):
	markerStart = re.compile(r'\{\{\{')
	markerEnd = re.compile(r'\}\}\}')
	interval = 100

	def __init__(self, editor=None, **kwargs):
		super(MarkerFolder, self).__init__(**kwargs)
		self.editor = editor
		editor.sciModified.connect(self.onModification)
		self.timer = QTimer()
		self.timer.setSingleShot(True)
		self.timer.timeout.connect(self.refold)
		self.start = 0

	@Slot()
	def refold(self):
		n = self.editor.getFoldLevel(self.start) & QsciScintilla.SC_FOLDLEVELNUMBERMASK

		first = True
		for i in range(self.start, self.editor.lines()):
			if not first:
				self.editor.setFoldLevel(i, n)
			first = False

			line = self.editor.text(i)
			diff = header = len(self.markerStart.findall(line))
			diff -= len(self.markerEnd.findall(line))
			if header:
				self.editor.setFoldLevel(i, n | QsciScintilla.SC_FOLDLEVELHEADERFLAG)
			n += diff

	@Slot(object)
	def onModification(self, st):
		refold = None

		pos, ev, text, length, added, line, folda, foldb, tok, anno = st
		if ev & QsciScintilla.SC_MOD_INSERTTEXT:
			refold, _ = self.editor.lineIndexFromPosition(pos)
		elif ev & QsciScintilla.SC_MOD_DELETETEXT:
			refold, _ = self.editor.lineIndexFromPosition(pos)

		if refold is not None:
			if self.timer.isActive():
				self.start = min(self.start, refold)
			else:
				self.start = refold
				self.timer.start(self.interval)

		# TODO smarter refold: check if insert/delete contains pattern or changes folding
