# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html
#
# -- Project information -----------------------------------------------------

import typing

from wakepy import __version__

if typing.TYPE_CHECKING:
    from sphinx.application import Sphinx

project = "wakepy"
copyright = "2023–2024, Niko Föhr"
author = "Niko Föhr"

# The full version, including alpha/beta/rc tags
release = __version__


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    # Adds support for NumPy style docstrings for autodoc
    # Note: numpydoc must be listed before myst_parser in order to make the
    # NamedTuples fix (https://github.com/numpy/numpydoc/pull/527) work.
    "numpydoc",
    # Markdown (MyST) format support for Sphinx
    "myst_parser",
    # Sphinx Design adds some sphinx directives for UI components
    # See: https://sphinx-design.readthedocs.io/
    "sphinx_design",
    # Add copy button to code blocks
    # See: https://sphinx-copybutton.readthedocs.io/
    "sphinx_copybutton",
    "sphinx.ext.autosummary",
]

# Needed by sphinx_design
# See: https://sphinx-design.readthedocs.io/en/latest/get_started.html
myst_enable_extensions = [
    "attrs_inline",
    # Enable block attributes, like: {emphasize-lines="2,3"}
    # See: https://myst-parser.readthedocs.io/en/latest/syntax/optional.html#block-attributes
    "attrs_block",
    # Allow ::: in addition to ```
    # See: https://myst-parser.readthedocs.io/en/latest/syntax/optional.html#code-fences-using-colons
    "colon_fence",
    # Enable definition list syntax.
    # See: https://myst-parser.readthedocs.io/en/latest/syntax/optional.html#definition-lists
    "deflist",
]

# For supporting links to headers like:
# [](#auto-generated-header-anchors)
# See: https://myst-parser.readthedocs.io/en/latest/syntax/optional.html#auto-generated-header-anchors
myst_heading_anchors = 3

# For numbered figures. Sphinx feature.
# Ref: https://www.sphinx-doc.org/en/master/usage/configuration.html#confval-numfig
# Enables {numref} role in MyST.
# Ref2: https://jupyterbook.org/en/stable/content/figures.html#numbered-references
numfig = True

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns: list[str] = []

html_static_path = ["_static"]
html_css_files = ["wakepy-docs.css"]
html_logo = "img/logo-small.svg"

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "sphinx_book_theme"
html_title = f"wakepy {__version__}"
html_theme_options = {
    "repository_url": "https://github.com/wakepy/wakepy",
    "use_repository_button": True,
    "use_download_button": False,
    "use_fullscreen_button": False,
    # Shows the landing page in the sidebar
    # See: https://sphinx-book-theme.readthedocs.io/en/stable/sections/sidebar-primary.html#add-the-home-page-to-your-table-of-contents
    "home_page_in_toc": True,
    "pygment_light_style": "friendly",
    "pygment_dark_style": "lightbulb",
}

# Whether to create a Sphinx table of contents for the lists of class methods
# and attributes. If a table of contents is made, Sphinx expects each entry to
# have a separate page. True by default.
numpydoc_class_members_toctree = False
# Removes the unnecessary automatically generated Attributes and Methods
# listings (duplicate info).
numpydoc_show_class_members = False

# This is a fix for https://github.com/wakepy/wakepy/issues/448
autodoc_mock_imports = []
try:
    from wakepy import JeepneyDBusAdapter  # noqa: F401
except ImportError:
    autodoc_mock_imports.append("wakepy.dbus_adapters.jeepney")


def setup(app: Sphinx) -> None:
    app.add_js_file("wakepy-docs.js", loading_method="defer")
