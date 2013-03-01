#!/usr/bin/env python

from setuptools import setup, Extension

setup(
      name="ternarytree", 
      version="0.1",
      test_suite = "nose.collector",
      author='Markon',
      setup_requires=['nose>=0.11'],
      description="TernarySearchTree implementation",
      ext_modules=[Extension("ternarytree", ["src/patricia_tree/ternarytreemodule.c"])]
)

