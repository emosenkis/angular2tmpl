#!/bin/env python2.7

from __future__ import (division, absolute_import, print_function,
                        unicode_literals)

import argparse
import collections
import io
import logging
import os
import sys

from xml.dom import minidom

import html5lib

LOGGER = logging.getLogger(__name__)


def main(args):
    parser = argparse.ArgumentParser()
    parser.add_argument('--infile', required=True)
    parser.add_argument('--outfile', type=file, default=sys.stdout)
    parser.add_argument('--basedir')
    args = parser.parse_args(args)
    if args.basedir is None:
        args.basedir = os.path.dirname(args.infile)
    LOGGER.info('Converting %s => %s in %s.',
                args.infile, args.outfile, args.basedir)
    converter = Converter(args.basedir)
    converter.module(noscript)
    with open(args.infile, 'rb') as f:
        document = converter.Convert(f)
    args.outfile.write('<!doctype html>\n')
    args.outfile.write(document.toxml(encoding='utf-8'))


class Converter(object):

    parser = html5lib.HTMLParser(
        tree=html5lib.getTreeBuilder("dom"),
        namespaceHTMLElements=False,
    )

    def __init__(self, basedir, loadNg=True):
        self.dir = basedir
        self.modules = []
        self._directives = []
        self._directive_config = collections.defaultdict(dict)
        if loadNg:
            self.module(ng)

    def module(self, mod):
        self.modules.append(mod)
        self._directives.extend(mod.directives)
        self._directives.sort(key=lambda x: x.priority, reverse=True)

    def config(self, directive, key, value):
        self._directive_config[directive][key] = value

    def Convert(self, f):
        document = self.parser.parse(f)
        self._convert(document, document.documentElement)
        return document

    def ConvertExpr(self, text):
        # TODO(eitan): be more nuanced about replacing $
        text = text.replace('$', '_')
        # TODO(eitan): This assumes | and : don't appear in strings
        parts = text.split('|')
        for i, filter in enumerate(parts[1:], start=1):
            args = filter.split(':')
            if args[0].strip() == 'orderBy':
                args[0] = 'sort'
            if len(args) > 1:
                parts[i] = '%s(%s)' % (args[0], ','.join(args[1:]))
            else:
                parts[i] = args[0]
        return '|'.join(parts)

    def _convert(self, doc, elem):
        if elem.nodeType != minidom.Node.ELEMENT_NODE:
            # TODO(eitan): handle text nodes and comments appropriately
            return
        tagName = self._normalize_name(elem.tagName)
        attrs = self._get_attribute_map(elem)
        # TODO(eitan): convert ngAttrFoo -> foo
        LOGGER.debug('%s node has attrs %s', tagName, attrs.keys())
        for directive in self._directives:
            if 'A' in directive.restrict and directive.name in attrs:
                value = elem.getAttribute(attrs[directive.name])
                directive(
                    doc,
                    elem,
                    converter=self,
                    attrs=attrs,
                    style='A',
                    config=self._directive_config[directive.name],
                    value=value,
                )
            if 'E' in directive.restrict and directive.name == tagName:
                directive(
                    doc,
                    elem,
                    converter=self,
                    attrs=attrs,
                    style='E',
                    config=self._directive_config[directive.name],
                )
            if elem.parentNode is None:
                return
        # Must slurp into list because elements may be removed during iteration
        # TODO(eitan): something safer for modifying during iteration
        for child in list(elem.childNodes):
            self._convert(doc, child)

    def _get_attribute_map(self, elem):
        if elem.attributes:
            return {self._normalize_name(attr): attr
                    for attr in elem.attributes.keys()}
        else:
            return {}

    def _normalize_name(self, name):
        """See http://docs.angularjs.org/guide/directive"""
        # Strip x- or data- prefix
        if name.lower().startswith('x-'):
            name = name[2:]
        elif name.lower().startswith('data-'):
            name = name[5:]
        out = io.StringIO()
        nextUpper = False
        for char in name:
            if char in (':', '-', '_'):
                nextUpper = True
                continue
            if nextUpper:
                char = char.upper()
            else:
                char = char.lower()
            out.write(char)
            nextUpper = False
        return out.getvalue()


class Module(object):
    def __init__(self, name):
        self.name = name
        self.directives = []

    def directive(self,
                  name=None,
                  **kwargs):
        def decorator(func):
            _name = func.__name__ if name is None else name
            directive = self.Directive(_name, func, **kwargs)
            self.directives.append(directive)
            return func
        return decorator

    class Directive(object):
        def __init__(self,
                     name,
                     func,
                     priority=0,
                     terminal=False,
                     restrict='A',
                     replace=False):
            self.name = name
            self.func = func
            self.priority = priority = priority
            self.terminal = terminal
            self.restrict = restrict
            self.replace = replace

        def __call__(self, *args, **kwargs):
            self.func(*args, **kwargs)


ng = Module('ng')


@ng.directive()
def ngHide(doc, elem, converter=None, value=None, **kwargs):
    open_tag = doc.createTextNode('{%% if not (%s) %%}'
                                  % converter.ConvertExpr(value))
    close_tag = doc.createTextNode('{% endif %}')
    elem.parentNode.insertBefore(open_tag, elem)
    elem.parentNode.insertBefore(close_tag, elem.nextSibling)


@ng.directive(name='ngIf')
@ng.directive()
def ngShow(doc, elem, converter=None, value=None, **kwargs):
    open_tag = doc.createTextNode('{%% if %s %%}'
                                  % converter.ConvertExpr(value))
    close_tag = doc.createTextNode('{% endif %}')
    elem.parentNode.insertBefore(open_tag, elem)
    elem.parentNode.insertBefore(close_tag, elem.nextSibling)


@ng.directive()
def ngCloak(doc, elem, style=None, attrs=None, **kwargs):
    # TODO(eitan): support ngCloak class
    if 'style' == 'A':
        elem.removeAttribute(attrs['ngCloak'])


@ng.directive(restrict='AE')
def ngInclude(doc, elem,
              converter=None, style=None, value=None, attrs=None, **kwargs):
    for child in elem.childNodes:
        elem.removeChild(child)
    if style == 'E':
        value = elem.getAttribute(attrs['src'])
    # TODO(eitan): deal with the include string possibly getting escaped if it
    # uses ", etc.
    include_tag = doc.createTextNode("{%% include %s %%}"
                                     % converter.ConvertExpr(value))
    elem.appendChild(include_tag)


@ng.directive(restrict='AE')
def ngView(doc, elem, style=None, attrs=None, **kwargs):
    """Implements ngView.

    You must provide two template variables:
        ngViewRoutes: a dict of routeName: template
        ngViewRoute: the current routeName
    """
    for child in elem.childNodes:
        elem.removeChild(child)
    include_tag = doc.createTextNode('{% include ngViewRoutes[ngViewRoute] %}')
    elem.appendChild(include_tag)


@ng.directive()
def ngRepeat(doc, elem, converter=None, value=None, **kwargs):
    LOOP_VARS = {
        '_index': 'loop.index0',
        '_first': 'loop.first',
        '_last': 'loop.last',
        '_middle': '(not first and not last)',
        '_even': 'loop.cycle(True, False)',
        '_odd': 'loop.cycle(False, True)',
    }
    open_tag = doc.createTextNode('{%% for %s %%}'
                                  % converter.ConvertExpr(value))
    setup_tag = doc.createTextNode(
        ''.join(
            '{%% set %s = %s %%}' % item
            for item in LOOP_VARS.iteritems()
        )
    )
    close_tag = doc.createTextNode('{% endfor %}')
    elem.parentNode.insertBefore(open_tag, elem)
    elem.insertBefore(setup_tag, elem.childNodes[0])
    elem.parentNode.insertBefore(close_tag, elem.nextSibling)


noscript = Module('noscript')


@noscript.directive(name='script', restrict='E')
def delete_scripts(doc, elem, **kwargs):
    elem.parentNode.removeChild(elem)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main(sys.argv[1:])
