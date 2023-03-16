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
``file_saved = Signal(str)`` signal, where the first argument is the path of the saved file.
When configuring EYE (see :doc:`configuration`), it's possible to add this code::

	from eye.connector import register_signal

	@register_signal('editor', 'file_saved')
	def foo(editor_obj, path):
		print('file %s was saved' % path)

We connect the ``file_saved`` signal all objects having the category ``"editor"`` to the ``foo`` callback, which will
receive multiple arguments, first the object which sent the signal, and then the arguments of the ``file_saved`` signal.
When a new Editor widget will be created, it will automatically be connected to our callback, so when any editor will be
saved, ``foo`` will be called.

Module contents
---------------
"""

import inspect
from logging import getLogger
import weakref

from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QWidget

from eye import BUILDING_DOCS, _add_doc
from eye.qt import Signal, Slot, override
from eye.utils import exception_logging

__all__ = (
	'register_signal', 'register_event_filter', 'disabled',
	'register_setup', 'register_teardown',
	'delete_created_by',
	'default_editor_config', 'default_window_config', 'default_lexer_config',
	'category_objects', 'CategoryMixin',
)


LOGGER = getLogger(__name__)


def to_stringlist(obj):
	if isinstance(obj, (str, bytes)):
		return [obj]
	else:
		return obj


class ListenerMixin(object):
	def unregister(self):
		objects = CONNECTOR.objects_matching(self.categories)
		for obj in objects:
			self.do_disconnect(obj)


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
	@Slot(QWidget)
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

		with exception_logging(reraise=False, logger=LOGGER):
			sender = kwargs.get('sender', self.sender())
			self.cb(sender, *args)

	def do_connect(self, obj):
		getattr(obj, self.signal).connect(self.map)

	def do_disconnect(self, obj):
		getattr(obj, self.signal).disconnect(self.map)


class ConnectListener(ListenerMixin):
	def __init__(self, cb, categories, parent=None):
		super(ConnectListener, self).__init__()
		self.cb = cb
		self.categories = categories
		self.caller = None

	def map(self, obj):
		if getattr(self.cb, 'enabled', True):
			with exception_logging(reraise=False, logger=LOGGER):
				self.cb(obj)


class SetupListener(ConnectListener):
	def do_connect(self, obj):
		self.map(obj)

	def do_disconnect(self, obj):
		pass


class TearListener(ConnectListener):
	def do_connect(self, obj):
		pass

	def do_disconnect(self, obj):
		self.map(obj)


class EventFilter(QObject, ListenerMixin):
	def __init__(self, cb, categories, event_types, parent=None):
		super(EventFilter, self).__init__(parent)
		self.cb = cb
		self.categories = categories
		self.event_types = event_types
		self.caller = None

	@override
	def eventFilter(self, obj, ev):
		ret = False
		if getattr(self.cb, 'enabled', True) and ev.type() in self.event_types:
			with exception_logging(reraise=False, logger=LOGGER):
				ret = bool(self.cb(obj, ev))
		return ret

	def do_connect(self, obj):
		obj.installEventFilter(self)

	def do_disconnect(self, obj):
		obj.removeEventFilter(self)


class EventConnector(QObject):
	category_added = Signal(object, str)
	category_removed = Signal(object, str)

	def __init__(self):
		super(EventConnector, self).__init__()
		self.all_objects = weakref.WeakSet()
		self.all_listeners = []

	def do_connect(self, obj, lis, cats=None):
		LOGGER.debug('connecting %r to %r (from file %r) in %r categories', obj, lis.cb, inspect.getfile(lis.cb), cats)
		with exception_logging(reraise=False, logger=LOGGER):
			lis.do_connect(obj)

	def do_disconnect(self, obj, lis, cats=None):
		LOGGER.debug('disconnecting %r to %r (from file %r) in %r categories', obj, lis.cb, inspect.getfile(lis.cb), cats)
		with exception_logging(reraise=False, logger=LOGGER):
			lis.do_disconnect(obj)

	def add_listener(self, categories, lis):
		self.all_listeners.append(lis)

		# iterate on list copy to avoid concurrent access
		for obj in list(self.all_objects):
			if categories <= obj.categories():
				self.do_connect(obj, lis, categories)

	def add_object(self, obj):
		self.all_objects.add(obj)

		oc = obj.categories()
		if not oc:
			return

		for lis in self.all_listeners:
			if lis.categories <= oc:
				self.do_connect(obj, lis, lis.categories)

	def add_category(self, obj, cat):
		oc = obj.categories()

		for lis in self.all_listeners:
			if lis.categories:
				if cat in lis.categories and lis.categories <= oc:
					self.do_connect(obj, lis, cat)
			elif len(obj.categories()) == 1:
				self.do_connect(obj, lis, cat)
		self.category_added.emit(obj, cat)

	def remove_category(self, obj, cat):
		for lis in self.all_listeners:
			if cat in lis.categories:
				self.do_disconnect(obj, lis, cat)
		self.category_removed.emit(obj, cat)

	def objects_matching(self, categories):
		categories = frozenset(to_stringlist(categories))
		return [obj for obj in self.all_objects if categories <= obj.categories()]

	def delete_created_by(self, caller):
		"""Unregister listeners registered in file `caller`."""
		new_listeners = []
		for lis in self.all_listeners:
			if lis.caller == caller:
				lis.unregister()
			else:
				new_listeners.append(lis)
		self.all_listeners = new_listeners


class CategoryMixin(object):
	"""Mixin class to support object categories.

	This class should be inherited by classes of objects which should have categories.
	"""

	def __init__(self, **kwargs):
		super(CategoryMixin, self).__init__(**kwargs)
		self._categories = set()
		CONNECTOR.add_object(self)

	def categories(self):
		"""Return categories of the object."""
		return self._categories

	def add_category(self, c):
		"""Add a category to the object."""
		if c in self._categories:
			return
		self._categories.add(c)
		CONNECTOR.add_category(self, c)

	def remove_category(self, c):
		"""Remove a category from an object."""
		if c not in self._categories:
			return
		self._categories.remove(c)
		CONNECTOR.remove_category(self, c)


def peek_set(s):
	return next(iter(s))


def is_ancestor_of(ancestor, child):
	"""Return True if `ancestor` is an ancestor of `child`, QObject-tree-wise."""
	while child is not None:
		if child is ancestor:
			return True
		child = child.parent()
	return False


def category_objects(categories, ancestor=None):
	"""Return objects matching all specified categories.

	:param categories: matching object should match _all_ these categories
	:type categories: list or str
	:param ancestor: if not None, only objects that are children of `ancestor` are returned
	"""
	if ancestor is None:
		return CONNECTOR.objects_matching(categories)
	else:
		return [obj for obj in CONNECTOR.objects_matching(categories) if is_ancestor_of(ancestor, obj)]


def delete_created_by(caller):
	"""Unregister listeners registered by script `caller`.

	If `caller` script file had registered any listeners (as with :any:`register_signal`), this method
	unregisters them.

	This can be useful to unregister all listeners from a script to re-run the script afterwards, to
	avoid listeners be registered (and listening) twice.

	:param caller: path of the script that registered listeners
	:type caller: str
	"""
	CONNECTOR.delete_created_by(caller)


def register_signal(categories, signal, stackoffset=0):
	"""Decorate a function that should be run when a signal is emitted.

	When the `signal` of all existing and future objects matching all specified `categories`
	is emitted, the decorated function will be called.

	When called, the decorated function will received the target object as first argument, then
	the signal arguments as next arguments.

	:param categories: the categories to match
	:type categories: list or str

	Example::

		@register_signal('editor', 'file_saved')
		def foo(editor_obj, path):
			print('file %s has been saved', path)
	"""

	categories = frozenset(to_stringlist(categories))
	doctext = ('This handler is registered for categories ``%s`` on signal ``%s``.'
				   % (list(categories), signal))

	if BUILDING_DOCS:
		return lambda x: _add_doc(x, doctext)

	def deco(func):
		caller = inspect.stack()[1 + stackoffset][1]

		lis = SignalListener(func, categories, signal, CONNECTOR)
		lis.caller = caller
		CONNECTOR.add_listener(categories, lis)

		_add_doc(func, doctext)

		return func

	return deco


def register_setup(categories, stackoffset=0):
	"""Decorate a function that should be run for all objects matching categories.

	When an object is created that matches `categories` or an object is being added new categories and they match
	the specified `categories`, the decorated function will be called.
	Also, when the function is decorated, it is called for all existing objects matching `categories`.

	The decorated function will received the matching object as only argument.

	:param categories: the categories to match
	:type categories: list or str

	Example::

		@register_setup('editor')
		def foo(editor_obj):
			print('an editor has been created')
	"""

	categories = frozenset(to_stringlist(categories))
	doctext = 'This handler is registered as setup for categories ``%s``.' % (list(categories),)

	if BUILDING_DOCS:
		return lambda x: _add_doc(x, doctext)

	def deco(func):
		caller = inspect.stack()[1 + stackoffset][1]

		lis = SetupListener(func, categories)
		lis.caller = caller
		CONNECTOR.add_listener(categories, lis)

		_add_doc(func, doctext)

		return func

	return deco


def register_teardown(categories, stackoffset=0):
	categories = frozenset(to_stringlist(categories))
	doctext = 'This handler is registered as teardown for categories ``%s``.' % (list(categories),)

	if BUILDING_DOCS:
		return lambda x: _add_doc(x, doctext)

	def deco(func):
		caller = inspect.stack()[1 + stackoffset][1]

		lis = TearListener(func, categories)
		lis.caller = caller
		CONNECTOR.add_listener(categories, lis)

		_add_doc(func, doctext)

		return func

	return deco



def register_event_filter(categories, event_types, stackoffset=0):
	"""Decorate a function that should be run when an event is sent to an object.

	When a :any:`PyQt5.QtCore.QEvent` object of a type in `event_types` is sent to an object
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

		@register_event_filter('window', [QEvent.Close])
		def on_win_close(window, event):
			print('the %s window was closed' % window)

	:param categories: the categories to match
	:type categories: list or str
	:param event_types: list of accepted ``QEvent.type()`` the sent event should match
	:type event_types: list of ints
	:rtype: bool
	"""

	categories = frozenset(to_stringlist(categories))
	doctext = ('This handler is registered as event filter for categories ``%s`` with '
			   'event types ``%r``.' % (list(categories), event_types))

	if BUILDING_DOCS:
		return lambda x: _add_doc(x, doctext)

	def deco(func):
		caller = inspect.stack()[1 + stackoffset][1]

		lis = EventFilter(func, categories, event_types, CONNECTOR)
		lis.caller = caller
		CONNECTOR.add_listener(categories, lis)

		# TODO use textual event type (parse source)
		_add_doc(func, doctext)

		return func

	return deco


def disabled(func):
	"""Disable a function previously decorated with a listener like register_signal.

	If the decorated function (`func`) has been decorated with :any:`register_signal`,
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

	doctext = 'This handler is disabled by default.'
	_add_doc(func, doctext)

	return func


default_editor_config = register_setup('editor')

"""Decorate a function that should be called for every editor.

This decorator is intended for functions to configure editor widgets.
See also :any:`register_setup`.
"""

default_window_config = register_setup('window')

"""Decorate a function that should be called for every EYE window.

This decorator is intended for functions to configure EYE windows.
See also :any:`register_setup`.
"""

default_lexer_config = register_signal(['editor'], 'lexer_changed')

"""Decorate a function that should be called when a lexer is set for an editor.

This decorator is intended for functions to configure lexers.
"""

CONNECTOR = EventConnector()
