# this project is licensed under the WTFPLv2, see COPYING.txt for details

from PyQt5.QtGui import QColor, QFont
from PyQt5.Qsci import QsciLexerBash, QsciLexerBatch, QsciLexerCPP
from PyQt5.Qsci import QsciLexerCSharp, QsciLexerJava, QsciLexerJavaScript
from PyQt5.Qsci import QsciLexerCSS, QsciLexerD, QsciLexerFortran
from PyQt5.Qsci import QsciLexerHTML, QsciLexerXML, QsciLexerLua
from PyQt5.Qsci import QsciLexerMakefile, QsciLexerPascal, QsciLexerPerl
from PyQt5.Qsci import QsciLexerPO, QsciLexerPostScript, QsciLexerPOV
from PyQt5.Qsci import QsciLexerProperties, QsciLexerPython, QsciLexerRuby
from PyQt5.Qsci import QsciLexerSQL, QsciLexerTCL, QsciLexerTeX
from PyQt5.Qsci import QsciLexerYAML

import re
import mimetypes

__all__ = ('applyStyles', 'extensionToLexer', 'mimeToLexer', 'stylesFromLexer')

def stylesFromLexer(lexer):
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
	if ext and ext.startswith('.'):
		ext = ext[1:]
	return _extensionLexer.get(ext)

def mimeToLexer(mime):
	return extensionToLexer(mimetypes.guess_extension(mime))
