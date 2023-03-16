# this project is licensed under the WTFPLv2, see COPYING.txt for details

from PyQt5.Qsci import QsciLexerPython, QsciLexerCPP, QsciLexerBash, QsciLexerCSS

# TODO case insensitive

# Keyword, Identifier, Number, Comment, String, Operator, Error
# IdentifierDefinition

__all__ = ('get_id_and_aliases',)

ALIASES = {
	QsciLexerPython: {
		'Identifier': [
			'ClassName', 'Decorator', 'FunctionMethodName'
		],
		'IdentifierDefinition': [
			'ClassName', 'FunctionMethodName'
		],
		'String': [
			'DoubleQuotedString', 'SingleQuotedString',
			'TripleSingleQuotedString', 'TripleDoubleQuotedString'
		],
		'Comment': ['CommentBlock'],
		'CommentLine': ['Comment'],
	},
	QsciLexerCPP: {
		'Comment': ['CommentLine'],
		'String': [
			'VerbatimString', 'DoubleQuotedString', 'SingleQuotedString',
			'TripleQuotedVerbatimString', 'HashQuotedString',
			'RawString'
		],
		'Keyword': ['KeywordSet2', 'CommentDocKeyword'],
		'Error': ['CommentDocKeywordError'],

		'Inactive': [
			'InactiveDefault',
			'InactiveComment',
			'InactiveCommentLine',
			'InactiveNumber',
			'InactiveDoubleQuotedString',
			'InactiveSingleQuotedString',
			'InactiveUUID',
			'InactivePreProcessor',
			'InactiveUnclosedString',
			'InactiveVerbatimString',
			'InactiveRegex',
			'InactiveCommentLineDoc',
			'InactiveKeywordSet2',
			'InactiveCommentDocKeyword',
			'InactiveCommentDocKeywordError',
			'InactiveGlobalClass',
			'InactiveRawString',
			'InactiveTripleQuotedVerbatimString',
			'InactiveHashQuotedString',
			'InactivePreProcessorComment',
			'InactivePreProcessorCommentLineDoc',
			'InactiveUserLiteral',
			'InactiveTaskMarker',
			'InactiveEscapeSequence',
			'InactiveKeyword',
			'InactiveIdentifier',
			'InactiveOperator',
			'InactiveKeyword',
			'InactiveKeyword',
		],
	},
	QsciLexerBash: {
		'String': ['DoubleQuotedString', 'SingleQuotedString'],
		'Identifier': ['ParameterExpansion'],
	},
	QsciLexerCSS: {
		'Identifier': [
			'Tag', 'ClassSelector', 'PseudoClass', 'CSS1Property',
			'CSS2Property', 'CSS3Property', 'PseudoElement', 'ExtendedCSSProperty',
			'ExtendedPseudoClass', 'ExtendedPseudoElement'
		],
		'Error': ['UnknownPseudoClass', 'UnknownProperty'],
	},
}


def lexer_description_ids(lexer):
	ret = {}
	for i in range(1 << lexer.styleBitsNeeded()):
		description = lexer.description(i)
		if not description:
			break
		ret[description] = i
	return ret


def get_id_and_aliases(lexer, keyword):
	ret = []

	cls = type(lexer)
	if hasattr(cls, keyword):
		ret.append(getattr(cls, keyword))
	if cls in ALIASES and keyword in ALIASES[cls]:
		aliases = ALIASES[cls][keyword]
		ret.extend(getattr(cls, alias) for alias in aliases if hasattr(cls, alias))

	if not ret:
		descs = lexer_description_ids(lexer)
		if keyword in descs:
			ret.append(descs[keyword])

	return ret
