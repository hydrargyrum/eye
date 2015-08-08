
from PyQt4.QtCore import Qt, QObject, pyqtSlot as Slot
from PyQt4.QtGui import QShortcut, QKeySequence
import collections
import weakref
import inspect

from .utils import exceptionLogging
from .app import qApp

__all__ = ('SignalListener', 'EventListener', 'EventConnector',
           'registerSignal', 'registerEventFilter', 'registerShortcut', 'disabled',
           'defaultEditorConfig', 'defaultWindowConfig', 'defaultLexerConfig',
           'categoryObjects')


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


class EventFilter(QObject):
	def __init__(self, cb, categories, eventTypes, parent=None):
		QObject.__init__(self, parent)
		self.cb = cb
		self.categories = categories
		self.eventTypes = eventTypes

	def eventFilter(self, obj, ev):
		ret = False
		if ev.type() in self.eventTypes:
			with exceptionLogging(reraise=False):
				ret = bool(self.cb(obj, ev))
		return ret

	def doConnect(self, obj):
		obj.installEventFilter(self)

	def doDisconnect(self, obj):
		obj.removeEventFilter(self)


class EventConnector(QObject, object):
	def __init__(self):
		QObject.__init__(self)
		self.allObjects = WeakSet()
		self.allListeners = []

	def doConnect(self, obj, lis, cat=''):
		qApp().logger.debug('connecting %r to %r (from file %r) in %r category', obj, lis.cb, inspect.getfile(lis.cb), cat)
		lis.doConnect(obj)

	def doDisconnect(self, obj, lis, cat=''):
		qApp().logger.debug('disconnecting %r to %r (from file %r) in %r category', obj, lis.cb, inspect.getfile(lis.cb), cat)
		lis.doDisconnect(obj)

	def addListener(self, categories, lis):
		self.allListeners.append(lis)

		for obj in self.allObjects:
			matches = categories & obj.categories()
			if not matches:
				continue
			else:
				self.doConnect(obj, lis, peekSet(matches))

	def addObject(self, obj):
		self.allObjects.add(obj)

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

	def objectsMatching(self, categories):
		if isinstance(categories, (str, unicode, basestring)):
			categories = (categories,)
		categories = frozenset(categories)
		return [obj for obj in self.allObjects if categories <= obj.categories()]


class WeakSet(weakref.WeakKeyDictionary):
	def add(self, obj):
		self[obj] = None

	def remove(self, obj):
		del self[obj]


def peekSet(s):
	return next(iter(s))


def categoryObjects(cats):
	return CONNECTOR.objectsMatching(cats)


def registerSignal(categories, signal):
	if isinstance(categories, (str, unicode, basestring)):
		categories = [categories]
	categories = frozenset(categories)

	def deco(func):
		lis = SignalListener(func, categories, signal, CONNECTOR)
		CONNECTOR.addListener(categories, lis)
		return func

	return deco


def registerEventFilter(categories, eventTypes):
	if isinstance(categories, (str, unicode, basestring)):
		categories = [categories]
	categories = frozenset(categories)

	def deco(func):
		lis = EventFilter(func, categories, eventTypes, CONNECTOR)
		CONNECTOR.addListener(categories, lis)
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
			CONNECTOR.doConnect(shortcut, lis, categories[0])

		return cb

	return deco


defaultEditorConfig = registerSignal(['editor'], 'connected')
defaultWindowConfig = registerSignal(['window'], 'connected')
defaultLexerConfig = registerSignal(['editor'], 'lexerChanged')


CONNECTOR = EventConnector()
