"""Sphinx configuration for Kataglyphis-WebDavClient documentation."""

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import sys
from pathlib import Path


sys.path.insert(0, str(Path("../../").resolve()))

project = "Kataglyphis-WebDavClient"
project_copyright = "2024, Jonas Heinle"
author = "Jonas Heinle"
release = "0.0.1"
globals()["copyright"] = project_copyright

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

html_theme = "sphinx_rtd_theme"
html_theme_options = {
    "style_nav_header_background": "#6af0ad",
}
html_static_path = ["_static"]

myst_heading_anchors = 3

# Enable the processing of Markdown files
source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

# Here we assume that the file is at _static/css/custom.css
html_css_files = ["css/custom.css"]

_SPHINX_EXPORTS = (
    project,
    project_copyright,
    author,
    release,
    myst_enable_extensions,
    exhale_args,
    templates_path,
    exclude_patterns,
    html_theme,
    html_theme_options,
    html_static_path,
    source_suffix,
    html_css_files,
)
