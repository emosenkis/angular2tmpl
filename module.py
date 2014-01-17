from __future__ import (division, absolute_import, print_function,
                        unicode_literals)

import inspect


class Module(object):
    def __init__(self, name):
        self.name = name
        self.directives = []
        self.filters = []

    def directive(self,
                  name=None,
                  **kwargs):
        def decorator(func):
            _name = func.__name__ if name is None else name
            directive = self.Directive(_name, func, **kwargs)
            self.directives.append(directive)
            return func
        return decorator

    def filter(self,
               name=None):
        def decorator(func):
            _name = func.__name__ if name is None else name
            self.filters.append((_name, func))
            return func
        return decorator

    def apply_to_jinja_env(self, env):
        for name, filter in self.filters:
            env.filters[name] = filter

    class Directive(object):
        def __init__(self,
                     name,
                     func,
                     priority=0,
                     terminal=False,
                     restrict='A',
                     replace=False,
                     inject=None,
                     templatePath=None,
                     scope=None):
            self.name = name
            self.func = func
            self.priority = priority = priority
            self.terminal = terminal
            self.restrict = restrict
            self.replace = replace
            if inject is None:
                inject = inspect.getargspec(func).args
            self.inject = inject
            self.templatePath = templatePath
            self.scope = scope

        def __call__(self, **kwargs):
            if self.scope is not None:
                self._applyScope(
                    kwargs['document'],
                    kwargs['element'],
                    kwargs['attrs'],
                    kwargs['converter'],
                )
            if self.templatePath is not None:
                self._insertTemplate(kwargs['document'], kwargs['element'])
            args = [kwargs.get(arg) for arg in self.inject]
            self.func(*args)

        def _insertTemplate(self, document, element):
            include_tag = document.createTextNode(
                '{%% include \'%s\' %%}' % self.templatePath)
            element.appendChild(include_tag)

        def _applyScope(self, document, element, attrs, converter):
            text = ''
            for target, source in self.scope.iteritems():
                if source.startswith('='):
                    source = source[1:]
                else:
                    raise NotImplementedError(
                        'Scope sources must begin with = for now.')
                if not source:
                    source = target
                if source in attrs:
                    sourceExpr = element.getAttribute(attrs[source])
                else:
                    sourceExpr = 'null'
                sourceExpr = converter.ConvertExpr(sourceExpr)
                text += '{%% set %s = %s %%}' % (target, sourceExpr)
            if text:
                # TODO(eitan): use 'with' Jinja2 extension to simulate isolate
                #              scope
                assignment = document.createTextNode(text)
                element.appendChild(assignment)
