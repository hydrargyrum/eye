# this project is licensed under the WTFPLv2, see COPYING.txt for details

from eye.connector import register_signal, disabled

__all__ = ('lines_margin_width',)


@register_signal(['editor'], 'linesChanged')
@disabled
def lines_margin_width(ed):
	if 'lines' in ed.margins:
		# add one character width as it may be truncated
		ed.margins['lines'].set_width('0%d' % ed.lines())
