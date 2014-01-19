angular2tmpl
============
Convert AngularJS templates to Jinja2 templates for SEO.

The basic idea is to create a version of an Angular-powered website that can be
rendered on the server for consumption by search engines. This is accomplished
in two parts:

1. Use angulart2tmpl to convert Angular templates to Jinja2 templates. This may
   require implementing custom Angular directives in Python (using
   ``xml.dom.minidom``).
2. Implement a Python WSGI app that gathers the necessary data using the same
   API that powers your Angular app and passes it to the generated Jinja2
   templates.

This project expressly does not intend to be a full implementation of AngularJS
in Python. Instead, it intends to implement a minimal subset of Angular
sufficient to provide server-side rendering for the purposes of SEO. The
resulting server-rendered sites need not be interactive, but they should look
roughly the same as their JavaScript-based counterparts.


Features
--------
- Reuses existing Angular templates and backend API
- Avoids the expense and complexity of running a headless browser
- Compatible with PaaS platforms such as Google App Engine


Status
------
angular2tmpl is pre-alpha software. It currently implements a *very* minimal
subset of the ``ng`` and ``ngRoute`` modules and makes little attempt to address
edge cases. No guarantees are made at this time about maintaining backwards
compatibility. Unit tests are still a twinkle in its eye.

That said, angular2tmpl does currently satisfy the needs of the site that it was
built for.


Installation & Dependencies
---------------------------
Installation is easy::

    pip install angular2tmpl

The only dependencies are Jinja2 and html5lib, both of which will be
automatically installed. angular2tmpl was built on Python 2.7, but with the
intention of making conversion with 2to3 fairly painless. If you try it, let me
know how it goes.


Usage
-----
Just run ``angular2tmpl``. Try ``--help`` to see the available flags and default
values, then run it on each of your Angular templates. angular2tmpl directives
are intended to be similar to Angular directives while staying Pythonic and
taking advantage of the reduced complexity that comes from non-interactive
rendering. See ``modules/ng.py`` for examples.

Due to differences in the semantics of Angular vs. Jinja2 expressions, some
modifications to the default Jinja2 environment and your template data are
necessary:

1. Angular is extremely generous about ignoring errors and missing values in
   templates. To emulate this behavior, set the ``undefined`` property of your
   Jinja2 environment object to ``angular2tmpl.jinja2.PermissiveUndefined``.
2. JavaScript objects allow access to non-existent properties and treat
   ``foo.bar`` and ``foo['bar']`` the same way. To get the same behavior out of
   your template variables, convert them using ``angular2tmpl.jinja2.js_data``.


Background
----------
For more information about how Google handles JavaScript-heavy sites and how to
make it request a special server-rendered version of your site, see
https://developers.google.com/webmasters/ajax-crawling/docs/specification. For
more information about other approaches to making Angular work within the bounds
of this specification, see
http://www.ng-newsletter.com/posts/serious-angular-seo.html.



Disclaimers
-----------
angular2tmpl is not affiliated in any way with Google or AngularJS.
