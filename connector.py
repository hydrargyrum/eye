
from PyQt4.QtCore import Qt, QObject, pyqtSlot as Slot
from PyQt4.QtGui import QShortcut, QKeySequence
import collections
import weakref
import inspect
from utils import exceptionLogging

from app import qApp

__all__ = ('SignalListener',
           'EventConnector', 'registerSignal', 'disabled',
           'defaultEditorConfig', 'defaultWindowConfig')


class SignalListener(QObject):
	def __init__(self, cb, categories, signal, parent=None):
		QObject.__init__(self, parent)
		self.cb = cb
		self.categories = categories
		self.signal = signal

	@Slot(int)
	@Slot(str)
	@Slot(unicode)
	@Slot(QObject)
	@Slot(object)
	@Slot()
	def map(self, *args, **kwargs):
		if not getattr(self.cb, 'enabled', True):
			return

		with exceptionLogging(reraise=False):
			sender = kwargs.get('sender', self.sender())
			self.cb(sender, *args)

	def doConnect(self, obj):
		if self.signal == 'connected':
			self.map(sender=obj)
		else:
			getattr(obj, self.signal).connect(self.map)

	def doDisconnect(self, obj):
		if self.signal == 'disconnected':
			self.map(sender=obj)
		else:
			getattr(obj, self.signal).disconnect(self.map)


class EventConnector(QObject, object):
	def __init__(self):
		QObject.__init__(self)
		self.allObjects = weakref.WeakKeyDictionary()
		self.allListeners = []

	def doConnect(self, obj, lis, cat=''):
		qApp().logger.debug('connecting %r to %r (from file %r) in %r category', obj, lis.cb, inspect.getfile(lis.cb), cat)
		lis.doConnect(obj)

	def doDisconnect(self, obj, lis, cat=''):
		qApp().logger.debug('disconnecting %r to %r (from file %r) in %r category', obj, lis.cb, inspect.getfile(lis.cb), cat)
		lis.doDisconnect(obj)

	def addSignalListener(self, cb, categories, signal):
		categories = frozenset(categories)
		lis = SignalListener(cb, categories, signal, self)

		self.allListeners.append(lis)

		for obj in self.allObjects:
			matches = categories & obj.categories()
			if not matches:
				continue
			else:
				self.doConnect(obj, lis, peekSet(matches))

	def addObject(self, obj):
		self.allObjects[obj] = True

		oc = obj.categories()
		for lis in self.allListeners:
			matches = lis.categories & oc
			if not matches:
				continue
			else:
				self.doConnect(obj, lis, peekSet(matches))

	def categoryAdded(self, obj, cat):
		prev = obj.categories().copy()
		prev.remove(cat)

		for lis in self.allListeners:
			if cat in lis.categories:
				if prev & lis.categories:
					continue # object is already connected
				else:
					self.doConnect(obj, lis, cat)

	def categoryRemoved(self, obj, cat):
		for lis in self.allListeners:
			if cat in lis.categories:
				if obj.categories() & lis.categories:
					continue # object is still connected
				else:
					self.doDisconnect(obj, lis, cat)


def peekSet(s):
	return next(iter(s))

def registerSignal(categories, signal):
	if isinstance(categories, (str, unicode, basestring)):
		categories = [categories]

	def deco(func):
		qApp().connector.addSignalListener(func, categories, signal)
		return func

	return deco

def disabled(func):
	func.enabled = False
	return func

def registerShortcut(categories, ks, context=Qt.WidgetShortcut):
	def deco(cb):
		def cbWidget(sh):
			return cb(sh.parentWidget())

		@registerSignal(categories, 'connected')
		def action(widget):
			shortcut = QShortcut(widget)
			shortcut.setKey(QKeySequence(ks))
			shortcut.setContext(context)

			lis = SignalListener(cbWidget, categories, 'activated', shortcut)
			qApp().connector.doConnect(shortcut, lis, categories[0])

		return cb

	return deco


defaultEditorConfig = registerSignal(['editor'], 'connected')
defaultWindowConfig = registerSignal(['window'], 'connected')
defaultLexerConfig = registerSignal(['editor'], 'lexerChanged')
