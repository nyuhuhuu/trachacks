= About this software =
 * Trac Report Manager is a Trac plugin.

= Install =
 You can install this software as normal Trac plugin.

 1. Uninstall Trac Report Manager if you have installed before.

 2. Change to the directory containning setup.py.

 3. If you want to install this plugin globally, that will install this plugin to the python path:
  * python setup.py install

 4. If you want to install this plugin to trac instance only:
  * python setup.py bdist_egg
  * copy the generated egg file to the trac instance's plugin directory
  {{{
cp dist/*.egg /srv/trac/env/plugins
}}}

 5. Config trac.ini:
  {{{
[components]
reportmanager.* = enabled
}}}

= Prerequisite =
 * [http://trac-hacks.org/wiki/WebAdminPlugin WebAdminPlugin]

= Usage =
 * TBD