"""Worker-facing views over the approved facts, terms, playbooks and registry."""

from .faq import load_faq, search_faq
from .numbers import build_numbers
from .terms import load_terms_plain
from .updates import build_updates

__all__ = ["build_numbers", "build_updates", "load_faq", "load_terms_plain", "search_faq"]
