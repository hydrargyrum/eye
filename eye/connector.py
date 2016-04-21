# this project is licensed under the WTFPLv2, see COPYING.txt for details

from PyQt5.QtCore import Qt, QObject, pyqtSignal as Signal, pyqtSlot as Slot
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QShortcut

import inspect
from logging import getLogger
import weakref

from .three import bytes, str
from .utils import exceptionLogging

__all__ = ('registerSignal', 'registerEventFilter', 'disabled',
           'defaultEditorConfig', 'defaultWindowConfig', 'defaultLexerConfig',
           'categoryObjects')


LOGGER = getLogger(__name__)


def to_stringlist(obj):
	if isinstance(obj, (str, bytes)):
		return [obj]
	else:
		return obj


class SignalListener(QObject):
	def __init__(self, cb, categories, signal, parent=None):
		super(SignalListener, self).__init__(parent)
		self.cb = cb
		self.categories = categories
		self.signal = signal

	@Slot(int)
	@Slot(str)
	@Slot(bytes)
	@Slot(QObject)
	@Slot(object)
	@Slot(int, int)
	@Slot(str, str)
	@Slot(int, str)
	@Slot(str, int)
	@Slot(str, object)
	@Slot(object, object)
	@Slot()
	def map(self, *args, **kwargs):
		if not getattr(self.cb, 'enabled', True):
			return

		with exceptionLogging(reraise=False, logger=LOGGER):
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
		super(EventFilter, self).__init__(parent)
		self.cb = cb
		self.categories = categories
		self.eventTypes = eventTypes

	def eventFilter(self, obj, ev):
		ret = False
		if ev.type() in self.eventTypes:
			with exceptionLogging(reraise=False, logger=LOGGER):
				ret = bool(self.cb(obj, ev))
		return ret

	def doConnect(self, obj):
		obj.installEventFilter(self)

	def doDisconnect(self, obj):
		obj.removeEventFilter(self)


class EventConnector(QObject):
	categoryAdded = Signal(object, str)
	categoryRemoved = Signal(object, str)

	def __init__(self):
		super(EventConnector, self).__init__()
		self.allObjects = weakref.WeakSet()
		self.allListeners = []

	def doConnect(self, obj, lis, cat=''):
		LOGGER.debug('connecting %r to %r (from file %r) in %r category', obj, lis.cb, inspect.getfile(lis.cb), cat)
		with exceptionLogging(reraise=False, logger=LOGGER):
			lis.doConnect(obj)

	def doDisconnect(self, obj, lis, cat=''):
		LOGGER.debug('disconnecting %r to %r (from file %r) in %r category', obj, lis.cb, inspect.getfile(lis.cb), cat)
		with exceptionLogging(reraise=False, logger=LOGGER):
			lis.doDisconnect(obj)

	def addListener(self, categories, lis):
		self.allListeners.append(lis)

		# iterate on list copy to avoid concurrent access
		for obj in list(self.allObjects):
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

	def addCategory(self, obj, cat):
		prev = obj.categories().copy()
		prev.remove(cat)

		for lis in self.allListeners:
			if cat in lis.categories:
				if prev & lis.categories:
					continue # object is already connected
				else:
					self.doConnect(obj, lis, cat)
		self.categoryAdded.emit(obj, cat)

	def removeCategory(self, obj, cat):
		for lis in self.allListeners:
			if cat in lis.categories:
				if obj.categories() & lis.categories:
					continue # object is still connected
				else:
					self.doDisconnect(obj, lis, cat)
		self.categoryRemoved.emit(obj, cat)

	def objectsMatching(self, categories):
		if isinstance(categories, (bytes, str)):
			categories = (categories,)
		categories = frozenset(categories)
		return [obj for obj in self.allObjects if categories <= obj.categories()]


def peekSet(s):
	return next(iter(s))


def categoryObjects(cats):
	return CONNECTOR.objectsMatching(cats)


def registerSignal(categories, signal):
	categories = frozenset(to_stringlist(categories))

	def deco(func):
		lis = SignalListener(func, categories, signal, CONNECTOR)
		CONNECTOR.addListener(categories, lis)
		return func

	return deco


def registerEventFilter(categories, eventTypes):
	categories = frozenset(to_stringlist(categories))

	def deco(func):
		lis = EventFilter(func, categories, eventTypes, CONNECTOR)
		CONNECTOR.addListener(categories, lis)
		return func

	return deco


def disabled(func):
	func.enabled = False
	return func


defaultEditorConfig = registerSignal(['editor'], 'connected')
defaultWindowConfig = registerSignal(['window'], 'connected')
defaultLexerConfig = registerSignal(['editor'], 'lexerChanged')


CONNECTOR = EventConnector()
