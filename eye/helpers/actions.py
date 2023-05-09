# this project is licensed under the WTFPLv2, see COPYING.txt for details

"""Module for registering actions on widgets

This module helps in the creation of `QAction` objects.
The `actions` module is to `QAction`s what the :any:`eye.connector` is to Qt signal and slots.

An action is registered with a name for a set of categories. The action can be triggered when a particular shortcut
is pressed, which are registered with :any:`register_action_shortcut`. When the action is triggered, in turn it can
trigger a callback (with :any:`register_action`) or a slot (with :any:`register_action_slot`, but this one is optional),
or a Scintilla editor action.

The use of categories lets the register be done once, not for every widget instance. Internally, `QAction` objects are
created automatically by the module in each instance.

For example, an action `print_console_file` could be created for editor widgets and bound to `Ctrl+P`::

	@register_action('editor', 'print_console_file')
	def my_action_func(ed):
		print(ed.text())

	register_action_shortcut('editor', 'print_console_file', 'Ctrl+P')

The same can be done in a single step::

	@register_shortcut('editor', 'Ctrl+P')
	def my_action_func(ed):
		print(ed.text())

This way is simpler but less re-usable because the action is unnamed. A plugin can register actions but should not
bind keyboard shortcuts to it and let user configuration do it.
"""

from collections import OrderedDict
from functools import wraps
import logging

from PyQt5.Qsci import QsciCommand, QsciScintilla
from PyQt5.QtCore import Qt, QObject
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QAction

from eye import BUILDING_DOCS
from eye.connector import category_objects, CONNECTOR
from eye.qt import Slot

__all__ = (
	'register_action_shortcut', 'unregister_action_shortcut',
	'register_shortcut',
	'register_action_slot', 'register_action',
	'get_action'
)


LOGGER = logging.getLogger(__name__)


def setup_action_slot(obj, slot_name):
	"""Setup an object QAction triggering a slot, named after that slot

	The slot `slot_name` will be called when the `QAction` is triggered

	:param obj: the object in which to add the `QAction`
	:type obj: QObject
	:param slot_name: name of the slot and name of the action to add
	:type slot_name: str
	"""
	slot = getattr(obj, slot_name)
	build_action(obj, slot_name, slot)


def build_action(obj, action_name, target):
	"""Setup an object QAction triggering a callable

	A `QAction` will be created with name `action_name`, added as a child of `obj`.
	When the action's `triggered()` signal is emitted, the `target` will be called.

	See :any:`QObject.setObjectName`.

	:param obj: the object in which to add the QAction
	:type obj: QObject
	:param target: the function/method to call when action is triggered
	:type target: callable or Slot
	"""
	action = QAction(obj)
	action.setObjectName(action_name)
	obj.addAction(action)
	action.triggered.connect(target)

	return action


def disable_shortcut(obj, keyseq):
	"""Disable actions children of `obj` using shortcut `keyseq`

	If a children QAction of `obj` has a shortcut set to `keyseq`, the shortcut is disabled.
	This function will not work for internal Scintilla actions, see :any:`disableSciShortcut`.
	"""
	qkeyseq = QKeySequence(keyseq)

	for child in obj.children():
		if isinstance(child, QAction):
			if child.shortcut() == qkeyseq:
				child.setShortcut(QKeySequence())


def disable_sci_shortcut(obj, keyseq):
	"""Disable Scintilla action shortcuts

	If `obj` is an :any:`eye.widgets.editor.Editor` and `keyseq` is a shortcut triggering a Scintilla editor action,
	the shortcut is disabled.
	This function only works for internal editor actions, like `PyQt5.Qsci.QsciCommand.Undo`.

	See :any:`QsciCommand`. The reverse function is :any:`setSciShortcut`.
	"""
	assert keyseq.count() == 1
	qcmd = obj.standardCommands().boundTo(keyseq[0])
	if qcmd is not None:
		qcmd.setKey(0)


def set_sci_shortcut(obj, action_name, keyseq):
	"""Set shortcut for internal Scintilla editor action.

	If `obj` is an :any:`eye.widgets.editor.Editor`, the editor action `action_name` will be linked to keyboard
	shortcut `keyseq`.
	This function only works for internal editor actions, like `PyQt5.Qsci.QsciCommand.Undo`.

	See :any:`QsciCommand`.
	"""
	assert keyseq.count() == 1
	qval = getattr(QsciCommand, action_name)
	qcmd = obj.standardCommands().find(qval)
	qcmd.setKey(keyseq[0])


def get_action(obj, action_name):
	"""Return children QAction of `obj` named `action_name`."""
	return obj.findChild(QAction, action_name, Qt.FindDirectChildrenOnly)


def disable_action(obj, action_name):
	"""Remove children QAction named"""
	action = get_action(action_name)
	if action:
		obj.removeAction(action)


def register_action_slot(categories, slot_name):
	"""Register an action named `slot_name`, triggering slot `slot_name`

	An action named `slot_name` is registered for `categories`. When the action is triggered, it will call the
	slot `slot_name` of the object where the action is triggered. So, objects matching `categories` should have
	a slot `slot_name`.

	It's not required to call this function: when a keyboard shortcut is triggered, and the shortcut was bound
	to an action (with :any:`register_action_shortcut`) which had no callable registered (i.e. :any:`register_action`
	or similar functions were never called), then it tries to call a slot named the same as the action name.
	"""
	ACTIONS.register_action_slot(categories, slot_name)


def to_stringlist(obj):
	if isinstance(obj, (str, bytes)):
		return [obj]
	else:
		return obj


class CategoryStore(QObject):
	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		self.by_cat = OrderedDict()
		self.by_key = OrderedDict()
		CONNECTOR.category_added.connect(self.category_added)
		CONNECTOR.category_removed.connect(self.category_removed)

	@Slot(object, str)
	def category_added(self, obj, cat):
		keys = self.by_cat.get(cat, {})
		for key in keys:
			self.register_object(obj, key, keys[key])

	@Slot(object, str)
	def category_removed(self, obj, cat):
		obj_cats = obj.categories()
		keys = self.by_cat.get(cat, {})
		for key in keys:
			key_cats = set(self.by_key.get(key, []))
			if not (obj_cats & key_cats):
				self.unregister_object(obj, key)

	def register_categories(self, categories, key, value):
		categories = set(to_stringlist(categories))

		objects = set()
		for cat in categories:
			objects |= set(category_objects(cat))

		for obj in objects:
			self.register_object(obj, key, value)

		for cat in categories:
			self.by_cat.setdefault(cat, OrderedDict())[key] = value
		self.by_key.setdefault(key, OrderedDict())[cat] = value

	def unregister_categories(self, categories, key):
		categories = set(to_stringlist(categories))

		# categories left that will prevent an object from being unregistered
		key_cats = set(self.by_key.get(key, []))
		retaining_cats = key_cats - categories

		# object list
		objects = set()
		for cat in categories:
			objects |= set(category_objects(cat))

		for obj in objects:
			if not (obj.categories() & retaining_cats):
				self.unregister_object(obj, key)

		for cat in categories:
			try:
				del self.by_cat[cat][key]
			except KeyError:
				pass
		try:
			del self.by_key[key][cat]
		except KeyError:
			pass

	def register_object(self, obj, key, value):
		raise NotImplementedError()

	def unregister_object(self, obj, key):
		raise NotImplementedError()


class ShortcutStore(CategoryStore):
	def __init__(self, **kwargs):
		super().__init__(**kwargs)

	def is_editor_command(self, obj, name):
		return isinstance(obj, QsciScintilla) and hasattr(QsciCommand, name)

	def register_object(self, obj, key, action_name):
		if self.is_editor_command(obj, action_name):
			disable_sci_shortcut(obj, key[0])
			set_sci_shortcut(obj, action_name, key[0])
			return

		disable_shortcut(obj, key[0])
		action = get_action(obj, action_name)
		action.setShortcut(key[0])
		action.setShortcutContext(key[1])

	def unregister_object(self, obj, key):
		if isinstance(obj, QsciScintilla):
			disable_sci_shortcut(obj, key[0])
		disable_shortcut(obj, key[0])

	def register_shortcut(self, categories, key, value):
		LOGGER.info('registering shortcut %r with %r for categories %r', key, value, categories)
		self.register_categories(categories, key, value)

	def unregister_shortcut(self, categories, key):
		LOGGER.info('unregistering shortcut %r for categories %r', key, categories)
		self.unregister_categories(categories, key)


class ActionStore(CategoryStore):
	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		self.func_counter = 0

	@Slot()
	def placeholder(self):
		LOGGER.warning("placeholder function shouldn't be called: %r", self.sender().objectName())

	def has_slot(self, obj, slot_name):
		return callable(getattr(obj, slot_name, None))

	def register_object(self, obj, key, value):
		LOGGER.debug('registering %s action %r for object %r', value[0], key, obj)

		old = get_action(obj, key)
		if old is not None:
			try:
				old.triggered.disconnect(self.placeholder)
			except TypeError:
				LOGGER.warning('will not override existing action %r from object %r', key, obj)
				return
			obj.removeAction(old)
			old.setParent(None)

		if value[0] == 'slot' or self.has_slot(obj, key):
			setup_action_slot(obj, key)
		elif value[0] == 'func':
			build_action(obj, key, value[1])
		elif value[0] == 'placeholder':
			build_action(obj, key, self.placeholder)
		elif value[0] == 'scicommand':
			build_action(obj, key, self.sci)

	def unregister_object(self, obj, key):
		LOGGER.debug('unregistering action %r for object %r', key, obj)
		disable_action(obj, key)

	def register_action_placeholder(self, categories, action_name):
		LOGGER.debug('creating registering placeholder action %r for categories %r', action_name, categories)
		self.register_categories(categories, action_name, ('placeholder',))

	def register_action_slot(self, categories, slot_name):
		LOGGER.info('registering slot action %r for categories %r', slot_name, categories)
		self.register_categories(categories, slot_name, ('slot',))

	def register_action_sci(self, categories, name):
		self.register_categories(categories, name, ('scicommand', name))

	def register_action_func(self, categories, cb, name=None):
		if name is None:
			self.func_counter += 1
			name = '%s_%d' % (cb.__name__, self.func_counter)

		LOGGER.info('registering function action %r (name=%r) for categories %r', cb, name, categories)
		cb.action_name = name
		self.register_categories(categories, name, ('func', cb))
		return name

	def has_action(self, category, action_name):
		return action_name in self.by_cat.get(category, {})


def register_action(categories, action_name):
	"""Decorate a function to be registered as an action

	The decorated function will be registered as action `action_name` for objects matching the `categories`
	"""
	if BUILDING_DOCS:
		return lambda x: x

	categories = set(to_stringlist(categories))

	def decorator(cb):
		@wraps(cb)
		def newcb():
			return cb(SHORTCUTS.sender().parent())

		ACTIONS.register_action_func(categories, newcb, name=action_name)
		return cb

	return decorator


def register_action_shortcut(categories, action_name, keyseq, context=Qt.WidgetShortcut):
	"""Register a shortcut for an action

	:param categories: the categories of the widgets where to watch the shortcut
	:param action_name: the name of the action to trigger when the shortcut is triggered
	:type action_name: str
	:param keyseq: the shortcut description
	:type keyseq: str, int or QKeySequence
	:param context: the context where to listen to the shortcut, relative to the widgets matching the categories
	"""
	categories = set(to_stringlist(categories))
	key = (QKeySequence(keyseq), context)

	create_ph = set()
	for cat in categories:
		if not ACTIONS.has_action(cat, action_name):
			create_ph.add(cat)
	if create_ph:
		ACTIONS.register_action_placeholder(create_ph, action_name)

	SHORTCUTS.register_shortcut(categories, key, action_name)


def unregister_action_shortcut(categories, keyseq, context=Qt.WidgetShortcut):
	"""Unregister a keyboard shortcut previously registered

	After this call, current widgets matching `categories` will not have the keyboard shortcut anymore, and it
	won't be bound to new widgets matching `categories`.
	"""
	key = (QKeySequence(keyseq), context)
	SHORTCUTS.unregister_shortcut(categories, key)


def register_shortcut(categories, keyseq, context=Qt.WidgetShortcut, action_name=None):
	"""Decorate a function to be called when a keyboard shortcut is typed

	When the keyboard shortcut `keyseq` is pressed in any widget matching `categories`, the decorated
	function will be called, with the widget passed as first parameter.

	Internally, when a widget matches the `categories`, a QAction is created for it and the shortcut is set.
	See :any:`build_action`.

	:param categories: the categories of the widgets where to watch the shortcut
	:type categories: str or list
	:param keyseq: the shortcut description
	:type keyseq: str, int or QKeySequence
	:param context: the context where to listen to the shortcut, relative to the widgets matching the categories
	"""

	if BUILDING_DOCS:
		return lambda x: x

	key = (QKeySequence(keyseq), context)

	def decorator(cb):
		name = action_name

		@wraps(cb)
		def newcb():
			return cb(SHORTCUTS.sender().parent())

		name = ACTIONS.register_action_func(categories, newcb, name=name)
		SHORTCUTS.register_shortcut(categories, key, name)
		return cb
	return decorator


# monkey-patch qkeysequence so it is hashable

QKeySequence.__hash__ = lambda self: hash(self.toString())
QKeySequence.__repr__ = lambda self: '<QKeySequence key=%r>' % self.toString()

# warning: order is important since shortcuts can create a slot-action
ACTIONS = ActionStore()
SHORTCUTS = ShortcutStore()
