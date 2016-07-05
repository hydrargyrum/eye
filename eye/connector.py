# this project is licensed under the WTFPLv2, see COPYING.txt for details

"""Connector for signals and slots of categories.

.. _connector:

Connector
---------

In Qt, a signal of an object can be connected to the slot of another object, so when the signal of this object
is emitted, the slot of that object is called. However, the connections are individual: even though a signal
exists for a whole class of object, it's not possible to connect the signal of all objects of a class to one slot.

In EYE, the connector allows to connect a signal of all existing objects matching a category (see :ref:`categories`)
as well as future objects matching this category, to a function.

.. _categories:

Categories
----------

A category is a string tag attached to an object. An object can have multiple categories.
Categories can be added to/removed from an object dynamically, though often the categories
will be set when the object is created.
Since the connector (see :ref:`connector`) allows automatic connection of many objects to a function, categories
allow finer grained control of what objects should be connected than if the class of the objects was the only
criterion of connection.

Example
-------

All objects of the class :class:`eye.widgets.Editor` have by default the category ``"editor"`` and that class has the
``fileSaved = Signal(str)`` signal, where the first argument is the path of the saved file.
When configuring EYE (see :doc:`configuration`), it's possible to add this code::

	from eye.connector import registerSignal

	@registerSignal('editor', 'fileSaved')
	def foo(editor_obj, path):
		print('file %s was saved' % path)

We connect the ``fileSaved`` signal all objects having the category ``"editor"`` to the ``foo`` callback, which will
receive multiple arguments, first the object which sent the signal, and then the arguments of the ``fileSaved`` signal.
When a new Editor widget will be created, it will automatically be connected to our callback, so when any editor will be
saved, ``foo`` will be called.

Module contents
---------------
"""

import inspect
from logging import getLogger
import weakref

from PyQt5.QtCore import QObject, pyqtSignal as Signal

from .qt import Slot
from .three import bytes, str
from .utils import exceptionLogging

__all__ = ('registerSignal', 'registerEventFilter', 'disabled',
           'registerSetup', 'registerTeardown',
           'defaultEditorConfig', 'defaultWindowConfig', 'defaultLexerConfig',
           'categoryObjects', 'CategoryMixin')


LOGGER = getLogger(__name__)


def to_stringlist(obj):
	if isinstance(obj, (str, bytes)):
		return [obj]
	else:
		return obj


class ListenerMixin(object):
	def unregister(self):
		objects = CONNECTOR.objectsMatching(self.categories)
		for obj in objects:
			self.doDisconnect(obj)


class SignalListener(QObject, ListenerMixin):
	def __init__(self, cb, categories, signal, parent=None):
		super(SignalListener, self).__init__(parent)
		self.cb = cb
		self.categories = categories
		self.signal = signal
		self.caller = None

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
		getattr(obj, self.signal).connect(self.map)

	def doDisconnect(self, obj):
		getattr(obj, self.signal).disconnect(self.map)


class ConnectListener(ListenerMixin):
	def __init__(self, cb, categories, parent=None):
		super(ConnectListener, self).__init__()
		self.cb = cb
		self.categories = categories
		self.caller = None

	def map(self, obj):
		if getattr(self.cb, 'enabled', True):
			with exceptionLogging(reraise=False, logger=LOGGER):
				self.cb(obj)


class SetupListener(ConnectListener):
	def doConnect(self, obj):
		self.map(obj)

	def doDisconnect(self, obj):
		pass


class TearListener(ConnectListener):
	def doConnect(self, obj):
		pass

	def doDisconnect(self, obj):
		self.map(obj)


class EventFilter(QObject, ListenerMixin):
	def __init__(self, cb, categories, eventTypes, parent=None):
		super(EventFilter, self).__init__(parent)
		self.cb = cb
		self.categories = categories
		self.eventTypes = eventTypes
		self.caller = None

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

	def doConnect(self, obj, lis, cats=None):
		LOGGER.debug('connecting %r to %r (from file %r) in %r categories', obj, lis.cb, inspect.getfile(lis.cb), cats)
		with exceptionLogging(reraise=False, logger=LOGGER):
			lis.doConnect(obj)

	def doDisconnect(self, obj, lis, cats=None):
		LOGGER.debug('disconnecting %r to %r (from file %r) in %r categories', obj, lis.cb, inspect.getfile(lis.cb), cats)
		with exceptionLogging(reraise=False, logger=LOGGER):
			lis.doDisconnect(obj)

	def addListener(self, categories, lis):
		self.allListeners.append(lis)

		# iterate on list copy to avoid concurrent access
		for obj in list(self.allObjects):
			if categories <= obj.categories():
				self.doConnect(obj, lis, categories)

	def addObject(self, obj):
		self.allObjects.add(obj)

		oc = obj.categories()
		if not oc:
			return

		for lis in self.allListeners:
			if lis.categories <= oc:
				self.doConnect(obj, lis, lis.categories)

	def addCategory(self, obj, cat):
		oc = obj.categories()

		for lis in self.allListeners:
			if cat in lis.categories:
				if lis.categories <= oc:
					self.doConnect(obj, lis, cat)
		self.categoryAdded.emit(obj, cat)

	def removeCategory(self, obj, cat):
		for lis in self.allListeners:
			if cat in lis.categories:
				self.doDisconnect(obj, lis, cat)
		self.categoryRemoved.emit(obj, cat)

	def objectsMatching(self, categories):
		if isinstance(categories, (bytes, str)):
			categories = (categories,)
		categories = frozenset(categories)
		return [obj for obj in self.allObjects if categories <= obj.categories()]

	def deleteCreatedBy(self, caller):
		newListeners = []
		for lis in self.allListeners:
			if lis.caller == caller:
				lis.unregister()
			else:
				newListeners.append(lis)
		self.allListeners = newListeners


class CategoryMixin(object):
	"""Mixin class to support object categories."""

	def __init__(self, **kwargs):
		super(CategoryMixin, self).__init__(**kwargs)
		self._categories = set()
		CONNECTOR.addObject(self)

	def categories(self):
		"""Return categories of the object."""
		return self._categories

	def addCategory(self, c):
		"""Add a category to the object."""
		if c in self._categories:
			return
		self._categories.add(c)
		CONNECTOR.addCategory(self, c)

	def removeCategory(self, c):
		"""Remove a category from an object."""
		if c not in self._categories:
			return
		self._categories.remove(c)
		CONNECTOR.removeCategory(self, c)


def peekSet(s):
	return next(iter(s))


def isAncestorOf(ancestor, child):
	while child is not None:
		if child == ancestor:
			return True
		child = child.parent()
	return False


def categoryObjects(cats, ancestor=None):
	"""Return objects matching all specified categories.

	:param ancestor: if not None, only objects that are children of `ancestor` are returned
	"""
	if ancestor is None:
		return CONNECTOR.objectsMatching(cats)
	else:
		return [obj for obj in CONNECTOR.objectsMatching(cats) if isAncestorOf(ancestor, obj)]


def deleteCreatedBy(caller):
	CONNECTOR.deleteCreatedBy(caller)


def registerSignal(categories, signal, stackoffset=0):
	"""Decorate a function that should be run when a signal is emitted.

	When the `signal` of all existing and future objects matching all specified `categories`
	is emitted, the decorated function will be called.

	Example::

		@registerSignal('editor', 'fileSaved')
		def foo(editor_obj, path):
			print('file %s has been saved', path)
	"""
	categories = frozenset(to_stringlist(categories))

	def deco(func):
		caller = inspect.stack()[1 + stackoffset][1]

		lis = SignalListener(func, categories, signal, CONNECTOR)
		lis.caller = caller
		CONNECTOR.addListener(categories, lis)
		return func

	return deco


def registerSetup(categories, stackoffset=0):
	"""Decorate a function that should be run for all objects matching categories.

	When an object is created that matches `categories` or an object is being added new categories and they match
	the specified `categories`, the decorated function will be called.
	Also, when the function is decorated, it is called for all existing objects matching `categories`.

	:param categories: the categories to match

	Example::

		@registerConnect('editor')
		def foo(editor_obj):
			print('an editor has been created')
	"""
	categories = frozenset(to_stringlist(categories))

	def deco(func):
		caller = inspect.stack()[1 + stackoffset][1]

		lis = SetupListener(func, categories)
		lis.caller = caller
		CONNECTOR.addListener(categories, lis)
		return func

	return deco


def registerTeardown(categories, stackoffset=0):
	categories = frozenset(to_stringlist(categories))

	def deco(func):
		caller = inspect.stack()[1 + stackoffset][1]

		lis = TearListener(func, categories)
		lis.caller = caller
		CONNECTOR.addListener(categories, lis)
		return func

	return deco



def registerEventFilter(categories, eventTypes, stackoffset=0):
	categories = frozenset(to_stringlist(categories))

	def deco(func):
		caller = inspect.stack()[1 + stackoffset][1]

		lis = EventFilter(func, categories, eventTypes, CONNECTOR)
		lis.caller = caller
		CONNECTOR.addListener(categories, lis)
		return func

	return deco


def disabled(func):
	"""Disable a function decorated with registerSignal."""
	func.enabled = False
	return func


defaultEditorConfig = registerSetup('editor')

"""Decorate a function that should be called for every editor.

This decorator is intended for functions to configure editor widgets.
"""

defaultWindowConfig = registerSetup('window')

"""Decorate a function that should be called for every EYE window.

This decorator is intended for functions to configure EYE windows.
"""

defaultLexerConfig = registerSignal(['editor'], 'lexerChanged')

"""Decorate a function that should be called when a lexer is set for an editor.

This decorator is intended for functions to configure lexers.
"""

CONNECTOR = EventConnector()
