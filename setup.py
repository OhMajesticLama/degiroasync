"""
setup file for degiroasync
"""
import sys
import os

import setuptools


# pyproject.toml top
"""
[project]
dependencies = [
    'httpx >= 0.21.3'
]

[project.optional-dependencies]
tests = [
	'nose2 >= 0.10.0',
    'mypy >= 0.931'
]
"""

def forbid_publish():
    argv = sys.argv
    blacklist = ['register', 'upload']

    for command in blacklist:
        if command in argv:
            print(f'Command "{command}" has been blacklisted, exiting...')
            sys.exit(2)


if __name__ == '__main__':
    forbid_publish()  # Not ready for publish
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    with open(readme_path, "r") as fh:
        long_description = fh.read()

    setuptools.setup(
        name="degiroasync",
        version="0.3",
        author_email="ohmajesticlama@gmail.com",
        description="A Python asynchronous library for Degiro trading service.",
        long_description=long_description,
        #url="https://github.com/pypa/sampleproject",
        #scripts=[],
        packages=setuptools.find_packages(),
        install_requires=[
            'httpx >= 0.21.3'
            ],
        extra_requires={
            'dev': [
                'nose2 >= 0.10.0',
                'mypy >= 0.931',
                'coverage >= 6.3'
                'build >= 0.7.0'
                ]
            },
        classifiers=[
            "Programming Language :: Python :: 3",
            "License :: OSI Approved :: MIT License",
            "Operating System :: OS Independent",
        ],
        test_suite='nose2.collector',
        tests_require=['nose2']
    )

