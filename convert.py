#!/bin/env python2.7

from __future__ import (division, absolute_import, print_function,
                        unicode_literals)

import argparse
import collections
import inspect
import io
import logging
import re
import sys

from xml.dom import minidom

import html5lib

LOGGER = logging.getLogger(__name__)


def main(args):
    parser = argparse.ArgumentParser()
    parser.add_argument('--infile', required=True)
    parser.add_argument('--outfile', type=file, default=sys.stdout)
    parser.add_argument('--debug', action='store_true')
    args = parser.parse_args(args)
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    LOGGER.info('Converting %s => %s',
                args.infile, args.outfile)
    converter = Converter()
    converter.module(noscript)
    with open(args.infile, 'rb') as f:
        document = converter.Convert(f)
    xml = document.toxml(encoding='utf-8')
    # Strip off XML declaration
    xml = xml[xml.index(b'>') + 1:]
    args.outfile.write(xml)


class Converter(object):

    parser = html5lib.HTMLParser(
        tree=html5lib.getTreeBuilder('dom'),
        namespaceHTMLElements=False,
    )

    def __init__(self, loadNg=True):
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
        # TODO(eitan): be more nuanced about replacing $, &&, !, ||, etc.
        text = text \
            .replace('$', '_') \
            .replace('&&', ' and ') \
            .replace('||', ' or ') \
            .replace('!', ' not ') \
            .replace(' not =', '!=')  # '!=' -> ' not =' -> '!='
        # TODO(eitan): This assumes | and : don't appear in strings
        parts = text.split('|')
        for i, filter in enumerate(parts[1:], start=1):
            args = filter.split(':')
            if args[0].strip() == 'orderBy':
                args[0] = 'sort'
                if len(args) >= 2:
                    args[1] = 'attribute=' + args[1]
                    if len(args) >= 3:
                        args[2] = 'reverse=' + args[2]
            if len(args) > 1:
                parts[i] = '%s(%s)' % (args[0], ','.join(args[1:]))
            else:
                parts[i] = args[0]
        return '|'.join(parts)

    def _convert_text_node(self, document, element):
        data = element.wholeText
        out = io.StringIO()
        i = 0
        while i < len(data):
            start = data.find('{{', i)
            if start == -1:
                break
            end = data.find('}}', start)
            if end == -1:
                break
            out.write(data[i:start])
            expr = data[start + 2:end]
            out.write('{{')
            out.write(self.ConvertExpr(expr))
            out.write('}}')
            i = end + 2
        out.write(data[i:])
        element.replaceWholeText(out.getvalue())

    def _convert(self, document, element):
        if element.nodeType == minidom.Node.TEXT_NODE:
            return self._convert_text_node(document, element)
        elif element.nodeType != minidom.Node.ELEMENT_NODE:
            # TODO(eitan): handle text nodes and comments appropriately
            return
        tagName = self._normalize_name(element.tagName)
        attrs = self._get_attribute_map(element)
        # TODO(eitan): convert ngAttrFoo -> foo
        LOGGER.debug('%s node has attrs %s', tagName, attrs.keys())
        for directive in self._directives:
            LOGGER.debug('Processing directive %s', directive.name)
            if 'A' in directive.restrict and directive.name in attrs:
                value = element.getAttribute(attrs[directive.name])
                directive(
                    document=document,
                    element=element,
                    converter=self,
                    attrs=attrs,
                    style='A',
                    config=self._directive_config[directive.name],
                    value=value,
                )
            if 'E' in directive.restrict and directive.name == tagName:
                directive(
                    document=document,
                    element=element,
                    converter=self,
                    attrs=attrs,
                    style='E',
                    config=self._directive_config[directive.name],
                )
            if element.parentNode is None:
                return
        # Must slurp into list because elements may be removed during iteration
        # TODO(eitan): something safer for modifying during iteration
        for child in list(element.childNodes):
            self._convert(document, child)
        # Avoid invalid self-closing tags by inserting a comment in empty tags
        # TODO(eitan): check against list of HTML5 bodyless tags
        if not element.childNodes:
            element.appendChild(document.createComment('nocollapse'))

    def _get_attribute_map(self, element):
        if element.attributes:
            return {self._normalize_name(attr): attr
                    for attr in element.attributes.keys()}
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
                     replace=False,
                     inject=None):
            self.name = name
            self.func = func
            self.priority = priority = priority
            self.terminal = terminal
            self.restrict = restrict
            self.replace = replace
            if inject is None:
                inject = inspect.getargspec(func).args
            self.inject = inject

        def __call__(self, **kwargs):
            args = [kwargs.get(arg) for arg in self.inject]
            self.func(*args)


ng = Module('ng')


@ng.directive()
def ngHide(document, element, converter, value):
    expr = converter.ConvertExpr(value)
    open_tag = document.createTextNode(
        '{%% if not (%s) %%}' % expr)
    close_tag = document.createTextNode('{% endif %}')
    # TODO(eitan): make debugging comments optional
    comment = document.createComment(
        '%s = {{ (%s).__repr__() }}' % (expr, expr))
    element.parentNode.insertBefore(comment, element)
    element.parentNode.insertBefore(open_tag, element)
    element.parentNode.insertBefore(close_tag, element.nextSibling)


@ng.directive(name='ngIf')
@ng.directive()
def ngShow(document, element, converter, value):
    expr = converter.ConvertExpr(value)
    open_tag = document.createTextNode('{%% if %s %%}' % expr)
    close_tag = document.createTextNode('{% endif %}')
    # TODO(eitan): make debugging comments optional
    comment = document.createComment(
        '%s = {{ (%s).__repr__() }}' % (expr, expr))
    element.parentNode.insertBefore(comment, element)
    element.parentNode.insertBefore(open_tag, element)
    element.parentNode.insertBefore(close_tag, element.nextSibling)


@ng.directive()
def ngCloak(document, element, style, attrs):
    # TODO(eitan): support ngCloak class
    if 'style' == 'A':
        element.removeAttribute(attrs['ngCloak'])


@ng.directive(restrict='AE')
def ngInclude(document, element, converter, style, attrs, value=None):
    for child in element.childNodes:
        element.removeChild(child)
    if style == 'E':
        value = element.getAttribute(attrs['src'])
    # TODO(eitan): deal with the include string possibly getting escaped if it
    # uses ", etc.
    include_tag = document.createTextNode(
        '{%% include %s %%}' % converter.ConvertExpr(value))
    element.appendChild(include_tag)


@ng.directive(restrict='AE')
def ngView(document, element, style, attrs):
    """Implements ngView.

    You must provide two template variables:
        ngViewRoutes: a dict of routeName: template
        ngViewRoute: the current routeName
    """
    for child in element.childNodes:
        element.removeChild(child)
    include_tag = document.createTextNode(
        '{% include ngViewRoutes[ngViewRoute] %}')
    element.appendChild(include_tag)


@ng.directive()
def ngRepeat(document, element, converter, value):
    LOOP_VARS = {
        '_index': 'loop.index0',
        '_first': 'loop.first',
        '_last': 'loop.last',
        '_middle': '(not loop.first and not loop.last)',
        '_even': 'loop.cycle(True, False)',
        '_odd': 'loop.cycle(False, True)',
    }
    open_tag = document.createTextNode(
        '{%% for %s %%}' % converter.ConvertExpr(value))
    setup_tag = document.createTextNode(
        ''.join(
            '{%% set %s = %s %%}' % item
            for item in LOOP_VARS.iteritems()
        )
    )
    close_tag = document.createTextNode('{% endfor %}')
    element.parentNode.insertBefore(open_tag, element)
    element.insertBefore(setup_tag, element.childNodes[0])
    element.parentNode.insertBefore(close_tag, element.nextSibling)


OPTIONS_RE = re.compile(r'\A([\w.]+) as ([\w.]+) for ([\w.]+) in ([\w.]+)\Z')


@ng.directive(restrict='E')
def select(document, element, attrs):
    if 'ngOptions' not in attrs:
        LOGGER.debug('select: ngOptions not found - do nothing')
        return
    options = element.getAttribute(attrs['ngOptions'])
    match = OPTIONS_RE.match(options)
    if not match:
        LOGGER.debug('select: unrecognized ngOptions format "%s" - do nothing',
                     options)
        # TODO(eitan): support the many other syntaxes
        return
    select, label, value, array = match.groups()
    start_loop = document.createTextNode(
        '{%% for %s in %s %%}' % (value, array))
    loop_body = document.createElement('option')
    loop_body.appendChild(document.createTextNode('{{%s}}' % label))
    loop_body.setAttribute('value', '{{%s}}' % select)
    end_loop = document.createTextNode('{% endfor %}')
    element.appendChild(start_loop)
    element.appendChild(loop_body)
    element.appendChild(end_loop)


noscript = Module('noscript')


@noscript.directive(name='script', restrict='E')
def delete_scripts(document, element):
    element.parentNode.removeChild(element)


if __name__ == '__main__':
    main(sys.argv[1:])
