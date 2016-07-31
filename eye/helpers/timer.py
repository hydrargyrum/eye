# this project is licensed under the WTFPLv2, see COPYING.txt for details

"""Timer-based callback registration
"""

import calendar
from datetime import datetime
import inspect
import itertools
import sys
import unittest

from PyQt5.QtCore import QTimer
from PyQt5.QtCore import pyqtSlot as Slot

from eye.connector import CONNECTOR

__all__ = ('registerTimerInterval', 'registerTimerCron', 'nextTime')


class TimerListener(QTimer):
	def __init__(self, cb=None, **kwargs):
		super().__init__(**kwargs)
		self.categories = {object()}
		self.cb = cb
		self.timeout.connect(self.onTimeout)

	@Slot()
	def onTimeout(self):
		if self.cb and getattr(self.cb, 'enabled', True):
			self.cb()

	def unregister(self):
		self.timeout.disconnect()


def registerTimerInterval(interval, singleshot=False, stackoffset=0):
	"""Decorate a function to call on a periodic interval.

	The decorated method will be called every `interval` milliseconds.

	:param interval: periodic interval (in milliseconds)
	:param singleshot: if True, the timer will fire once, and thus the function will be called once
	"""

	def decorator(cb):
		timer = TimerListener(cb=cb)
		timer.caller = inspect.stack()[1 + stackoffset][1]
		timer.setInterval(interval)
		timer.setSingleShot(singleshot)
		timer.start()
		CONNECTOR.addListener(timer.categories, timer)
		return cb

	return decorator


def datetime2ts(dt):
	"""Convert a datetime object into a UNIX timestamp."""
	return calendar.timegm(dt.utctimetuple())


def nextTime(base=None, **kwargs):
	"""Computes the nearest datetime matching given criteria.

	The function takes ``crontab``-like criteria and returns the nearest datetime occurrence after `base` matching the criteria.
	If `base` is None, the current datetime is used as base.

	The criteria are specified in `kwargs`. Each keyword-argument consists in a unit (the key) and a list of
	acceptable values for this unit. The possible keywords are `second`, `minute`, `hour`, `day`, `month` and
	`year`.
	For each keyword argument passed, the computed datetime must be exactly one of the values in the list.

	For example, ``nextTime(minute=[30], second=[0])`` will return the nearest half-hour minute.
	If the time is 4:10:20, it will return the datetime corresponding to 4:30:00.
	If it were 4:40:05, it would return 5:30:00.

	For units that are not passed in keyword arguments, any value is acceptable.

	Thus, in the previous example, if ``second=[0]`` had not been passed, it would match each second in the 30th minute.
	For example, ``nextTime(datetime(2000, 1, 1, 4, 30, 10), minute=[30])`` would return ``datetime(2000, 1, 1, 4, 30, 11)`` instead
	of ``datetime(2000, 1, 1, 5, 30, 0)``.

	:param base: compute the nearest datetime occurring after `base`
	:type base: datetime or None
	:keyword year: if specified, restrict the year to the given list
	:keyword month: if specified, restrict the month to the given list
	:keyword day: if specified, restrict the day to the given list
	:keyword hour: if specified, restrict the hour to the given list
	:keyword minute: if specified, restrict the minute to the given list
	:keyword second: if specified, restrict the second to the given list
	"""

	if isinstance(base, int):
		base = datetime.utcfromtimestamp(base)
	if base is None:
		base = datetime.now()

	all_units = ('year', 'month', 'day', 'hour', 'minute', 'second')

	for u in all_units:
		if u not in kwargs:
			value = getattr(base, u)
			if u == 'year':
				kwargs[u] = [value, value + 1]
			elif u in ('month', 'day'):
				kwargs[u] = sorted({1, value, value + 1})
			else:
				kwargs[u] = sorted({0, value, value + 1})


	all_values = [kwargs[u] for u in all_units]

	for values in itertools.product(*all_values):
		replacement = dict(zip(all_units, values))
		try:
			new = base.replace(**replacement)
		except ValueError:
			continue
		if new > base:
			return new


class CronListener(QTimer):
	def __init__(self, cb=None, **kwargs):
		super().__init__(**kwargs)
		self.categories = {object()}
		self.cb = cb
		self.timeout.connect(self.callCb)
		self.timeout.connect(self.resetCron)

		self.cron = {}
		self.end = False

	def start(self):
		self.setCron(**self.cron)
		super().start()

	def setCron(self, **kwargs):
		self.cron = kwargs

		nextDt = nextTime(**kwargs)
		if nextDt is None:
			self.end = True
			return self.setInterval(sys.maxint)

		self.end = False

		now = datetime.now()
		duration = (nextDt - now).total_seconds()
		self.setInterval(duration * 1000)

	@Slot()
	def callCb(self):
		if self.end:
			return
		if self.cb and getattr(self.cb, 'enabled', True):
			self.cb()

	@Slot()
	def resetCron(self):
		if not self.isSingleShot():
			self.setCron(**self.cron)

	def unregister(self):
		self.timeout.disconnect()


def registerTimerCron(stackoffset=0, singleshot=False, **kwargs):
	"""Decorate a function to call in a timed manner, specified by crontab-criteria.

	The decorated function shall be called when the current datetime matches criteria specified by `kwargs`.
	The `kwargs` are interpreted with the semantics described in :any:`nextTime`.

	:param singleshot: if True, the time will fire once, and thus the decorated function will be called once
	:param kwargs: see :any:`nextTime`
	"""
	def decorator(cb):
		timer = CronListener(cb=cb)
		timer.caller = inspect.stack()[1 + stackoffset][1]
		timer.setSingleShot(singleshot)
		timer.setCron(**kwargs)
		timer.start()
		CONNECTOR.addListener(timer.categories, timer)
		return cb

	return decorator



class CronTests(unittest.TestCase):
	def test_next(self):
		self.assertEqual(datetime(1970, 1, 1, 0, 0, 1), nextTime(datetime(1970, 1, 1)))
		self.assertEqual(datetime(1970, 1, 1, 0, 1, 0), nextTime(datetime(1970, 1, 1), minute=[1]))
		self.assertEqual(datetime(1970, 1, 1, 2, 0, 0), nextTime(datetime(1970, 1, 1), hour=[2, 4]))

		self.assertEqual(datetime(1970, 1, 1, 2, 1, 1), nextTime(datetime(1970, 1, 1, 2, 1, 0), hour=[2, 4]))
		self.assertEqual(datetime(1970, 1, 1, 4, 0, 0), nextTime(datetime(1970, 1, 1, 3, 1, 0), hour=[2, 4]))
		self.assertEqual(datetime(1970, 1, 1, 4, 0, 0), nextTime(datetime(1970, 1, 1, 2, 1, 0), hour=[2, 4], minute=[0]))

		self.assertEqual(datetime(1971, 2, 10), nextTime(datetime(1970, 2, 28), month=[2], day=[10, 20]))

		self.assertEqual(datetime(1972, 2, 29), nextTime(datetime(1971, 1, 1), month=[2], day=[29]))


if __name__ == '__main__':
	unittest.main()
