# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# Build the files to DocString reference
# sphinx-apidoc -o docs/development/foundations/code_structure src
# Build html
# sphinx-build -b html -v docs docs/_build/html
# start docs/_build/html/index.html


import datetime
import os
import sys
from importlib import metadata

sys.path.insert(0, os.path.abspath("../src"))
print(sys.path)

CONF_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__)))
ROOT_DIR = os.path.abspath(os.path.join(CONF_DIR, os.pardir))

# -- Project information -----------------------------------------------------
project = "flowchem"
YEAR = datetime.date.today().strftime("%Y")
author = "Dario Cambié, Jakob Wolf, Wei-Hsin Hsu, Samuel Saraiva"
copyright = f"{YEAR}, {author}"
release = metadata.version("flowchem")

# -- General configuration ---------------------------------------------------
extensions = [
    "myst_parser",
    "sphinx_design",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinxcontrib.openapi",
    "sphinxcontrib.httpdomain",
]

source_suffix = [".rst", ".md"]
autodoc_member_order = "bysource"

myst_enable_extensions = [
    # "amsmath",
    "colon_fence",
    "deflist",
    # "dollarmath",
    "fieldlist",
    "html_admonition",
    "html_image",
    "replacements",
    "smartquotes",
    "strikethrough",
    "substitution",
    "tasklist",
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

# -- Options for HTML output -------------------------------------------------
# html_logo = "http://placekitten.com/200/90"
#html_theme = "furo"
#html_theme_options = {
#    "light_css_variables": {
#        "primary-color": "#005555",
#    },
#    "dark_css_variables": {
#        "primary-color": "#e5c07b",
#    },
#}
#html_show_copyright = False
#html_show_sphinx = False

#html_static_path = ["_static"]
#html_css_files = [
#    "flowchem.css",
#]