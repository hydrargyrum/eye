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
		self.timer.timeout.connect(self.refoldQueue)
		self.linesToRefold = set()

	@Slot()
	def refold(self, force=False):
		self.refoldAt(0, force)

	@Slot()
	def refoldQueue(self, force=False):
		while len(self.linesToRefold):
			start = self.linesToRefold.pop()
			self.refoldAt(start, force)

	def refoldAt(self, start, force=False):
		waitnext = True
		level = self.editor.getFoldLevel(start) & QsciScintilla.SC_FOLDLEVELNUMBERMASK
		for i in range(start, self.editor.lines()):
			self.linesToRefold.discard(i)
			flag = 0

			line = self.editor.text(i)
			diff = len(self.markerStart.findall(line))
			if diff:
				flag |= QsciScintilla.SC_FOLDLEVELHEADERFLAG
			diff -= len(self.markerEnd.findall(line))

			new = level | flag
			current = self.editor.getFoldLevel(i)
			if force or current != new:
				self.editor.setFoldLevel(i, new)
				waitnext = True
			else:
				if not waitnext:
					break
				waitnext = False

			level += diff

	@Slot(object)
	def onModification(self, st):
		refold = None

		pos, ev, text, length, added, line, folda, foldb, tok, anno = st
		if ev & QsciScintilla.SC_MOD_INSERTTEXT:
			refold, _ = self.editor.lineIndexFromPosition(pos)
		elif ev & QsciScintilla.SC_MOD_DELETETEXT:
			refold, _ = self.editor.lineIndexFromPosition(pos)

		if refold is not None:
			self.linesToRefold.add(refold)
			if not self.timer.isActive():
				self.timer.start(self.interval)

		# TODO smarter refold: check if insert/delete contains pattern or changes folding
