from __future__ import (division, absolute_import, print_function,
                        unicode_literals)

import jinja2


class PermissiveUndefined(jinja2.Undefined):
    def __getattr__(self, name):
        return PermissiveUndefined(name)

    def __getitem__(self, name):
        return PermissiveUndefined(name)

    def __call__(self, *args, **kwargs):
        return PermissiveUndefined()


class JSDict(dict):
    def __getitem__(self, item):
        try:
            return super(JSDict, self).__getitem__(item)
        except KeyError:
            return PermissiveUndefined(item)

    def __getattr__(self, name):
        return self[name]


class JSList(list):
    @property
    def length(self):
        return len(self)


# TODO(eitan): this won't work for dict and list literals inside expressions in
#              the template
def js_data(obj):
    if type(obj) is dict:
        out = JSDict()
        for k, v in obj.iteritems():
            out[k] = js_data(v)
    elif type(obj) is list:
        out = JSList(js_data(item) for item in obj)
    else:
        out = obj
    return out
