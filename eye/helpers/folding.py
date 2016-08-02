# this project is licensed under the WTFPLv2, see COPYING.txt for details

"""Plugin for non-lexical code folding

Default lexers provide code folding, for example functions can be folded. This plugin provides folding that isn't
based on lexer tokens but on markers. For example "{{{" for starting a fold zone and "}}}" for ending a fold zone.

Simple usage:

	>>> import eye.helpers.folding
	>>> eye.helpers.folding.setMarkerFolder.enabled = True
"""

from PyQt5.QtCore import QObject, QTimer
from PyQt5.Qsci import QsciScintilla

import re

from ..connector import disabled, defaultLexerConfig, defaultEditorConfig
from ..widgets.editor import HasWeakEditorMixin
from ..qt import Slot


__all__ = ('MarkerFolder', 'disableLexerFolding', 'setMarkerFolder')


@defaultLexerConfig
@disabled
def disableLexerFolding(ed, *args):
	"""Disable folding based on QsciLexer for an editor widget"""
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

		if editor:
			self.refold(True)

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

		if st.modificationType & QsciScintilla.SC_MOD_INSERTTEXT:
			refold, _ = self.editor.lineIndexFromPosition(st.position)
		elif st.modificationType & QsciScintilla.SC_MOD_DELETETEXT:
			refold, _ = self.editor.lineIndexFromPosition(st.position)

		if refold is not None:
			self.linesToRefold.add(refold)
			if not self.timer.isActive():
				self.timer.start(self.interval)

		# TODO smarter refold: check if insert/delete contains pattern or changes folding


@defaultEditorConfig
@defaultLexerConfig
@disabled
def setMarkerFolder(editor, *args):
	"""Enable folding based on markers for an editor widget"""
	editor.setLexerProperty(b'fold', b'0')
	editor.folding = MarkerFolder(editor=editor)
