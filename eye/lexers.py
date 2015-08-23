
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.Qsci import *

import re
import mimetypes

__all__ = ('applyStyles', 'extensionToLexer', 'mimeToLexer')

def stylesFromLexer(lexer):
	styles = {}
	for i in xrange(i << lexer.styleBitsNeeded()):
		name = obj.description(i)
		if not n:
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
