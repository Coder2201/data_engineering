# Always prefer setuptools over distutils
from setuptools import setup, find_packages

# To use a consistent encoding
from codecs import open
from os import path

# The directory containing this file
HERE = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(HERE, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

# This call to setup() does all the work
setup(
    name="polygon-data-generator",
    version="0.1.16",
    description="Demo library for polygon data",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://medium-multiply.readthedocs.io/",
    author="Trishita Singh",
    author_email="ts4376@nyu.edu",
    license="MIT",
    packages=["polygon_data_generator"],
    include_package_data=True,
    install_requires=["datetime","polygon-api-client","sqlalchemy"]
)