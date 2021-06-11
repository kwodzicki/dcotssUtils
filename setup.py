import setuptools
from distutils.util import convert_path

main_ns  = {};
ver_path = convert_path("dcotssUtils/version.py");
with open(ver_path) as ver_file:
  exec(ver_file.read(), main_ns);

setuptools.setup(
  name             = "DCOTSS_Utils",
  description      = "Small GUI with some utilities for the DCOTSS Project",
  url              = "",
  author           = "Kyle R. Wodzicki",
  author_email     = "wodzicki@tamu.com",
  version          = main_ns['__version__'],
  packages         = setuptools.find_packages(),
  install_requires = [ "pyqt5" ],
  scripts          = ['bin/dcotssUtils'],
  zip_safe         = False,
);
