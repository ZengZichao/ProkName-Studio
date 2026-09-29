"""ProkName Studio — the native desktop GUI for ProkName.

ProkName Studio is a separate deliverable from the ``prokname`` engine it drives:
it is distributed as its own package (``prokname-studio``, console entry point
``prokname-studio``) and depends on ``prokname`` the way any other consumer does.
Nothing here is reachable as ``prokname.studio``.

``__version__`` is the single source of truth for the Studio's own version, in
the same way ``prokname.__version__`` is for the engine: the build backend reads
this line (``[tool.hatch.version]``), ``prokname-studio --version`` reports it,
and the PyInstaller spec stamps it into the app bundle, so a released build can
never carry three different version numbers.
"""
from __future__ import annotations

__version__ = "0.1.0"

#: What this release of Studio was built against. The engine's own version is
#: read at runtime from ``prokname.__version__``; this floor is the contract the
#: views were written against (``presentation.decision``, ``storage.ProjectStore``
#: and the ``routing.route`` role spellings they render).
MIN_PROKNAME_VERSION = "0.1.0"

__all__ = ["__version__", "MIN_PROKNAME_VERSION"]
