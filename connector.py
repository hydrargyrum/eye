
from PyQt4.QtCore import QObject, pyqtSlot as Slot
import collections
import weakref
import inspect

from app import qApp

__all__ = 'Listener EventConnector registerSignal'.split()


class Listener(QObject):
	def __init__(self, cb, categories, signal, parent=None):
		QObject.__init__(self, parent)
		self.cb = cb
		self.categories = categories
		self.signal = signal

	@Slot(int)
	@Slot(str)
	@Slot(unicode)
	@Slot(QObject)
	@Slot()
	def map(self, *args, **kwargs):
		sender = kwargs.get('sender', self.sender())
		self.cb(sender, *args)


class EventConnector(QObject, object):
	def __init__(self):
		QObject.__init__(self)
		self.allObjects = weakref.WeakKeyDictionary()
		self.allListeners = []

	def doConnect(self, obj, lis, cat=''):
		qApp().logger.debug('connecting %r to %r (from file %r) in %r category', obj, lis.cb, inspect.getfile(lis.cb), cat)
		getattr(obj, lis.signal).connect(lis.map)

	def doDisconnect(self, obj, lis, cat=''):
		qApp().logger.debug('disconnecting %r to %r (from file %r) in %r category', obj, lis.cb, inspect.getfile(lis.cb), cat)
		getattr(obj, lis.signal).disconnect(lis.map)

	def addListener(self, cb, categories, signal):
		categories = frozenset(categories)
		lis = Listener(cb, categories, signal, self)

		self.allListeners.append(lis)

		for obj in self.allObjects:
			matches = categories & obj.categories()
			if not matches:
				continue
			elif lis.signal == 'connected':
				lis.map(sender=obj)
			else:
				self.doConnect(obj, lis, peekSet(matches))

	def addObject(self, obj):
		self.allObjects[obj] = True

		oc = obj.categories()
		for lis in self.allListeners:
			matches = lis.categories & oc
			if not matches:
				continue
			elif lis.signal == 'connected':
				lis.map(sender=obj)
			else:
				self.doConnect(obj, lis, peekSet(matches))

	def categoryAdded(self, obj, cat):
		prev = obj.categories().copy()
		prev.remove(cat)

		for lis in self.allListeners:
			if cat in lis.categories:
				if prev & lis.categories:
					continue # object is already connected
				elif lis.signal == 'connected':
					lis.map(sender=obj)
				else:
					self.doConnect(obj, lis, cat)

	def categoryRemoved(self, obj, cat):
		for lis in self.allListeners:
			if cat in lis.categories:
				if obj.categories() & lis.categories:
					continue # object is still connected
				elif lis.signal == 'disconnected':
					lis.map(sender=obj)
				else:
					self.doDisconnect(obj, lis, cat)


def peekSet(s):
	return next(iter(s))

def registerSignal(categories, signal):
	if isinstance(categories, (str, unicode, basestring)):
		categories = [categories]

	def deco(func):
		qApp().connector.addListener(func, categories, signal)
		return func
	return deco

defaultEditorConfig = registerSignal(['editor'], 'connected')
