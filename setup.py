import setuptools

from setuptools import find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

with open("requirements.txt", "r") as fh:
    requirements = fh.read().splitlines()

with open("digital_thought_commons/version", "r") as fh:
    version_info = fh.read()

setuptools.setup(
    name="digital_thought_commons",
    version=version_info,
    author="Digital Thought",
    author_email="development@digital-thought.org",
    description="My standard python libs for doing things",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Digital-Thought/commons",
    install_requires=requirements,
    classifiers=[
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "License :: OSI Approved :: GNU Affero General Public License v3",
        "Operating System :: OS Independent",
        "Development Status :: 4 - Beta"
    ],
    packages=find_packages(exclude=('tests', 'docs', 'sampleConfigs')),
    python_requires='>=3.8',
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'ip_enrichment = digital_thought_commons.enrichers:main',
        ],
    }
)
