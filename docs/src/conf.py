# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# Generate modules:
#  sphinx-apidoc -o ./src/modules/ ../src/ska-mid-dish-steering-control/

import os
import sys

sys.path.insert(0, os.path.abspath("../../src"))

# -- Project information -----------------------------------------------------

project = "SKA-Mid Weather Monitoring System"
copyright = "2024, SKAO"
author = "Team Wombat"

# The full version, including alpha/beta/rc tags
release = "0.1.0"


# -- General configuration ---------------------------------------------------

autodoc_typehints_format = "short"

autodoc_default_options = {
    "member-order": "bysource",
}

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.coverage",
    "sphinx.ext.doctest",
    "sphinx.ext.intersphinx",
    "sphinx_autodoc_typehints",
    "sphinxcontrib.plantuml",
    "enum_tools.autoenum",
]
plantuml_syntax_error_image = True

# This will use the type annotations from your function signature to populate the
# type-related fields in your documentation.
autodoc_typehints = "description"

# Add any paths that contain templates here, relative to this directory.
# templates_path = ["_templates"]

# The suffix(es) of source filenames.
# You can specify multiple suffix as a list of string:
source_suffix = [".rst"]

# The master toctree document.
master_doc = "index"

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
add_module_names = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = "sphinx"

# If true, `todo` and `todoList` produce output, else they produce nothing.
# todo_include_todos = True

if os.environ.get("LOCAL_BUILD") == "True":
    plantuml = "java -jar %s" % os.path.join(
        os.path.dirname(__file__), "utils", "plantuml.jar"
    )

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "ska_ser_sphinx_theme"

html_context = {}
# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
# html_static_path = []

intersphinx_mapping = {
    "python": ("https://docs.python.org/3.10/", None),
    "pymodbus": ("https://pymodbus.readthedocs.io/en/latest/", None),
    "ska-mid-wms-interface": ("https://developer.skao.int/projects/ska-mid-wms-interface/en/latest/", None),
}

# nitpicky = True
# nitpick_ignore = [("py:class", "")]
