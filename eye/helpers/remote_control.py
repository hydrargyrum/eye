# this project is licensed under the WTFPLv2, see COPYING.txt for details

from functools import wraps
import logging
import os

from PyQt5.QtCore import QObject, pyqtSlot as Slot, Q_CLASSINFO
from PyQt5.QtDBus import QDBusConnection, QDBusVariant, QDBusMessage

from ..three import str
from ..connector import disabled, CategoryMixin
from ..app import qApp
from .. import pathutils
from .intent import registerIntentListener, sendIntent


__all__ = ('registerRemoteRequest', 'onRequestOpen', 'SimpleHandler')


LOGGER = logging.getLogger(__name__)


ROOT_OBJ = None
BUS = None


class SimpleHandler(QObject, CategoryMixin):
	Q_CLASSINFO('D-Bus Interface', 're.indigo.eye')

	def __init__(self, **kwargs):
		super(SimpleHandler, self).__init__(**kwargs)
		self.addCategory('remote_control')

	@Slot(str, result=QDBusVariant)
	@Slot(str, QDBusVariant, result=QDBusVariant)
	@Slot(str, str, result=QDBusVariant)
	@Slot(str, QDBusVariant, QDBusVariant, result=QDBusVariant)
	@Slot(str, str, str, result=QDBusVariant)
	@Slot(str, QDBusVariant, QDBusVariant, QDBusVariant, result=QDBusVariant)
	@Slot(str, str, str, str, result=QDBusVariant)
	@Slot(str, QDBusVariant, QDBusVariant, QDBusVariant, QDBusVariant, result=QDBusVariant)
	@Slot(str, QDBusVariant, QDBusVariant, QDBusVariant, QDBusVariant, QDBusVariant, result=QDBusVariant)
	@Slot(str, QDBusVariant, QDBusVariant, QDBusVariant, QDBusVariant, QDBusVariant, QDBusVariant,
	      result=QDBusVariant)
	@Slot(str, QDBusVariant, QDBusVariant, QDBusVariant, QDBusVariant, QDBusVariant, QDBusVariant, QDBusVariant,
	      result=QDBusVariant)
	@Slot(str, QDBusVariant, QDBusVariant, QDBusVariant, QDBusVariant, QDBusVariant, QDBusVariant, QDBusVariant,
	      QDBusVariant, result=QDBusVariant)
	def request(self, request_type, *args):
		args = tuple(arg.variant() if isinstance(arg, QDBusVariant) else arg for arg in args)

		LOGGER.debug('received request %r%r', request_type, args)
		result = sendIntent(self, 'remoteRequest', request_type=request_type, args=args)
		if result is None:
			result = False

		LOGGER.debug('replying %r to request %r%r', result, request_type, args)
		return QDBusVariant(result)


def registerRemoteRequest(request_type, stackoffset=0):
	def decorator(func):
		@registerIntentListener('remoteRequest', categories='remote_control', stackoffset=(1 + stackoffset))
		@wraps(func)
		def wrapper(remote, intent):
			if intent.info.request_type == request_type and getattr(func, 'enabled', True):
				result = func(intent.info.args)
				intent.accept(result)
				return True
			return False

		return func
	return decorator


def createServer():
	global BUS, ROOT_OBJ

	ROOT_OBJ = SimpleHandler()

	BUS = QDBusConnection.sessionBus()
	BUS.registerService('re.indigo.eye')
	BUS.registerObject('/', ROOT_OBJ, QDBusConnection.ExportAllContents)


def sendRequest(req, *args):
	global BUS

	LOGGER.debug('sending request %r%r', req, args)

	method_args = [req]
	method_args.extend(args)

	msg = QDBusMessage.createMethodCall('re.indigo.eye', '/', 're.indigo.eye', 'request')
	msg.setArguments(method_args)

	BUS = QDBusConnection.sessionBus()
	reply = BUS.call(msg)

	if reply.type() == QDBusMessage.ErrorMessage:
		raise ValueError(reply.errorMessage())
	return list(reply.arguments())


@registerRemoteRequest('ping')
def onRequestPing(args):
	return True


@registerRemoteRequest('open')
def onRequestOpen(args):
	path, row, col = pathutils.parseFilename(args[0])
	path = os.path.abspath(path)
	if row is None:
		loc = None
	else:
		loc = (row, col)

	sendIntent(ROOT_OBJ, 'openEditor', path=path, loc=loc, reason='remote')
