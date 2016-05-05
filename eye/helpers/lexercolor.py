# this project is licensed under the WTFPLv2, see COPYING.txt for details

from six.moves.configparser import SafeConfigParser
from logging import getLogger

from ..three import str
from ..connector import categoryObjects, registerSignal, disabled
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


class Modificator(object):
	def __init__(self, editor, key, strvalue):
		self.editor = editor
		self.key = key
		self.strvalue = strvalue


class LexerModificator(Modificator):
	def apply(self):
		tokenname, attr = self.key.split('.')

		lexer = self.editor.lexer()
		if not lexer:
			return

		if tokenname == '*':
			ids = stylesFromLexer(lexer).values()
		elif tokenname == '_default':
			ids = [self.editor.STYLE_DEFAULT]
		else:
			ids = getIdAndAliases(type(lexer), tokenname)

		for id in ids:
			self.applyOne(id, attr)

	def applyOne(self, styleId, attr):
		lexer = self.editor.lexer()

		if attr == 'font':
			self.applyFont(styleId, 'Family', self.strvalue)
		elif attr == 'points':
			self.applyFont(styleId, 'PointSizeF', float(self.strvalue))
		elif attr == 'bold':
			self.applyFont(styleId, 'Bold', parseBool(self.strvalue))
		elif attr == 'italic':
			self.applyFont(styleId, 'Italic', parseBool(self.strvalue))
		elif attr == 'underline':
			self.applyFont(styleId, 'Underline', parseBool(self.strvalue))
		elif attr in FG_ATTRS:
			lexer.setColor(QColorAlpha(self.strvalue), styleId)
		elif attr in BG_ATTRS:
			lexer.setPaper(QColorAlpha(self.strvalue), styleId)

	def applyFont(self, styleId, fontAttr, value):
		lexer = self.editor.lexer()
		font = lexer.font(styleId)
		fontAttr = 'set%s' % fontAttr
		getattr(font, fontAttr)(value)
		lexer.setFont(font, styleId)


class EditorModificator(Modificator):
	def apply(self):
		self.element, attr = self.key.split('.')

		d = {
			'text': self.applyText,
			'whitespace': self.applyWS,
			'caret': self.applyCaret,
			'selection': self.applySelection,
			'hotspot': self.applyHotspot,
			'matchedbrace': self.applyMB,
			'unmatchedbrace': self.applyUB,
		}

		d[self.element](attr, self.strvalue)

	def unsupported(self, attr):
		LOGGER.warning('%s.%s is not supported', self.element, attr)

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

	def applyText(self, attr, strvalue):
		if attr in FG_ATTRS:
			qc = QColorAlpha(strvalue)
			self.editor.setColor(qc)
		elif attr in BG_ATTRS:
			qc = QColorAlpha(strvalue)
			self.editor.setPaper(qc)
		elif attr == 'font':
			self.applyFont('Family', strvalue)
		elif attr == 'points':
			self.applyFont('PointSizeF', float(strvalue))
		elif attr == 'bold':
			self.applyFont('Bold', parseBool(strvalue))
		elif attr == 'italic':
			self.applyFont('Italic', parseBool(strvalue))
		elif attr == 'underline':
			self.applyFont('Underline', parseBool(strvalue))

	def applyFont(self, fontAttr, value):
		font = self.editor.font()
		fontAttr = 'set%s' % fontAttr
		getattr(font, fontAttr)(value)
		self.editor.setFont(font)


def IndicatorModificator(Modificator):
	pass


def getModificator(name):
	modificators = {
		'token': LexerModificator,
		'indicator': IndicatorModificator,
		'base': EditorModificator,
	}

	return modificators.get(name)


def applySchemeDictToEditor(dct, editor):
	for key, value in dct.items():
		try:
			styletype, subkey = key.split('.', 1)
		except ValueError:
			LOGGER.info('ignoring malformed style key %r', key)
			continue

		modificator_type = getModificator(styletype)
		if modificator_type is None:
			LOGGER.info('ignoring unknown style type %r', styletype)
			continue

		mod = modificator_type(editor, subkey, value)
		mod.apply()


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
