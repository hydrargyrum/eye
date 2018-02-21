# this project is licensed under the WTFPLv2, see COPYING.txt for details

"""Helpers for QsciStyle

`QsciStyle` objects have numeric identifiers, in a limited number.
This module holds a dictionary for storing QsciStyle and map them to text identifiers.

This allows multiple modules to coordinate by using the same textual key and let user configuration to choose
how this style should be displayed.

For example, a helper module could run::

	editor.annotate(1, 'Hello world!', eye.helpers.style.STYLES['hello'])

And a user configuration file could contain::

	eye.helpers.style.STYLES['hello'].setPaper(QColor('#ff0000'))
"""

from PyQt5.Qsci import QsciStyle


__all__ = ('STYLES',)


class Styles(object):
	def __init__(self):
		super(Styles, self).__init__()
		self.styles = {}
		self.reuse = set()

	def __iter__(self):
		return iter(self.styles)

	def __contains__(self, name):
		return name in self.styles

	def __getitem__(self, name):
		if name not in self.styles:
			if self.reuse:
				id = self.reuse.pop()
			else:
				id = -1
			self.styles[name] = QsciStyle(id)

		return self.styles[name]

	def __setitem__(self, name, style):
		if name in self.styles:
			if self.styles[name].style() != style.style():
				del self.style[name]
		self.styles[name] = style

	def __delattr__(self, name):
		id = self.styles[name].style()
		self.reuse.add(id)
		del self.styles[name]


STYLES = Styles()

"""Dict-like for storing QsciStyle objects.

Deleting an item from this mark the id used by the associated QsciStyle as free.
When a new key is inserted, ids marked as free will be reused first before letting QScintilla find a free id.
"""
