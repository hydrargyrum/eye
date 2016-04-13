# this project is licensed under the WTFPLv2, see COPYING.txt for details

from ConfigParser import SafeConfigParser
from logging import getLogger

from ..three import str
from ..connector import categoryObjects, registerSignal, disabled
from ..utils import ignoreExceptions
from ..colorutils import QColorAlpha
from ..lexers import stylesFromLexer
from ._lexercolorgroups import getIdAndAliases

__all__ = ('readScheme', 'applySchemeToEditor', 'applySchemeDictToEditor',
           'applySchemeOnLexerChange', 'useSchemeFile')


LOGGER = getLogger(__name__)

FG_ATTRS = frozenset(['fg', 'foreground', 'color'])
BG_ATTRS = frozenset(['bg', 'background'])

SCHEME = None

def readScheme(path):
	parser = SafeConfigParser()
	parser.optionxform = str
	parser.read([path])
	return parser


def fuzzyEquals(a, b):
	def norm(name):
		return name.lower().replace(' ', '_')
	return norm(a) == norm(b)

def getStyleByDesc(lexer, desc, fuzzy=False):
	for i in range(1 << lexer.styleBitsNeeded()):
		idesc = lexer.description(i)
		if idesc == desc or (fuzzy and fuzzyEquals(desc, idesc)):
			return i

def parseBool(s):
	if s in ['1', 'true', 'yes', 'y', 'on']:
		return True
	elif s in ['0', 'false', 'no', 'n', 'off']:
		return False
	raise ValueError('%r is not a boolean value' % s)


def lexerModificator(tokenname, attr, strvalue, editor):
	def applyOne(styleId, attr, strvalue):
		if attr == 'font':
			font = lexer.font(styleId)
			font.setFamily(strvalue)
			lexer.setFont(font, styleId)
		elif attr == 'bold':
			font = lexer.font(styleId)
			font.setBold(parseBool(strvalue))
			lexer.setFont(font, styleId)
		elif attr == 'italic':
			font = lexer.font(styleId)
			font.setItalic(parseBool(strvalue))
			lexer.setFont(font, styleId)
		elif attr == 'underline':
			font = lexer.font(styleId)
			font.setUnderline(parseBool(strvalue))
			lexer.setFont(font, styleId)
		elif attr in FG_ATTRS:
			lexer.setColor(QColorAlpha(strvalue), styleId)
		elif attr in BG_ATTRS:
			lexer.setPaper(QColorAlpha(strvalue), styleId)

	lexer = editor.lexer()
	if not lexer:
		return
	if tokenname == '*':
		ids = stylesFromLexer(lexer).values()
	elif tokenname == '_default':
		ids = [editor.STYLE_DEFAULT]
	else:
		ids = getIdAndAliases(type(lexer), tokenname)

	for id in ids:
		applyOne(id, attr, strvalue)


def editorModificator(element, attr, strvalue, editor):
	def unsupported(attr):
		LOGGER.warning('%s.%s is not supported', element, attr)

	def applyCaret(attr, strvalue):
		if attr in FG_ATTRS:
			qc = QColorAlpha(strvalue)
			editor.setCaretForegroundColor(qc)
		elif attr in BG_ATTRS:
			qc = QColorAlpha(strvalue)
			editor.setCaretLineBackgroundColor(qc)
		else:
			unsupported(attr)

	def applySelection(attr, strvalue):
		applyBasic('Selection', attr, strvalue)

	def applyMB(attr, strvalue):
		applyBasic('MatchedBrace', attr, strvalue)

	def applyUB(attr, strvalue):
		applyBasic('UnmatchedBrace', attr, strvalue)

	def applyWS(attr, strvalue):
		applyBasic('Whitespace', attr, strvalue)

	def applyHotspot(attr, strvalue):
		applyBasic('Hotspot', attr, strvalue)

	def applyBasic(edAttr, attr, strvalue):
		if attr in FG_ATTRS:
			edAttr = 'set%sForegroundColor' % edAttr
			qc = QColorAlpha(strvalue)
			getattr(editor, edAttr)(qc)
		elif attr in BG_ATTRS:
			edAttr = 'set%sBackgroundColor' % edAttr
			qc = QColorAlpha(strvalue)
			getattr(editor, edAttr)(qc)
		else:
			unsupported(attr)

	def applyText(attr, strvalue):
		if attr in FG_ATTRS:
			qc = QColorAlpha(strvalue)
			editor.setColor(qc)
		elif attr in BG_ATTRS:
			qc = QColorAlpha(strvalue)
			editor.setPaper(qc)
		elif attr == 'font':
			font = editor.font()
			font.setFamily(strvalue)
			editor.setFont(font)
		elif attr == 'bold':
			font = editor.font()
			font.setBold(parseBool(strvalue))
			editor.setFont(font)
		elif attr == 'italic':
			font = editor.font()
			font.setItalic(parseBool(strvalue))
			editor.setFont(font)
		elif attr == 'underline':
			font = editor.font()
			font.setUnderline(parseBool(strvalue))
			editor.setFont(font)

	d = {
		'caret': applyCaret, 'selection': applySelection,
		'matchedbrace': applyMB, 'hotspot': applyHotspot,
		'unmatchedbrace': applyUB,
		'whitespace': applyWS, 'text': applyText
	}
	d[element](attr, strvalue)


def indicatorModificator(name, attr, strvalue, editor):
	pass


def getModificator(name):
	if name == 'token':
		return lexerModificator
	elif name == 'indicator':
		return indicatorModificator
	elif name == 'base':
		return editorModificator


def applySchemeDictToEditor(dct, editor):
	lexer = editor.lexer()

	for key, value in dct.items():
		try:
			styletype, stylename, attr = key.split('.')
		except ValueError as e:
			LOGGER.info('ignoring style key %r', key)
			continue

		modificator = getModificator(styletype)
		modificator(stylename, attr, value, editor)


def applySchemeToEditor(parser, editor):
	lexer = editor.lexer()

	lexer_name = lexer.language() if lexer else 'None'
	for section in ('*', lexer_name):
		if parser.has_section(section):
			LOGGER.debug('using section %r for file %r', section, editor.path)

			dict_scheme = dict(parser.items(section))
			applySchemeDictToEditor(dict_scheme, editor)


def useSchemeFile(path, applyToAll=True):
	global SCHEME

	if path is None:
		SCHEME = None
		LOGGER.info('unsetting scheme file')
		return
	else:
		SCHEME = readScheme(path)
		LOGGER.info('using scheme file %r', path)

	if applyToAll:
		for ed in categoryObjects('editor'):
			applySchemeToEditor(SCHEME, ed)


@registerSignal('editor', 'connected')
@disabled
def applySchemeOnCreate(editor):
	if SCHEME:
		applySchemeToEditor(SCHEME, editor)


@registerSignal('editor', 'lexerChanged')
@disabled
def applySchemeOnLexerChange(editor, lexer):
	if SCHEME:
		applySchemeToEditor(SCHEME, editor)
