from __future__ import (division, absolute_import, print_function,
                        unicode_literals)

import logging
import re

from angular2tmpl import module

LOGGER = logging.getLogger(__name__)


ng = module.Module('ng')


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
        # TODO(eitan): use 'with' Jinja2 extension to simulate isolate scope
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
