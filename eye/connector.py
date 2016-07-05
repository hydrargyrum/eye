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
           'deleteCreatedBy',
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
		if getattr(self.cb, 'enabled', True) and  ev.type() in self.eventTypes:
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
			if lis.categories:
				if cat in lis.categories and lis.categories <= oc:
					self.doConnect(obj, lis, cat)
			elif len(obj.categories()) == 1:
				self.doConnect(obj, lis, cat)
		self.categoryAdded.emit(obj, cat)

	def removeCategory(self, obj, cat):
		for lis in self.allListeners:
			if cat in lis.categories:
				self.doDisconnect(obj, lis, cat)
		self.categoryRemoved.emit(obj, cat)

	def objectsMatching(self, categories):
		categories = frozenset(to_stringlist(categories))
		return [obj for obj in self.allObjects if categories <= obj.categories()]

	def deleteCreatedBy(self, caller):
		"""Unregister listeners registered in file `caller`."""
		newListeners = []
		for lis in self.allListeners:
			if lis.caller == caller:
				lis.unregister()
			else:
				newListeners.append(lis)
		self.allListeners = newListeners


class CategoryMixin(object):
	"""Mixin class to support object categories.

	This class should be inherited by classes of objects which should have categories.
	"""

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
	"""Return True if `ancestor` is an ancestor of `child`, QObject-tree-wise."""
	while child is not None:
		if child is ancestor:
			return True
		child = child.parent()
	return False


def categoryObjects(categories, ancestor=None):
	"""Return objects matching all specified categories.

	:param categories: matching object should match _all_ these categories
	:type categories: list or str
	:param ancestor: if not None, only objects that are children of `ancestor` are returned
	"""
	if ancestor is None:
		return CONNECTOR.objectsMatching(categories)
	else:
		return [obj for obj in CONNECTOR.objectsMatching(categories) if isAncestorOf(ancestor, obj)]


def deleteCreatedBy(caller):
	"""Unregister listeners registered by script `caller`.

	If `caller` script file had registered any listeners (as with :any:`registerSignal`), this method
	unregisters them.

	This can be useful to unregister all listeners from a script to re-run the script afterwards, to
	avoid listeners be registered (and listening) twice.

	:param caller: path of the script that registered listeners
	:type caller: str
	"""
	CONNECTOR.deleteCreatedBy(caller)


def registerSignal(categories, signal, stackoffset=0):
	"""Decorate a function that should be run when a signal is emitted.

	When the `signal` of all existing and future objects matching all specified `categories`
	is emitted, the decorated function will be called.

	When called, the decorated function will received the target object as first argument, then
	the signal arguments as next arguments.

	:param categories: the categories to match
	:type categories: list or str

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

	The decorated function will received the matching object as only argument.

	:param categories: the categories to match
	:type categories: list or str

	Example::

		@registerSetup('editor')
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
	"""Decorate a function that should be run when an event is sent to an object.

	When a :any:`PyQt5.QtCore.QEvent` object of a type in `eventTypes` is sent to an object
	matching `categories`, the decorated function will be called.

	The decorated function must take 2 parameters: the destination object to which the event
	is sent and the event itself.

	If the value returned by the decorated function is True, the sent event will be filtered:
	it will not reach the destination object, and it will not be processed by any other
	event-filters, registered by standard Qt functions or by :any:`registerEventFilter`.

	If the value returned by the decorated function is False or is omitted (it is None then),
	the event will continue its route through other event-filters and to the destination
	object.

	See also :any:`PyQt5.QtCore.QObject.eventFilter` and
	:any:`PyQt5.QtCore.QObject.installEventFilter`.

	Example::

		@registerEventFilter('window', [QEvent.Close])
		def onWinClose(window, event):
			print('the %s window was closed' % window)

	:param categories: the categories to match
	:type categories: list or str
	:param eventTypes: list of accepted ``QEvent.type()`` the sent event should match
	:type eventTypes: list of ints
	:rtype: bool
	"""
	categories = frozenset(to_stringlist(categories))

	def deco(func):
		caller = inspect.stack()[1 + stackoffset][1]

		lis = EventFilter(func, categories, eventTypes, CONNECTOR)
		lis.caller = caller
		CONNECTOR.addListener(categories, lis)
		return func

	return deco


def disabled(func):
	"""Disable a function previously decorated with a listener like registerSignal.

	If the decorated function (`func`) has been decorated with :any:`registerSignal`,
	:any:`registerEventFilter` or some other kind of listener decorator, the decorated function
	will not be called anymore when a matching signal is emitted or a event has to pass in a
	filter, until it is enabled again.

	This decorator simply sets an ``enabled`` attribute on the decorated function to False.
	To re-enable the disabled function, just set the ``enabled`` attribute to True.

	When the function is re-enabled, missed signals and events will not cause the decorated
	function to be called, but upcoming signals/events will trigger the decorated function.

	Since functions decorated with :any:`registerSetup` can be triggered only when an object
	_starts_ matching categories, re-enabling such a function will not catch-up the setup of
	an object.
	"""
	func.enabled = False
	return func


defaultEditorConfig = registerSetup('editor')

"""Decorate a function that should be called for every editor.

This decorator is intended for functions to configure editor widgets.
See also :any:`registerSetup`.
"""

defaultWindowConfig = registerSetup('window')

"""Decorate a function that should be called for every EYE window.

This decorator is intended for functions to configure EYE windows.
See also :any:`registerSetup`.
"""

defaultLexerConfig = registerSignal(['editor'], 'lexerChanged')

"""Decorate a function that should be called when a lexer is set for an editor.

This decorator is intended for functions to configure lexers.
"""

CONNECTOR = EventConnector()
