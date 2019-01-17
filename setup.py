#!/usr/bin/env python
# this project is licensed under the WTFPLv2, see COPYING.txt for details

import glob
import os.path
import sys

from setuptools import setup, find_packages


if __name__ == '__main__':
	with open(os.path.join(sys.path[0], 'README.rst')) as fd:
		README = fd.read().strip()

	setup(
		name='eyeditor',
		version='0.0.1',

		description='EYE - A Qt-based scriptable text editor',
		long_description=README,
		url='https://github.com/hydrargyrum/eye',
		author='Hg',
		license='WTFPLv2',
		classifiers=[
			'Development Status :: 3 - Alpha',

			'Environment :: X11 Applications :: Qt',

			'Intended Audience :: Developers',
			'Intended Audience :: System Administrators',

			'License :: Public Domain',

			'Topic :: Text Editors',
			'Topic :: Text Editors :: Integrated Development Environments (IDE)',

			'Programming Language :: Python :: 2',
			'Programming Language :: Python :: 2.7',
			'Programming Language :: Python :: 3',
			'Programming Language :: Python :: 3.2',
			'Programming Language :: Python :: 3.3',
			'Programming Language :: Python :: 3.4',
			'Programming Language :: Python :: 3.5',
			'Programming Language :: Python :: 3.6',
		],
		keywords='code development editor qt script ide',

		packages=find_packages(),
		install_requires=['six', 'PyQt5', 'QScintilla', 'pyxdg'],
		data_files=[
			('share/eye/colorschemes', glob.glob('data/colorschemes/*')),
			('share/eye/sample_conf', glob.glob('data/sample_conf/*')),
			('share/applications', ['data/eye.desktop']),
			('share/icons/hicolor/256x256/apps', ['data/eye.png']),
		],
		entry_points={
			'console_scripts': [
				'eye=eye.app:main'
			]
		}
	)
