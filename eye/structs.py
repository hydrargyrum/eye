# this project is licensed under the WTFPLv2, see COPYING.txt for details

__all__ = ('PropDict',)

class PropDict(dict):
	def __getattr__(self, k):
		try:
			return self[k]
		except KeyError:
			# raised so getattr with a default value works
			raise AttributeError('object has no attribute %r' % k)

	def __setattr__(self, k, v):
		self[k] = v

	def __delattr__(self, k):
		del self[k]
