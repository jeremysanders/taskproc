#   Copyright 2016 Jeremy Sanders
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#############################################################################

try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup

def main():
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

if __name__ == '__main__':
    main()
