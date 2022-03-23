"""
setup file for degiroasync
"""
import sys
import os

import setuptools


def forbid_publish():
    argv = sys.argv
    blacklist = ['register', 'upload']

    for command in blacklist:
        if command in argv:
            print(f'Command "{command}" has been blacklisted, exiting...')
            sys.exit(2)


if __name__ == '__main__':
    forbid_publish()  # Not ready for publish

    description = "A Python asynchronous library for Degiro trading service."
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    with open(readme_path, "r") as fh:
        long_description = fh.read()

    setuptools.setup(
        name="degiroasync",
        version="0.14.1",
        author_email="ohmajesticlama@gmail.com",
        description=description,
        long_description=long_description,
        long_description_content_type='text/markdown',
        url="https://github.com/OhMajesticLama/degiroasync",
        packages=setuptools.find_packages(),
        install_requires=[
            'httpx >= 0.21.3',
            'jsonloader >= 0.8.1',
            'typeguard >= 2.13.3',
            'asyncstdlib >= 3.10.3',
            'more_itertools >= 8.12.0'
            ],
        extras_require={
            'dev': [
                'pytest >= 7.0.1',
                'mypy >= 0.931',
                'coverage >= 6.3',
                'build >= 0.7.0',
                'flake8 >= 4.0.1',
                'twine >= 3.8.0',
                'sphinx >= 4.4.0',
                'ipython',
                'ipdb'
                ]
            },
        classifiers=[
            "Programming Language :: Python :: 3",
            "License :: OSI Approved :: MIT License",
            "Operating System :: OS Independent",
            "Development Status :: 3 - Alpha"
        ],
        test_suite='pytest',
        tests_require=['pytest']
    )
