from __future__ import (division, absolute_import, print_function,
                        unicode_literals)

from angular2tmpl import module

noscript = module.Module('noscript')


@noscript.directive(name='script', restrict='E')
def delete_scripts(document, element):
    element.parentNode.removeChild(element)
