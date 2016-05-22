# this project is licensed under the WTFPLv2, see COPYING.txt for details

"""Helpers for QsciStyle
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
