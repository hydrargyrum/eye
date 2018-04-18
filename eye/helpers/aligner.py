# this project is licensed under the WTFPLv2, see COPYING.txt for details

from eye.connector import register_signal
from eye.helpers.actions import register_shortcut
from eye.helpers.buffers import current_buffer
from eye.widgets.minibuffer import open_mini_buffer

__all__ = (
	'prompt_align', 'align',
)

def align(ed, separator, gapping=None):
	"""Align selected editor text basing on a separator.

	If separator is ``=`` and this text is selected in editor::

		a=1
		bbb=2
		cc=3

	It will be aligned like this::

		a  =1
		bbb=2
		cc =3

	Left-alignment is achieved by adding or removing space characters before a separator.
	Works with single selection and rectangular selection. Supports having the separator multiple
	times on a line (useful for aligning ASCII tables).

	Warning: may suppress tab characters if they are not at the beginning of the line.

	:param ed: editor widget in which to perform alignment
	:type ed: :any:`eye.widgets.editor.Editor`
	:param separator: separator string which should be aligned in the selection
	:type separator: str
	:param gapping: optional tuple to indicate how to surround separator when outputting.
	                Useful to include extra spaces around separators.
	:type gapping: tuple[str,str]
	"""

	def single_split(ed):
		sl, sc, el, ec = ed.get_selection_n(0)

		if (sl, sc) > (el, ec):
			sl, sc, el, ec = el, ec, sl, sc
		if ec == 0:
			el -= 1

		spl = []
		linenos = []
		for l in range(sl, el + 1):
			new = [part.rstrip() for part in lines[l].split(separator)]
			spl.append([''] + new + [''])
			linenos.append(l)

		return spl, linenos

	def multi_split(ed):
		seen = set()
		spl = []
		linenos = []
		for sel in range(ed.selections_count()):
			sl, sc, el, ec = ed.get_selection_n(sel)

			if sl != el:
				return None, None
			if sl in seen:
				return None, None

			seen.add(sl)

			if sc > ec:
				sc, ec = ec, sc

			new = [part.rstrip() for part in lines[sl][sc:ec].split(separator)]
			spl.append([lines[sl][:sc]] + new + [lines[sl][ec:]])
			linenos.append(sl)

		return spl, linenos

	if ed.selections_empty():
		return

	if gapping is None:
		gapping = ('', '')
	outsep = gapping[0] + separator + gapping[1]

	lines = ed.text().split('\n')

	if ed.selections_count() == 1:
		spl, linenos = single_split(ed)
	else:
		spl, linenos = multi_split(ed)
	if spl is None:
		return

	tw = ed.tabWidth()
	lengths = []
	for parts in spl:
		for i, part in enumerate(parts[1:-1]):
			if i == len(lengths):
				lengths.append(0)
			lengths[i] = max(lengths[i], len(part.expandtabs(tw)))

	for parts in spl:
		for i, part in enumerate(parts[1:-1]):
			fill = lengths[i] - len(part.expandtabs(tw))
			parts[i + 1] = part + ' ' * fill

	for l, parts in zip(linenos, spl):
		lines[l] = parts[0] + outsep.join(parts[1:-1]).rstrip() + parts[-1]

	with ed.undo_group():
		# XXX setText would clear the history
		ed.clear()
		ed.insert('\n'.join(lines))


def prompt_align():
	"""Prompt a string on which to align and perform align on validation

	This will open a mini-buffer with category ``prompt_aligner``. When enter is pressed, alignment
	will be performed using the input string.
	"""
	inp = open_mini_buffer(category='prompt_aligner', placeholder='Enter string to align on...')


@register_signal('prompt_aligner', 'text_entered')
def prompt_success(prompter, txt):
	txt = txt.strip()
	if txt:
		ed = current_buffer()
		align(ed, txt)

