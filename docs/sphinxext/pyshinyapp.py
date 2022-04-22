"""Sphinx extensions for running python code and/or Shiny apps in the browser via WASM
Usage::
    .. shinyapp::
        :width: 100%
        :height: 500px

   .. shinyeditor::
        :width: 100%
        :height: 500px

    .. cell::
        :width: 100%
        :height: 500px

    .. terminal::
        :width: 100%
        :height: 500px
"""

import os
from os.path import dirname, join, abspath
import shutil

from docutils.nodes import SkipNode, Element
from docutils.parsers.rst import directives
from sphinx.application import Sphinx
from sphinx.util.docutils import SphinxDirective
from htmltools import css

# Local path to the shinylive/ directory (currently provided by rstudio/prism-experiments)
# This is only needed for the "self-contained" version of the API reference.
# (in other words, you can set this to "" if you already have the shinylive/ directory
# in your repo, just make sure to also point SHINYLIVE_DEST to the right place)
shinylive_src = abspath(join(dirname(__file__), "../../../prism-experiments/shinylive"))
SHINYLIVE_SRC = os.getenv("SHINYLIVE_SRC", shinylive_src)

# The location of the shinylive/ directory (relative to the output/root directory)
SHINYLIVE_BASE_URL = os.getenv("SHINYLIVE_BASE_URL", "/")
SHINYLIVE_DEST = os.getenv("SHINYLIVE_DEST", "shinylive")

# Since we may want to configure the location of the shinylive directory,
# write a _templates/layout.html with the relevant extrahead content
# See https://rstudio.github.io/prism-experiments/embedded-app.html
# and https://rstudio.github.io/prism-experiments/guide/site/components.html
# for more/update details
LAYOUT_TEMPLATE = f"""
<!-- Do not manually edit this file. It is automatically generated by the pyshinyapp extension -->
{{% extends "!layout.html" %}}
{{% block extrahead %}}
  <script type="module">
    const serviceWorkerPath = "{join(SHINYLIVE_BASE_URL, dirname(SHINYLIVE_DEST), 'serviceworker.js')}";
    // Start the service worker as soon as possible, to maximize the
    // resources it will be able to cache on the first run.
    if ("serviceWorker" in navigator) {{
      navigator.serviceWorker
        .register(serviceWorkerPath)
        .then(() => console.log("Service Worker registered"))
        .catch(() => console.log("Service Worker registration failed"));
      navigator.serviceWorker.ready.then(() => {{
        if (!navigator.serviceWorker.controller) {{
          // For Shift+Reload case; navigator.serviceWorker.controller will
          // never appear until a regular (not Shift+Reload) page load.
          window.location.reload();
        }}
      }});
    }}
  </script>
  <link rel="stylesheet" href="{join(SHINYLIVE_BASE_URL, SHINYLIVE_DEST, 'Components/App.css')}" type="text/css">
  <script src="{join(SHINYLIVE_BASE_URL, SHINYLIVE_DEST, 'run-python-blocks.js')}" type="module"></script>
{{% endblock %}}
"""

layout_template = join(
    dirname(dirname(__file__)),
    "source/_templates/layout.html",
)

with open(layout_template, "w") as f:
    f.write(LAYOUT_TEMPLATE)


class ShinyElement(Element):
    def html(self):
        style = css(height=self["height"], width=self["width"])
        type = self["type"]
        code = self["code"]
        if type == "shinyeditor":
            # TODO: allow the layout to be specified (right now I don't think we need
            # horizontal layout, but maybe someday we will)
            code = "#| layout: vertical\n" + code
            # the class for the editor currently is, somewhat confusingly, pyshiny
            type = "shiny"

        return f'<pre class="py{type}" style="{style}"><code>{code}</code></pre>'


def _run(self: SphinxDirective, type: str):
    code = "\n".join(self.content)
    width = self.options.pop("width", "100%")
    height = self.options.pop("height", None)

    return [ShinyElement(type=type, code=code, height=height, width=width)]


class BaseDirective(SphinxDirective):
    has_content = True
    required_arguments = 0
    option_spec = {
        "width": directives.unchanged,
        "height": directives.unchanged,
    }


class ShinyAppDirective(BaseDirective):
    def run(self):
        return _run(self, "shinyapp")


class ShinyEditorDirective(BaseDirective):
    def run(self):
        return _run(self, "shinyeditor")


class CellDirective(BaseDirective):
    def run(self):
        return _run(self, "cell")


class TerminalDirective(BaseDirective):
    def run(self):
        return _run(self, "terminal")


def setup(app: Sphinx):
    # After the build is finished, if necessary, copy over the necessary shinylive
    # static files the usual _static/ directory won't work given the limitations in it's
    # current design
    def after_build(app: Sphinx, error: object):
        if not SHINYLIVE_SRC:
            return
        shinylive = os.path.join(app.outdir, SHINYLIVE_DEST)
        if os.path.exists(shinylive):
            shutil.rmtree(shinylive)
        shutil.copytree(SHINYLIVE_SRC, shinylive)
        shutil.copy(
            os.path.join(SHINYLIVE_SRC, "../serviceworker.js"),
            os.path.join(app.outdir, "serviceworker.js"),
        )

    app.connect("build-finished", after_build)

    def append_element_html(self: Sphinx, node: Element):
        # Not sure why type checking doesn't work on this line
        self.body.append(node.html())  # type: ignore
        raise SkipNode

    def skip(self: Sphinx, node: Element):
        raise SkipNode

    app.add_node(
        ShinyElement,
        html=(append_element_html, None),
        latex=(skip, None),
        textinfo=(skip, None),
        text=(skip, None),
        man=(skip, None),
    )
    app.add_directive("shinyapp", ShinyAppDirective)
    app.add_directive("shinyeditor", ShinyEditorDirective)
    app.add_directive("cell", CellDirective)
    app.add_directive("terminal", TerminalDirective)

    return {"version": "0.1"}
