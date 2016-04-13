# this project is licensed under the WTFPLv2, see COPYING.txt for details

import sys

__all__ = ('bytes', 'str')


if sys.version_info.major < 3:
    bytes, str = str, unicode
else:
    bytes, str = bytes, str

