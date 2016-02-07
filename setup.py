"""A setuptools based setup module.
See:
https://packaging.python.org/en/latest/distributing.html
https://github.com/pypa/sampleproject
"""

try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup

long_description=\
"""taskproc is a simple Python module for executing a set of tasks,
using make-like dependency resolution.  The tasks are processed in
sequential order or using multiple threads."""

setup(
    name="taskproc",
    version="0.1",
    description="Process tasks with dependency resolution",
    long_description=long_description,

    # The project's main homepage.
    url="https://github.com/jeremysanders/taskproc",

    # Author details
    author="Jeremy Sanders",
    author_email="jeremy@jeremysanders.net",

    # Choose your license
    license="Apache",

    classifiers=[
        "Development Status :: 3 - Alpha",
        "Topic :: Software Development :: Build Tools",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.2",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
    ],

    # What does your project relate to?
    keywords="task processing make dependency",

    # You can just specify the packages manually here if your project is
    # simple. Or you can use find_packages().
    packages=["taskproc"],
    install_requires=[],
)
