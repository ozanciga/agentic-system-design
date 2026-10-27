"""Chapter order and lesson numbering. Lesson content lives in content/chNN_*.py."""

import importlib
import sys

sys.dont_write_bytecode = True

MODULES = [
    "ch01_bounded_task",
    "ch02_runtime",
    "ch03_tools",
    "ch04_composition",
    "ch05_recovery",
    "ch06_retrieval",
    "ch07_evaluation",
    "ch08_memory",
    "ch09_specialists",
    "ch10_performance",
    "ch11_operations",
    "ch12_case_studies",
    "ch13_platform",
]

# Old lesson slugs that were merged into another lesson keep working as redirects.
ALIASES = {
    "validate-tool-arguments": "design-tool-contracts",
    "apply-privacy-and-residency": "keep-secrets-out-and-data-in-scope",
    "resolve-memory-write-conflicts": "gate-memory-writes",
}

CHAPTERS = []
LESSONS = []
for chapter, name in enumerate(MODULES, 1):
    module = importlib.import_module(f"content.{name}")
    CHAPTERS.append(module.CHAPTER)
    for item in module.LESSONS:
        LESSONS.append(dict(number=len(LESSONS) + 1, chapter=chapter, **item))
