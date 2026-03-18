"""View package exports for the web application."""

from .home import render_home_page
from .progress import render_progress_page
from .result import render_result_page

__all__ = [
    "render_home_page",
    "render_progress_page",
    "render_result_page",
]
