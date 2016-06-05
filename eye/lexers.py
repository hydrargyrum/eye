# this project is licensed under the WTFPLv2, see COPYING.txt for details

"""Helpers for lexer use

In EYE, builtin lexers from QScintilla are used. See :any:`PyQt5.Qsci.QsciLexer`.
"""

from PyQt5.QtGui import QColor, QFont
from PyQt5.Qsci import (
	QsciLexerBash, QsciLexerBatch, QsciLexerCPP, QsciLexerCSharp, QsciLexerJava, QsciLexerJavaScript,
	QsciLexerCSS, QsciLexerD, QsciLexerFortran, QsciLexerHTML, QsciLexerXML, QsciLexerLua, QsciLexerMakefile,
	QsciLexerPascal, QsciLexerPerl, QsciLexerPO, QsciLexerPostScript, QsciLexerPOV, QsciLexerProperties,
	QsciLexerPython, QsciLexerRuby, QsciLexerSQL, QsciLexerTCL, QsciLexerTeX, QsciLexerYAML,
)

import mimetypes


__all__ = ('extensionToLexer', 'mimeToLexer', 'applyStyles', 'stylesFromLexer')


def stylesFromLexer(lexer):
	"""Return the style names used by a QsciLexer object

	Lexers provide a number of styles names, like "Comment", "Operator", "Identifier", etc.
	"""
	styles = {}
	for i in range(1 << lexer.styleBitsNeeded()):
		name = lexer.description(i)
		if not name:
			break
		styles[name] = i
	return styles


def applyStyles(lexer, spec):
	styles = stylesFromLexer(lexer)

	for name, values in spec:
		style = styles.get(name, -1)
		if style >= 0:
			lexer.setColor(QColor(values[0]))
			if len(values) > 1:
				lexer.setPaper(QColor(values[1]))
			if len(values) > 2:
				lexer.setFont(QFont(values[2]))


_extensionLexer = {
	'sh': QsciLexerBash,
	'bash': QsciLexerBash,
	'zsh': QsciLexerBash,
	'bat': QsciLexerBatch,
	'cmd': QsciLexerBatch,
	'c': QsciLexerCPP,
	'cc': QsciLexerCPP,
	'cpp': QsciLexerCPP,
	'cxx': QsciLexerCPP,
	'h': QsciLexerCPP,
	'hh': QsciLexerCPP,
	'hpp': QsciLexerCPP,
	'hxx': QsciLexerCPP,
	'cs': QsciLexerCSharp,
	'java': QsciLexerJava,
	'js': QsciLexerJavaScript,
	'json': QsciLexerJavaScript,
	'css': QsciLexerCSS,
	'd': QsciLexerD,
	'f': QsciLexerFortran,
	'html': QsciLexerHTML,
	'htm': QsciLexerHTML,
	'xml': QsciLexerXML,
	'lua': QsciLexerLua,
	'Makefile': QsciLexerMakefile,
	'pas': QsciLexerPascal,
	'pl': QsciLexerPerl,
	'pm': QsciLexerPerl,
	'po': QsciLexerPO,
	'pot': QsciLexerPO,
	'ps': QsciLexerPostScript,
	'pov': QsciLexerPOV,
	'inc': QsciLexerPOV,
	'properties': QsciLexerProperties,
	'ini': QsciLexerProperties,
	'py': QsciLexerPython,
	'rb': QsciLexerRuby,
	'sql': QsciLexerSQL,
	'tcl': QsciLexerTCL,
	'tex': QsciLexerTeX,
	'yaml': QsciLexerYAML,
	'yml': QsciLexerYAML,
}


def extensionToLexer(ext):
	"""Return a QsciLexer corresponding to extension

	If no appropriate lexer is found for `ext`, `None` is returned.
	"""
	if ext and ext.startswith('.'):
		ext = ext[1:]
	return _extensionLexer.get(ext)


def mimeToLexer(mime):
	"""Return a QsciLexer corresponding to mimetype

	If no appropriate lexer is found for `mime`, `None` is returned.
	"""
	return extensionToLexer(mimetypes.guess_extension(mime))
