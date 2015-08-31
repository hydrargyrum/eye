
from PyQt4.QtGui import QFont
from PyQt4.Qsci import QsciScintilla

from ConfigParser import SafeConfigParser
from logging import getLogger

from ..connector import categoryObjects, registerSignal, disabled
from ..utils import ignoreExceptions
from ..colorutils import QColorAlpha
from ..lexers import stylesFromLexer
from ._lexercolorgroups import getIdAndAliases

__all__ = ('readScheme', 'applySchemeToEditor', 'applySchemeOnLexerChange', 'useSchemeFile')


LOGGER = getLogger(__name__)

FG_ATTRS = frozenset(['fg', 'foreground', 'color'])
BG_ATTRS = frozenset(['bg', 'background'])

SCHEME = None

def readScheme(path):
	parser = SafeConfigParser()
	parser.optionxform = unicode
	parser.read([path])
	return parser


def fuzzyEquals(a, b):
	def norm(name):
		return name.lower().replace(' ', '_')
	return norm(a) == norm(b)

def getStyleByDesc(lexer, desc, fuzzy=False):
	for i in xrange(1 << lexer.styleBitsNeeded()):
		idesc = lexer.description(i)
		if idesc == desc or (fuzzy and fuzzyEquals(desc, idesc)):
			return i

def parseBool(s):
	if s in ['1', 'true', 'yes', 'y', 'on']:
		return True
	elif s in ['0', 'false', 'no', 'n', 'off']:
		return False
	raise ValueError('%r is not a boolean value' % s)


class LexerModificator(object):
	def __init__(self, lexer, ids):
		self.lexer = lexer
		self.ids = ids

	def apply(self, attr, strvalue):
		for id in self.ids:
			self.applyOne(id, attr, strvalue)

	def applyOne(self, styleId, attr, strvalue):
		if attr == 'font':
			font = self.lexer.font(styleId)
			font.setFamily(strvalue)
			self.lexer.setFont(font, styleId)
		elif attr == 'bold':
			font = self.lexer.font(styleId)
			font.setBold(parseBool(strvalue))
			self.lexer.setFont(font, styleId)
		elif attr == 'italic':
			font = self.lexer.font(styleId)
			font.setItalic(parseBool(strvalue))
			self.lexer.setFont(font, styleId)
		elif attr == 'underline':
			font = self.lexer.font(styleId)
			font.setUnderline(parseBool(strvalue))
			self.lexer.setFont(font, styleId)
		elif attr in FG_ATTRS:
			self.lexer.setColor(QColorAlpha(strvalue), styleId)
		elif attr in BG_ATTRS:
			self.lexer.setPaper(QColorAlpha(strvalue), styleId)


class EditorModificator(object):
	PROPS = ['_caret', '_selection', '_matchedbrace', '_unmatchedbrace', '_whitespace', '_hotspot']

	def __init__(self, editor, prop):
		self.editor = editor
		self.prop = prop

	def unsupported(self, attr):
		LOGGER.warning('%s.%s is not supported', self.prop, attr)

	def applyCaret(self, attr, strvalue):
		if attr in FG_ATTRS:
			qc = QColorAlpha(strvalue)
			self.editor.setCaretForegroundColor(qc)
		elif attr in BG_ATTRS:
			qc = QColorAlpha(strvalue)
			self.editor.setCaretLineBackgroundColor(qc)
		else:
			self.unsupported(attr)

	def applySelection(self, attr, strvalue):
		self.applyBasic('Selection', attr, strvalue)

	def applyMB(self, attr, strvalue):
		self.applyBasic('MatchedBrace', attr, strvalue)

	def applyUB(self, attr, strvalue):
		self.applyBasic('UnmatchedBrace', attr, strvalue)

	def applyWS(self, attr, strvalue):
		self.applyBasic('Whitespace', attr, strvalue)

	def applyHotspot(self, attr, strvalue):
		self.applyBasic('Hotspot', attr, strvalue)

	def applyBasic(self, edAttr, attr, strvalue):
		if attr in FG_ATTRS:
			edAttr = 'set%sForegroundColor' % edAttr
			qc = QColorAlpha(strvalue)
			getattr(self.editor, edAttr)(qc)
		elif attr in BG_ATTRS:
			edAttr = 'set%sBackgroundColor' % edAttr
			qc = QColorAlpha(strvalue)
			getattr(self.editor, edAttr)(qc)
		else:
			self.unsupported(attr)


	def apply(self, attr, strvalue):
		d = {
			'_caret': self.applyCaret, '_selection': self.applySelection,
			'_matchedbrace': self.applyMB, '_hotspot': self.applyHotspot,
			'_unmatchedbrace': self.applyUB,
			'_whitespace': self.applyWS
		}
		d[self.prop](attr, strvalue)


def matchingStyles(lexer, name):
	base_style = 'STYLE%s' % name.upper()

	if name in EditorModificator.PROPS:
		return EditorModificator(lexer.editor(), name)
	elif name == '*':
		return LexerModificator(lexer, stylesFromLexer(lexer).values())
	elif hasattr(QsciScintilla, base_style):
		return LexerModificator(lexer, [getattr(QsciScintilla, base_style)])
	elif name.isdigit():
		return LexerModificator(lexer, [int(name)])
	else:
		return LexerModificator(lexer, getIdAndAliases(type(lexer), name))


def applySchemeToEditor(parser, editor):
	lexer = editor.lexer()

	lexer_name = lexer.language() if lexer else 'None'
	for section in ('*', lexer_name):
		if parser.has_section(section):
			LOGGER.debug('using section %r', section)
			for key in parser.options(section):
				try:
					stylename, attr = key.split('.')
				except ValueError as e:
					LOGGER.info('ignoring style key %r', key)
					continue
				value = parser.get(section, key)

				modificator = matchingStyles(lexer, stylename)
				modificator.apply(attr, value)


def useSchemeFile(path, applyToAll=True):
	global SCHEME

	if path is None:
		SCHEME = None
		return
	else:
		SCHEME = readScheme(path)

	if applyToAll:
		for ed in categoryObjects('editor'):
			lexer = ed.lexer()
			if lexer is not None:
				applySchemeToLexer(SCHEME, ed.lexer())


@registerSignal('editor', 'lexerChanged')
@disabled
def applySchemeOnLexerChange(editor, lexer):
	if not lexer:
		return
	if SCHEME:
		applySchemeToEditor(SCHEME, editor)
