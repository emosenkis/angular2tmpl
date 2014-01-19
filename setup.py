#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name='angular2tmpl',
    version='0.1.0',
    packages=find_packages(),
    scripts=['bin/angular2tmpl'],
    author='Eitan Mosenkis',
    author_email='eitan@mosenkis.net',
    description='Convert AngularJS templates to Jinja2 templates for SEO.',
    long_description=open('README.rst').read(),
    license='MIT',
    keywords='angularjs jinja2 seo',
    url='https://github.com/emosenkis/angular2tmpl',
    install_requires=['html5lib >= 1.0b3', 'Jinja2 >= 2.7.1']
)
