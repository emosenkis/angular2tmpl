from __future__ import (division, absolute_import, print_function,
                        unicode_literals)

import collections
import io
import logging

from xml.dom import minidom

import html5lib

import angular2tmpl

LOGGER = logging.getLogger(__name__)
HTML5_VOID_ELEMENTS = set((
    'area',
    'base',
    'br',
    'col',
    'embed',
    'hr',
    'img',
    'input',
    'keygen',
    'link',
    'menuitem',
    'meta',
    'param',
    'source',
    'track',
    'wbr',
))


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
            self.module(angular2tmpl.ng)

    def module(self, mod):
        self.modules.append(mod)
        self._directives.extend(mod.directives)
        self._directives.sort(key=lambda x: x.priority, reverse=True)

    def config(self, directive, key, value):
        self._directive_config[directive][key] = value

    def Convert(self, input):
        document = self.parser.parse(input)
        self._convert_element(document, document.documentElement)
        xml = document.toxml(encoding='utf-8')
        # Strip off XML declaration
        xml = xml[xml.index(b'>') + 1:]
        return xml

    def ConvertExpr(self, text):
        # TODO(eitan): be more nuanced about replacing $, &&, !, ||, etc.
        # TODO(eitan): should === be == or is?
        text = text \
            .replace('null', 'none') \
            .replace('$', '_') \
            .replace('&&', ' and ') \
            .replace('||', ' or ') \
            .replace('===', '==') \
            .replace('!==', '!=') \
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

    def _convert_text_node(self, document, node):
        data = node.wholeText
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
        node.replaceWholeText(out.getvalue())

    def _convert_element(self, document, element):
        tagName = self._normalize_name(element.tagName)
        attrs = self._get_attribute_map(element)
        # TODO(eitan): convert ngAttrFoo -> foo
        for directive in self._directives:
            if 'A' in directive.restrict and directive.name in attrs:
                LOGGER.debug('Applying directive %s to <%s> for attribute',
                             directive.name, element.tagName)
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
                LOGGER.debug('Applying directive %s for element',
                             directive.name)
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
        # TODO(eitan): something safer for modifying during iteration - maybe
        #              non-recursive
        for child in list(element.childNodes):
            if child.parentNode != element:
                continue
            if child.nodeType == minidom.Node.TEXT_NODE:
                self._convert_text_node(document, child)
            elif child.nodeType == minidom.Node.ELEMENT_NODE:
                self._convert_element(document, child)
            # TODO(eitan): handle comments appropriately
        # Minidom will produce self-closing tags whenever it prints an empty
        # element. In HTML5, the self-closing status is not honored except in
        # the case of 'foreign elements' (SVG and MathML). To force separate
        # open and close tags, add an empty comment.
        if not (tagName in HTML5_VOID_ELEMENTS or element.childNodes):
            element.appendChild(document.createComment(''))

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
