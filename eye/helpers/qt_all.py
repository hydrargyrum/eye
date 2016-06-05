# this project is licensed under the WTFPLv2, see COPYING.txt for details

"""Module importing all Qt symbols

This module just imports every Qt symbol from QtCore, QtGui, QtWidgets and Qsci and exports them all.

This module avoids having to remember in which Qt submodule is a particular Qt/QScintilla class. It should not be used
in released plugins but can be used in config files like this::

	from eye.helpers.qt_all import *

Even though it is bad practice to import `*` in released code, user config files are not released code, and it can be
simpler to write such file with this module.
"""

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.Qsci import *

