"""Internal sd-webui worker boundary and store-path confinement tests.

Package split of the original flat module; each slice module groups the
shipped classes by concern (the store-isolation suite, the output-format
pipeline, the gallery worker path, and the cutout stage/failure suites).
The fake clients, the opaque PNG fixture and the store-isolation base live
in ``_support`` (not a collected test module).
"""
