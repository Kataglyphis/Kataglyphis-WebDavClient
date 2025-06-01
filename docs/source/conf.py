# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import os
import sys

sys.path.insert(0, os.path.abspath("../../"))

project = "Kataglyphis-WebDavClient"
copyright = "2024, Jonas Heinle"
author = "Jonas Heinle"
release = "0.0.1"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",  # For Google and NumPy style docstrings
    "sphinx.ext.viewcode",  # To include links to the source code
    "myst_parser",  # adding .md files
]

myst_enable_extensions = [
    "dollarmath",  # Enables dollar-based math syntax
    "amsmath",  # Supports extended LaTeX math environments
    "colon_fence",  # Allows ::: for directives
    "deflist",  # Enables definition lists
]

exhale_args = {
    "containmentFolder": "./api",
    "rootFileName": "library_root.rst",
    "rootFileTitle": "Library API",
    "doxygenStripFromPath": "../..",
    "createTreeView": True,
}

templates_path = ["_templates"]
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "press"
html_theme_options = {
    "palette": "dark",  # Set dark mode as default
    "fixed_sidebar": True,
}
html_static_path = ["_static"]

# Enable the processing of Markdown files
source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

# Here we assume that the file is at _static/css/custom.css
html_css_files = ["css/custom.css"]
