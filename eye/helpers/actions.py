# this project is licensed under the WTFPLv2, see COPYING.txt for details

from collections import OrderedDict
import logging

from PyQt5.QtCore import Qt, QObject, pyqtSlot as Slot
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QAction
from PyQt5.Qsci import QsciCommand, QsciScintilla

from ..three import bytes, str
from ..connector import registerSignal, categoryObjects, CONNECTOR


__all__ = ('registerActionShortcut', 'unregisterActionShortcut',
           'registerShortcut',
           'registerActionSlot', 'registerAction',
           'getAction')


LOGGER = logging.getLogger(__name__)


def setupActionSlot(obj, slotName):
	slot = getattr(obj, slotName)
	buildAction(obj, slotName, slot)


def buildAction(obj, actionName, target):
	action = QAction(obj)
	action.setObjectName(actionName)
	obj.addAction(action)
	action.triggered.connect(target)

	return action


def disableShortcut(obj, keyseq):
	qkeyseq = QKeySequence(keyseq)

	for child in obj.children():
		if isinstance(child, QAction):
			if child.shortcut() == qkeyseq:
				child.setShortcut(QKeySequence())


def disableSciShortcut(obj, keyseq):
	assert keyseq.count() == 1
	qcmd = obj.standardCommands().boundTo(keyseq[0])
	if qcmd is not None:
		qcmd.setKey(0)


def setSciShortcut(obj, actionName, keyseq):
	assert keyseq.count() == 1
	qval = getattr(QsciCommand, actionName)
	qcmd = obj.standardCommands().find(qval)
	qcmd.setKey(keyseq[0])


def getAction(obj, actionName):
	return obj.findChild(QAction, actionName, Qt.FindDirectChildrenOnly)


def disableAction(obj, actionName):
	action = getAction(actionName)
	if action:
		obj.removeAction(action)


def registerActionSlot(categories, slotName):
	ACTIONS.registerActionSlot(categories, slotName)


def to_stringlist(obj):
	if isinstance(obj, (str, bytes)):
		return [obj]
	else:
		return obj


class CategoryStore(QObject):
	def __init__(self, **kwargs):
		super(CategoryStore, self).__init__(**kwargs)
		self.by_cat = OrderedDict()
		self.by_key = OrderedDict()
		CONNECTOR.categoryAdded.connect(self.categoryAdded)
		CONNECTOR.categoryRemoved.connect(self.categoryRemoved)

	@Slot(object, str)
	def categoryAdded(self, obj, cat):
		keys = self.by_cat.get(cat, {})
		for key in keys:
			self.registerObject(obj, key, keys[key])

	@Slot(object, str)
	def categoryRemoved(self, obj, cat):
		obj_cats = obj.categories()
		keys = self.by_cat.get(cat, {})
		for key in keys:
			key_cats = set(self.by_key.get(key, []))
			if not (obj_cats & sh_cats):
				self.unregisterObject(obj, key)

	def registerCategories(self, categories, key, value):
		categories = set(to_stringlist(categories))

		objects = set()
		for cat in categories:
			objects |= set(categoryObjects(cat))

		for obj in objects:
			self.registerObject(obj, key, value)

		for cat in categories:
			self.by_cat.setdefault(cat, OrderedDict())[key] = value
		self.by_key.setdefault(key, OrderedDict())[cat] = value

	def unregisterCategories(self, categories, key):
		categories = set(to_stringlist(categories))

		# categories left that will prevent an object from being unregistered
		key_cats = set(self.by_key.get(key, []))
		retaining_cats = key_cats - categories

		# object list
		objects = set()
		for cat in categories:
			objects |= set(categoryObjects(cat))

		for obj in objects:
			if not (obj.categories() & retaining_cats):
				self.unregisterObject(obj, key)

		for cat in categories:
			try:
				del self.by_cat[cat][key]
			except KeyError:
				pass
		try:
			del self.by_key[key][cat]
		except KeyError:
			pass

	def registerObject(self, obj, key, value):
		raise NotImplementedError()

	def unregisterObject(self, obj, key):
		raise NotImplementedError()


class ShortcutStore(CategoryStore):
	def __init__(self, **kwargs):
		super(ShortcutStore, self).__init__(**kwargs)

	def isEditorCommand(self, obj, name):
		return isinstance(obj, QsciScintilla) and hasattr(QsciCommand, name)

	def registerObject(self, obj, key, actionName):
		if self.isEditorCommand(obj, actionName):
			disableSciShortcut(obj, key[0])
			setSciShortcut(obj, actionName, key[0])
			return

		disableShortcut(obj, key[0])
		action = getAction(obj, actionName)
		action.setShortcut(key[0])
		action.setShortcutContext(key[1])

	def unregisterObject(self, obj, key):
		if isinstance(obj, QsciScintilla):
			disableSciShortcut(obj, key[0])
		disableShortcut(obj, key[0])

	def registerShortcut(self, categories, key, value):
		LOGGER.info('registering shortcut %r with %r for categories %r', key, value, categories)
		self.registerCategories(categories, key, value)

	def unregisterShortcut(self, categories, key):
		LOGGER.info('unregistering shortcut %r with %r for categories %r', key, value, categories)
		self.unregisterCategories(categories, key)


class ActionStore(CategoryStore):
	def __init__(self, **kwargs):
		super(ActionStore, self).__init__(**kwargs)
		self.func_counter = 0

	@Slot()
	def placeholder(self):
		LOGGER.warning("placeholder function shouldn't be called %r", actionName)

	def hasSlot(self, obj, slotName):
		return callable(getattr(obj, slotName, None))

	def registerObject(self, obj, key, value):
		LOGGER.debug('registering %s action %r for object %r', value[0], key, obj)

		old = getAction(obj, key)
		if old is not None:
			try:
				old.triggered.disconnect(self.placeholder)
			except TypeError:
				LOGGER.warning('will not override existing action %r from object %r', key, obj)
				return
			obj.removeAction(old)
			old.setParent(None)

		if value[0] == 'slot' or self.hasSlot(obj, key):
			setupActionSlot(obj, key)
		elif value[0] == 'func':
			buildAction(obj, key, value[1])
		elif value[0] == 'placeholder':
			buildAction(obj, key, self.placeholder)
		elif value[0] == 'scicommand':
			buildAction(obj, key, self.sci)

	def unregisterObject(self, obj, key):
		LOGGER.debug('unregistering action %r for object %r', key, obj)
		disableAction(obj, key)

	def registerActionPlaceholder(self, categories, actionName):
		LOGGER.debug('creating registering placeholder action %r for categories %r', actionName, categories)
		self.registerCategories(categories, actionName, ('placeholder',))

	def registerActionSlot(self, categories, slotName):
		LOGGER.info('registering slot action %r for categories %r', slotName, categories)
		self.registerCategories(categories, slotName, ('slot',))

	def registerActionSci(self, categories, name):
		self.registerCategories(categories, name, ('scicommand', name))

	def registerActionFunc(self, categories, cb, name=None):
		if name is None:
			self.func_counter += 1
			name = '%s_%d' % (cb.__name__, self.func_counter)

		LOGGER.info('registering function action %r (name=%r) for categories %r', cb, name, categories)
		cb.action_name = name
		self.registerCategories(categories, name, ('func', cb))
		return name

	def hasAction(self, category, actionName):
		return actionName in self.by_cat.get(category, {})


def registerAction(categories, actionName):
	"""Decorate a function to be registered as an action"""

	categories = set(to_stringlist(categories))
	def decorator(cb):
		newcb = lambda: cb(SHORTCUTS.sender().parent())
		ACTIONS.registerActionFunc(categories, newcb, name=actionName)
		return cb
	return decorator


def registerActionShortcut(categories, actionName, keyseq, context=Qt.WidgetShortcut):
	categories = set(to_stringlist(categories))
	key = (QKeySequence(keyseq), context)

	create_ph = set()
	for cat in categories:
		if not ACTIONS.hasAction(cat, actionName):
			create_ph.add(cat)
	if create_ph:
		ACTIONS.registerActionPlaceholder(create_ph, actionName)

	SHORTCUTS.registerShortcut(categories, key, actionName)


def unregisterActionShortcut(categories, keyseq, context=Qt.WidgetShortcut):
	key = (QKeySequence(keyseq), context)
	SHORTCUTS.unregisterShortcut(categories, key)


def registerShortcut(categories, keyseq, context=Qt.WidgetShortcut, actionName=None):
	key = (QKeySequence(keyseq), context)

	def decorator(cb):
		name = actionName
		newcb = lambda: cb(SHORTCUTS.sender().parent())
		name = ACTIONS.registerActionFunc(categories, newcb, name=name)
		SHORTCUTS.registerShortcut(categories, key, name)
		return cb
	return decorator


# monkey-patch qkeysequence so it is hashable

QKeySequence.__hash__ = lambda self: hash(self.toString())
QKeySequence.__repr__ = lambda self: '<QKeySequence key=%r>' % self.toString()

# warning: order is important since shortcuts can create a slot-action
ACTIONS = ActionStore()
SHORTCUTS = ShortcutStore()
