"""Automation Hub - launcher package.

Presentation (``ui_*`` modules) is kept separate from the launcher logic
(``config``, ``process_manager``, ``preferences``) so that the way child EXEs
are located and started stays small, testable and unchanged.
"""

APP_TITLE = "Automation Control Center"
APP_BRAND = "Automation Hub"
APP_TAGLINE = "Multi-application automation launcher"
REPO_SLUG = "rishu-pandeylenskart/multi-exexs"
REPO_URL = f"https://github.com/{REPO_SLUG}"
