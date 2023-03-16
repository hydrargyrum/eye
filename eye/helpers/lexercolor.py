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

from configparser import SafeConfigParser
from logging import getLogger

from eye.colorutils import QColorAlpha
from eye.connector import category_objects, register_signal, register_setup, disabled
from eye.helpers._lexercolorgroups import get_id_and_aliases
from eye.helpers.styles import STYLES
from eye.lexers import styles_from_lexer

__all__ = (
	'set_enabled', 'use_scheme_file', 'add_scheme_file',
	'lexer_set_font_family', 'lexer_set_font_point_size',
	'apply_scheme_to_editor', 'apply_scheme_dict_to_editor',
	'apply_scheme_on_lexer_change', 'apply_scheme_on_create',
)


LOGGER = getLogger(__name__)

FG_ATTRS = frozenset(['fg', 'foreground', 'color'])
BG_ATTRS = frozenset(['bg', 'background'])

SCHEME = None


def new_scheme():
	parser = SafeConfigParser()
	parser.optionxform = str
	return parser


def fuzzy_equals(a, b):
	def norm(name):
		return name.lower().replace(' ', '_')
	return norm(a) == norm(b)


def get_style_by_desc(lexer, desc, fuzzy=False):
	for i in range(1 << lexer.styleBitsNeeded()):
		idesc = lexer.description(i)
		if idesc == desc or (fuzzy and fuzzy_equals(desc, idesc)):
			return i


def parse_bool(s):
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

	def apply_generic(self, attr, *args):
		if attr == 'font':
			self.set_font('Family', self.strvalue, *args)
		elif attr == 'points':
			self.set_font('PointSizeF', float(self.strvalue), *args)
		elif attr == 'bold':
			self.set_font('Bold', parse_bool(self.strvalue), *args)
		elif attr == 'italic':
			self.set_font('Italic', parse_bool(self.strvalue), *args)
		elif attr == 'underline':
			self.set_font('Underline', parse_bool(self.strvalue), *args)
		elif attr in FG_ATTRS:
			self.set_color(QColorAlpha(self.strvalue), *args)
		elif attr in BG_ATTRS:
			self.set_paper(QColorAlpha(self.strvalue), *args)
		else:
			raise UnsupportedModification()


class LexerModificator(Modificator):
	def apply(self):
		tokenname, attr = self.key.split('.')

		lexer = self.editor.lexer()
		if not lexer:
			return

		if tokenname == '*':
			ids = styles_from_lexer(lexer).values()
		elif tokenname == '_default':
			ids = [self.editor.STYLE_DEFAULT]
		else:
			ids = get_id_and_aliases(lexer, tokenname)

		for id in ids:
			self.apply_one(id, attr)

	def apply_one(self, style_id, attr):
		lexer = self.editor.lexer()

		self.apply_generic(attr, lexer, style_id)

	def apply_generic(self, attr, lexer, style_id):
		if attr == 'eolfill':
			lexer.setEolFill(parse_bool(self.strvalue))
		else:
			super(LexerModificator, self).apply_generic(attr, lexer, style_id)

	def set_color(self, qc, lexer, style_id):
		lexer.setColor(QColorAlpha(self.strvalue), style_id)

	def set_paper(self, qc, lexer, style_id):
		lexer.setPaper(QColorAlpha(self.strvalue), style_id)

	def set_font(self, font_attr, value, lexer, style_id):
		font = lexer.font(style_id)
		font_attr = 'set%s' % font_attr
		getattr(font, font_attr)(value)
		lexer.setFont(font, style_id)


class EditorModificator(Modificator):
	def apply(self):
		element, attr = self.key.split('.')
		self.apply_generic(attr, element)

	def apply_caret(self, attr, strvalue):
		if attr in FG_ATTRS:
			qc = QColorAlpha(strvalue)
			self.editor.setCaretForegroundColor(qc)
		elif attr in BG_ATTRS:
			qc = QColorAlpha(strvalue)
			self.editor.setCaretLineBackgroundColor(qc)
		else:
			raise UnsupportedModification('only elements in %s are supported for caret' % (FG_ATTRS + BG_ATTRS))

	def set_color(self, qc, element):
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

	def set_paper(self, qc, element):
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

	def set_font(self, font_attr, value, element):
		if element != 'text':
			raise UnsupportedModification('only "text" is supported')
		# margin.* lacks a Editor.marginsFont()

		font = self.editor.font()
		font_attr = 'set%s' % font_attr
		getattr(font, font_attr)(value)
		self.editor.setFont(font)


class IndicatorModificator(Modificator):
	def apply(self):
		name, attr = self.key.split('.')

		indicator = self.editor.indicators.get(name)
		if not indicator:
			indicator = self.editor.create_indicator(name, self.editor.PlainIndicator)

		self.apply_generic(attr, indicator)

	def apply_generic(self, attr, indicator):
		if attr == 'style':
			indicator.set_style(getattr(self.editor, self.strvalue))
		else:
			super(IndicatorModificator, self).apply_generic(attr, indicator)

	def set_color(self, qc, indicator):
		indicator.set_color(qc)

	def set_paper(self, qc, indicator):
		indicator.setOutlineColor(qc)

	def set_font(self, *args):
		raise UnsupportedModification('font cannot be set for indicators')


class StyleModificator(Modificator):
	def apply(self):
		name, attr = self.key.split('.')

		self.apply_generic(attr, STYLES[name])

	def apply_generic(self, attr, style):
		if attr == 'eolfill':
			style.setEolFill(parse_bool(self.strvalue))
		else:
			super(StyleModificator, self).apply_generic(attr, style)

	def set_font(self, font_attr, value, style):
		font = style.font()
		font_attr = 'set%s' % font_attr
		getattr(font, font_attr)(value)
		style.setFont(font)

	def set_color(self, qc, style):
		style.set_color(qc)

	def set_paper(self, qc, style):
		style.set_paper(qc)


def get_modificator(name):
	modificators = {
		'token': LexerModificator,
		'indicator': IndicatorModificator,
		'base': EditorModificator,
		'style': StyleModificator,
	}

	return modificators.get(name)


def apply_scheme_dict_to_editor(dct, editor):
	for key in sorted(dct):
		value = dct[key]
		try:
			styletype, subkey = key.split('.', 1)
		except ValueError:
			LOGGER.info('ignoring malformed style key %r', key)
			continue

		modificator_type = get_modificator(styletype)
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


def apply_scheme_to_editor(parser, editor):
	lexer = editor.lexer()

	lexer_name = lexer.language() if lexer else 'None'
	for section in ('*', lexer_name):
		if parser.has_section(section):
			LOGGER.debug('using section %r for file %r', section, editor.path)

			dict_scheme = dict(parser.items(section))
			apply_scheme_dict_to_editor(dict_scheme, editor)


def use_scheme_file(path, apply_to_all=True):
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
	add_scheme_file(path, apply_to_all)


def add_scheme_file(path, apply_to_all=True):
	"""Load a color scheme file

	Unlike :any:`use_scheme_file`, it does not reset the current color scheme but adds new definitions.
	If a previous scheme file had some definitions which are redefined in the new scheme, they are replaced by the
	new one.

	:param path: color scheme file
	:param apply_to_all: if True, apply to existing editor widgets
	"""
	global SCHEME

	if SCHEME is None:
		LOGGER.info('starting with empty scheme')
		SCHEME = new_scheme()

	LOGGER.info('adding scheme %r', path)
	SCHEME.read([path])

	if apply_to_all:
		for ed in category_objects('editor'):
			apply_scheme_to_editor(SCHEME, ed)


@register_setup('editor')
@disabled
def apply_scheme_on_create(editor):
	if SCHEME:
		apply_scheme_to_editor(SCHEME, editor)


@register_signal('editor', 'lexer_changed')
@disabled
def apply_scheme_on_lexer_change(editor, lexer):
	if SCHEME:
		apply_scheme_to_editor(SCHEME, editor)


def set_enabled(enabled=True):
	"""Enabled/disable automatic color scheme application to editors"""
	apply_scheme_on_create.enabled = enabled
	apply_scheme_on_lexer_change.enabled = enabled


def _lexer_set_font(lexer, cb, style):
	if style >= 0:
		font = lexer.font(style)
		cb(font)
		lexer.setFont(font, style)
		return

	for i in range(1 << lexer.styleBitsNeeded()):
		desc = lexer.description(i)
		if desc:
			_lexer_set_font(lexer, cb, i)


def lexer_set_font_family(lexer, family, style=-1):
	"""Set the font family of a lexer

	Set just the font family for `style` of `lexer`.
	Like :any:`QsciLexer.setFont`, but only change the font family, not font size or weight.

	:param lexer: the lexer to change
	:type lexer: QsciLexer
	:param family: font family to use
	:param style: if negative, modifies all styles of `lexer`
	"""
	def cb(font):
		font.setFamily(family)

	_lexer_set_font(lexer, cb, style)


def lexer_set_font_point_size(lexer, size, style=-1):
	"""Set the font size of a lexer

	Set just the font size for `style` of `lexer`.
	Like :any:`QsciLexer.setFont`, but only change the font size, not font family or weight.

	:param lexer: the lexer to change
	:type lexer: QsciLexer
	:param size: font size to use (in points)
	:param style: if negative, modifies all styles of `lexer`
	"""
	def cb(font):
		font.setPointSize(size)

	_lexer_set_font(lexer, cb, style)
