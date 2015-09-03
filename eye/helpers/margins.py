# this project is licensed under the WTFPLv2, see COPYING.txt for details

from ..connector import registerSignal, disabled

__all__ = ('linesMarginWidth',)

@registerSignal(['editor'], 'linesChanged')
@disabled
def linesMarginWidth(ed):
	if 'lines' in ed.margins:
		# add one character width as it may be truncated
		ed.margins['lines'].setWidth('0%d' % ed.lines())
