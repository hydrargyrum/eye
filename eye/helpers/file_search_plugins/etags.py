# this project is licensed under the WTFPLv2, see COPYING.txt for details

from PyQt5.QtCore import pyqtSlot as Slot, pyqtSignal as Signal, QTimer, QElapsedTimer

from contextlib import contextmanager
import fnmatch
import logging
import os

from .base import registerPlugin, SearchPlugin
from ...pathutils import findAncestorContaining, findInAncestors
from ..confcache import ConfCache


__all__ = ('ETagSearch',)


LOGGER = logging.getLogger(__name__)


class ETagsParser(object):
	START = 0
	SECTION_HEADER = 1
	SECTION_DATA = 2
	END = 3

	def __init__(self, path):
		super(ETagsParser, self).__init__()
		self.path = path

		self.state = None
		self.fd = None
		self.current_filename = None

	def parse(self):
		funcs = {
			self.START: self.parse_start,
			self.SECTION_HEADER: self.parse_header,
			self.SECTION_DATA: self.parse_data
		}

		LOGGER.debug('parsing tags database %r', self.path)

		with open(self.path, 'rb') as self.fd:
			self.state = self.START
			while self.state != self.END:
				res = funcs[self.state]()
				if res is not None:
					yield res

	def parse_start(self):
		self.state = self.SECTION_DATA

	def parse_header(self):
		line = self.fd.readline().rstrip(b'\n')
		self.current_filename, size = line.rsplit(b',', 1)
		self.current_filename = self.current_filename.decode('utf-8')
		self.current_filename = os.path.join(os.path.dirname(self.path), self.current_filename)
		self.state = self.SECTION_DATA

	def parse_data(self):
		line = self.fd.readline().rstrip(b'\n')
		if not line:
			self.state = self.END
		elif line == b'\x0c':
			self.state = self.SECTION_HEADER
		else:
			next = line
			definition, next = next.split(b'\x7f', 1)
			name, next = next.split(b'\x01', 1)
			linenumber, offset = next.split(b',')

			linenumber = int(linenumber)
			#definition = definition.decode('utf-8')
			try:
				name = name.decode('utf-8')
			except UnicodeDecodeError:
				name = name.decode('latin-1')

			self.state = self.SECTION_DATA
			return {
				'tag': name,
				'path': self.current_filename,
				'line': linenumber,
			}


class TagDb(object):
	def __init__(self):
		super(TagDb, self).__init__()
		self.db = {}

	def add_tag(self, d):
		LOGGER.debug('adding tag %r', d)

		occurences = self.db.setdefault(d['tag'], [])
		occurences.append(d)

	def find_tag(self, name):
		return self.db.get(name, [])

	def tags_matching(self, pattern):
		for tag in self.db:
			if fnmatch.fnmatch(tag, pattern):
				yield tag


def findTagDir(path):
	return findAncestorContaining(path, ['TAGS'])


def findTagFile(path):
	return findInAncestors(path, ['TAGS'])


class DbCache(ConfCache):
	pass


CACHE = DbCache(weak=False)


@registerPlugin
class ETagsSearch(SearchPlugin):
	id = 'etags'

	def __init__(self, **kwargs):
		super(ETagsSearch, self).__init__(**kwargs)
		self.db = None
		self.parser = None
		self.parsing = None
		self.request = None

		self.timer = QTimer(self)
		self.timer.timeout.connect(self._batchLoad)

	@classmethod
	def isAvailable(cls, path):
		return bool(findTagDir(path))

	@classmethod
	def searchRootPath(cls, path):
		return findTagDir(path)

	@contextmanager
	def safeBatch(self):
		try:
			yield
		except:
			self.timer.stop()
			self.finished.emit(0)
			raise

	def loadDb(self, dbpath):
		self.db = CACHE.get(dbpath)
		if self.db:
			self.searchInDb(self.request)
			return

		LOGGER.debug('loading db %r because it is not in cache', dbpath)
		self.db = TagDb()
		self.parser = ETagsParser(dbpath)
		self.parsing = self.parser.parse()
		self.timer.start()

	@Slot()
	def _batchLoad(self):
		with self.safeBatch():
			duration = QElapsedTimer()
			duration.start()

			for taginfo in self.parsing:
				self.db.add_tag(taginfo)

				if duration.hasExpired(10):
					return

			CACHE.addConf(self.parser.path, self.db)
			self.timer.stop()

			LOGGER.debug('db %r has finished loading', self.parser.path)
			self.searchInDb(self.request)

	def searchInDb(self, pattern):
		for match in self.db.find_tag(pattern):
			self.found.emit(match)
		self.finished.emit(0)

	def search(self, root, pattern, **options):
		self.request = pattern
		self.started.emit()

		with self.safeBatch():
			dbpath = findTagFile(root)
			if not dbpath:
				self.finished.emit(0)
				return

			self.loadDb(dbpath)
