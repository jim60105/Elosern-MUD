"""Browser acceptance test package marker.

Makes ``web.tests.browser`` discoverable as a package by both the Evennia test
runner (``evennia test --settings settings.py web``) and the explicit browser
entry point (``python -m unittest discover -s web/tests/browser -t .``).
"""
