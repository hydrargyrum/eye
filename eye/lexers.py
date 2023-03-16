# this project is licensed under the WTFPLv2, see COPYING.txt for details

"""Helpers for lexer use

In EYE, builtin lexers from QScintilla are used. See :any:`PyQt5.Qsci.QsciLexer`.
"""

import mimetypes

from PyQt5.QtGui import QColor, QFont
from PyQt5.Qsci import (
	QsciLexerBash, QsciLexerBatch, QsciLexerCPP, QsciLexerCSharp, QsciLexerJava, QsciLexerJavaScript,
	QsciLexerCSS, QsciLexerD, QsciLexerFortran, QsciLexerHTML, QsciLexerXML, QsciLexerLua,
	QsciLexerMakefile, QsciLexerPascal, QsciLexerPerl, QsciLexerPO, QsciLexerPostScript,
	QsciLexerPOV, QsciLexerProperties, QsciLexerPython, QsciLexerRuby, QsciLexerSQL, QsciLexerTCL,
	QsciLexerTeX, QsciLexerYAML, QsciLexerDiff,
)

__all__ = ('extension_to_lexer', 'mime_to_lexer', 'apply_styles', 'styles_from_lexer')


def styles_from_lexer(lexer):
	"""Return the style names used by a Qsci_lexer object

	Lexers provide a number of styles names, like "Comment", "Operator", "Identifier", etc.
	"""
	styles = {}
	for i in range(1 << lexer.styleBitsNeeded()):
		name = lexer.description(i)
		if not name:
			break
		styles[name] = i
	return styles


def apply_styles(lexer, spec):
	styles = styles_from_lexer(lexer)

	for name, values in spec:
		style = styles.get(name, -1)
		if style >= 0:
			lexer.set_color(QColor(values[0]))
			if len(values) > 1:
				lexer.set_paper(QColor(values[1]))
			if len(values) > 2:
				lexer.set_font(QFont(values[2]))


_extension_lexer = {
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
	'patch': QsciLexerDiff,
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


def extension_to_lexer(ext):
	"""Return a QsciLexer corresponding to extension

	If no appropriate lexer is found for `ext`, `None` is returned.
	"""
	if ext and ext.startswith('.'):
		ext = ext[1:]
	return _extension_lexer.get(ext)


def mime_to_lexer(mime):
	"""Return a QsciLexer corresponding to mimetype

	If no appropriate lexer is found for `mime`, `None` is returned.
	"""
	return extension_to_lexer(mimetypes.guess_extension(mime))
