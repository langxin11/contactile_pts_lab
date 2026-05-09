# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
project = "Contactile PTS Lab"
copyright = "2026, Contactile PTS Lab"
author = "Contactile PTS Lab"
version = "0.1.0"
release = "0.1.0"

# -- General configuration ---------------------------------------------------
extensions = [
    "myst_parser",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store", "manuals"]

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

language = "zh_CN"

# -- Options for HTML output -------------------------------------------------
html_theme = "furo"
html_static_path = ["_static"]

# myst-parser 配置
myst_enable_extensions = [
    "colon_fence",
    "deflist",
]
