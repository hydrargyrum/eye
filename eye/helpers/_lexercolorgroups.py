# this project is licensed under the WTFPLv2, see COPYING.txt for details

from PyQt5.Qsci import QsciLexerPython, QsciLexerCPP, QsciLexerBash, QsciLexerCSS


# TODO case insensitive

# Keyword, Identifier, Number, Comment, String, Operator, Error
# IdentifierDefinition

__all__ = ('getIdAndAliases',)

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


def getIdAndAliases(cls, keyword):
	ret = []
	if hasattr(cls, keyword):
		ret.append(getattr(cls, keyword))
	if cls in ALIASES and keyword in ALIASES[cls]:
		aliases = ALIASES[cls][keyword]
		ret.extend(getattr(cls, alias) for alias in aliases)
	return ret
