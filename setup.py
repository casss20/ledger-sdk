#!/usr/bin/env python
"""Setup script for citadel-sdk (fallback for older tools)."""

from setuptools import setup, find_packages

setup(
    name="citadel-sdk",
    use_scm_version=True,
    setup_requires=["setuptools_scm"],
    packages=find_packages(where="src"),
    package_dir={"": "src"},
)
