#!/usr/bin/env python
# this project is licensed under the WTFPLv2, see COPYING.txt for details

from setuptools import setup, find_packages

import glob

setup(
	name='eye',
	version='0.0.1',

	description='A Qt-based scriptable text editor',
	long_description='Edit Your Editor - A Qt-based scriptable text editor',
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
	],
	keywords='code development editor qt script',

	packages=find_packages(),
	install_requires=['six'],
	data_files=[
		('eye/colorschemes', glob.glob('data/colorschemes/*')),
		('share/applications', 'data/eye.desktop'),
	],
	entry_points={
		'console_scripts': [
			'eye=eye.app:main'
		]
	}
)
