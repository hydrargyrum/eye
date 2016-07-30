# this project is licensed under the WTFPLv2, see COPYING.txt for details

"""Color scheme application

This plugin allows to load color scheme definition from a file and apply them to editor and syntax coloring.

Color scheme format
===================

Color scheme files are in INI format (as read by `configparser`). A scheme file sets style attributes for multiples
lexers and such descriptions can be applied to an editor.

Sections
--------

A color scheme file consist in one or more INI sections, each corresponding to a lexer.
The special section `*` applies to all lexers. When applying a color scheme to an editor, the `*` section is applied
first if it exists, then the section for the lexer of the editor is applied, if it exists and if the editor has
a lexer.

Attributes
----------

Within a section, there are multiple entries in the form: `item_kind.item_name.style_property = style_value`.

The `item_kind.item_name` part specifies for which items of the lexer it should apply, for example:
the "keyword" token, the "search" indicator, or simply the caret style.

The `style_property` indicates what attribute should be set, for example: the font size, the background color.

Finally, the `style_value` is the value the `style_property` should be set to, for example: a color, a size, a
font name.

Item types
----------

Editor properties
+++++++++++++++++

If `item_kind` is `base`, `item_name` can be:

* `text`: applies to normal text
* `selection`': applies to selected text
* `whitespace`
* `caret`: applies to caret, for `foreground`, or whole line under cursor, for `background` (if set visible)
* `hotspot`
* `matchedbrace`: for a brace under cursor, which has a corresponding matching brace
* `unmatchedbrace`: for a brace under cursor, which doesn't have a corresponding matching brace
* `margin`: for the margin column

The valid `style_property` are `foreground`, `background`, `font`, `points`, `bold`, `italic`, `underline`.

Tokens
++++++

If `item_kind` is `token`, `item_name` is the token name, which corresponds to one style in `QsciLexer`.

The token name `*` is special: it matches all tokens, and is applied first, so it can be overwritten by more
specific color scheme entries.

The valid `style_property` are `foreground`, `background`, `font`, `points`, `bold`, `italic`, `underline`.

Styles
++++++

If `item_kind` is `style`, `item_name` is the style name, as registered in :any:`eye.helpers.styles`.

The valid `style_property` are `foreground`, `background`, `font`, `points`, `bold`, `italic`, `underline` and
`eolfill`.

Indicators
++++++++++

If `item_kind` is `indicator`, `item_name` is the indicator name (see :any:`eye.widgets.editor.Editor.indicators`)

The valid `style_property` are: `foreground`, `background` and `style`.

Property types
--------------

* `foreground` (or `fg`, or `color`) specifies the text color
* `background` (or `bg`) specifies the background color

* `font` specifies the font family (font name)
* `points` specifies the font size in points

* `bold` specifies whether the font is bold
* `italic` specifies whether the font is italic
* `underline` specifies whether the font is underline

* `eolfill` specifies whether the background color applies to the rest of the line, after last character

* `style` specifies which indicator style should be used, e.g. `StraightBoxIndicator`


Module contents
===============

"""

from six.moves.configparser import SafeConfigParser
from logging import getLogger

from ..three import str
from ..connector import categoryObjects, registerSignal, registerSetup, disabled
from ..colorutils import QColorAlpha
from ..lexers import stylesFromLexer
from ._lexercolorgroups import getIdAndAliases
from .styles import STYLES

__all__ = ('setEnabled', 'useSchemeFile', 'addSchemeFile',
           'lexerSetFontFamily', 'lexerSetFontPointSize',
           'applySchemeToEditor', 'applySchemeDictToEditor',
           'applySchemeOnLexerChange', 'applySchemeOnCreate')


LOGGER = getLogger(__name__)

FG_ATTRS = frozenset(['fg', 'foreground', 'color'])
BG_ATTRS = frozenset(['bg', 'background'])

SCHEME = None


def newScheme():
	parser = SafeConfigParser()
	parser.optionxform = str
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
	s = s.lower()
	if s in ['1', 'true', 'yes', 'y', 'on']:
		return True
	elif s in ['0', 'false', 'no', 'n', 'off']:
		return False
	raise ValueError('%r is not a boolean value' % s)


class UnsupportedModification(Exception):
	pass


class Modificator(object):
	def __init__(self, editor, key, strvalue):
		self.editor = editor
		self.key = key
		self.strvalue = strvalue

	def applyGeneric(self, attr, *args):
		if attr == 'font':
			self.setFont('Family', self.strvalue, *args)
		elif attr == 'points':
			self.setFont('PointSizeF', float(self.strvalue), *args)
		elif attr == 'bold':
			self.setFont('Bold', parseBool(self.strvalue), *args)
		elif attr == 'italic':
			self.setFont('Italic', parseBool(self.strvalue), *args)
		elif attr == 'underline':
			self.setFont('Underline', parseBool(self.strvalue), *args)
		elif attr in FG_ATTRS:
			self.setColor(QColorAlpha(self.strvalue), *args)
		elif attr in BG_ATTRS:
			self.setPaper(QColorAlpha(self.strvalue), *args)
		else:
			raise UnsupportedModification()


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
			ids = getIdAndAliases(lexer, tokenname)

		for id in ids:
			self.applyOne(id, attr)

	def applyOne(self, styleId, attr):
		lexer = self.editor.lexer()

		self.applyGeneric(attr, lexer, styleId)

	def applyGeneric(self, attr, lexer, styleId):
		if attr == 'eolfill':
			lexer.setEolFill(parseBool(self.strvalue))
		else:
			super(LexerModificator, self).applyGeneric(attr, lexer, styleId)

	def setColor(self, qc, lexer, styleId):
		lexer.setColor(QColorAlpha(self.strvalue), styleId)

	def setPaper(self, qc, lexer, styleId):
		lexer.setPaper(QColorAlpha(self.strvalue), styleId)

	def setFont(self, fontAttr, value, lexer, styleId):
		font = lexer.font(styleId)
		fontAttr = 'set%s' % fontAttr
		getattr(font, fontAttr)(value)
		lexer.setFont(font, styleId)


class EditorModificator(Modificator):
	def apply(self):
		element, attr = self.key.split('.')
		self.applyGeneric(attr, element)

	def applyCaret(self, attr, strvalue):
		if attr in FG_ATTRS:
			qc = QColorAlpha(strvalue)
			self.editor.setCaretForegroundColor(qc)
		elif attr in BG_ATTRS:
			qc = QColorAlpha(strvalue)
			self.editor.setCaretLineBackgroundColor(qc)
		else:
			raise UnsupportedModification('only elements in %s are supported for caret' % (FG_ATTRS + BG_ATTRS))

	def setColor(self, qc, element):
		attrs = {
			'text': 'setColor',
			'selection': 'setSelectionForegroundColor',
			'whitespace': 'setWhitespaceForegroundColor',
			'caret': 'setCaretForegroundColor',
			'hotspot': 'setHotspotForegroundColor',
			'matchedbrace': 'setMatchedBraceForegroundColor',
			'unmatchedbrace': 'setUnmatchedBraceForegroundColor',
			'margin': 'setMarginsForegroundColor',
		}

		getattr(self.editor, attrs[element])(qc)

	def setPaper(self, qc, element):
		attrs = {
			'text': 'setPaper',
			'selection': 'setSelectionBackgroundColor',
			'whitespace': 'setWhitespaceBackgroundColor',
			'caret': 'setCaretLineBackgroundColor',
			'hotspot': 'setHotspotBackgroundColor',
			'matchedbrace': 'setMatchedBraceBackgroundColor',
			'unmatchedbrace': 'setUnmatchedBraceBackgroundColor',
			'margin': 'setMarginsBackgroundColor',
		}

		getattr(self.editor, attrs[element])(qc)

	def setFont(self, fontAttr, value, element):
		if element != 'text':
			raise UnsupportedModification('only "text" is supported')
		# margin.* lacks a Editor.marginsFont()

		font = self.editor.font()
		fontAttr = 'set%s' % fontAttr
		getattr(font, fontAttr)(value)
		self.editor.setFont(font)


class IndicatorModificator(Modificator):
	def apply(self):
		name, attr = self.key.split('.')

		indicator = self.editor.indicators.get(name)
		if not indicator:
			indicator = self.editor.createIndicator(name, self.editor.PlainIndicator)

		self.applyGeneric(attr, indicator)

	def applyGeneric(self, attr, indicator):
		if attr == 'style':
			indicator.setStyle(getattr(self.editor, self.strvalue))
		else:
			super(IndicatorModificator, self).applyGeneric(attr, indicator)

	def setColor(self, qc, indicator):
		indicator.setColor(qc)

	def setPaper(self, qc, indicator):
		indicator.setOutlineColor(qc)

	def setFont(self, *args):
		raise UnsupportedModification('font cannot be set for indicators')


class StyleModificator(Modificator):
	def apply(self):
		name, attr = self.key.split('.')

		self.applyGeneric(attr, STYLES[name])

	def applyGeneric(self, attr, style):
		if attr == 'eolfill':
			style.setEolFill(parseBool(self.strvalue))
		else:
			super(StyleModificator, self).applyGeneric(attr, style)

	def setFont(self, fontAttr, value, style):
		font = style.font()
		fontAttr = 'set%s' % fontAttr
		getattr(font, fontAttr)(value)
		style.setFont(font)

	def setColor(self, qc, style):
		style.setColor(qc)

	def setPaper(self, qc, style):
		style.setPaper(qc)


def getModificator(name):
	modificators = {
		'token': LexerModificator,
		'indicator': IndicatorModificator,
		'base': EditorModificator,
		'style': StyleModificator,
	}

	return modificators.get(name)


def applySchemeDictToEditor(dct, editor):
	for key in sorted(dct):
		value = dct[key]
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
		try:
			mod.apply()
		except UnsupportedModification as exc:
			LOGGER.warning('%s is not supported: %s', key, exc.message)
			continue

		LOGGER.debug('applied %r=%r to %r', key, value, editor)


def applySchemeToEditor(parser, editor):
	lexer = editor.lexer()

	lexer_name = lexer.language() if lexer else 'None'
	for section in ('*', lexer_name):
		if parser.has_section(section):
			LOGGER.debug('using section %r for file %r', section, editor.path)

			dict_scheme = dict(parser.items(section))
			applySchemeDictToEditor(dict_scheme, editor)


def useSchemeFile(path, applyToAll=True):
	"""Use a color scheme file

	Reset current color scheme and load a new scheme file.

	:param path: color scheme file
	:param applyToAll: if True, apply to existing editor widgets
	"""
	global SCHEME

	if path is None:
		SCHEME = None
		LOGGER.info('unsetting scheme file')
		return

	SCHEME = None
	addSchemeFile(path, applyToAll)


def addSchemeFile(path, applyToAll=True):
	"""Load a color scheme file

	Unlike :any:`useSchemeFile`, it does not reset the current color scheme but adds new definitions.
	If a previous scheme file had some definitions which are redefined in the new scheme, they are replaced by the
	new one.

	:param path: color scheme file
	:param applyToAll: if True, apply to existing editor widgets
	"""
	global SCHEME

	if SCHEME is None:
		LOGGER.info('starting with empty scheme')
		SCHEME = newScheme()

	LOGGER.info('adding scheme %r', path)
	SCHEME.read([path])

	if applyToAll:
		for ed in categoryObjects('editor'):
			applySchemeToEditor(SCHEME, ed)


@registerSetup('editor')
@disabled
def applySchemeOnCreate(editor):
	if SCHEME:
		applySchemeToEditor(SCHEME, editor)


@registerSignal('editor', 'lexerChanged')
@disabled
def applySchemeOnLexerChange(editor, lexer):
	if SCHEME:
		applySchemeToEditor(SCHEME, editor)


def setEnabled(enabled=True):
	"""Enabled/disable automatic color scheme application to editors"""
	applySchemeOnCreate.enabled = enabled
	applySchemeOnLexerChange.enabled = enabled


def _lexerSetFont(lexer, cb, style):
	if style >= 0:
		font = lexer.font(style)
		cb(font)
		lexer.setFont(font, style)
		return

	for i in range(1 << lexer.styleBitsNeeded()):
		desc = lexer.description(i)
		if desc:
			_lexerSetFont(lexer, cb, i)


def lexerSetFontFamily(lexer, family, style=-1):
	"""Set the font family of a lexer

	Set just the font family for `style` of `lexer`.
	Like :any:`QsciLexer.setFont`, but only change the font family, not font size or weight.

	:param lexer: the lexer to change
	:type lexer: QsciLexer
	:param family: font family to use
	:param style: if negative, modifies all styles of `lexer`
	"""
	cb = lambda font: font.setFamily(family)
	_lexerSetFont(lexer, cb, style)


def lexerSetFontPointSize(lexer, size, style=-1):
	"""Set the font size of a lexer

	Set just the font size for `style` of `lexer`.
	Like :any:`QsciLexer.setFont`, but only change the font size, not font family or weight.

	:param lexer: the lexer to change
	:type lexer: QsciLexer
	:param size: font size to use (in points)
	:param style: if negative, modifies all styles of `lexer`
	"""
	cb = lambda font: font.setPointSize(size)
	_lexerSetFont(lexer, cb, style)
