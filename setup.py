from setuptools import setup, find_packages


def read_requirements(file):
    with open(file, "r") as f:
        return f.read().splitlines()


setup(
    name="rt-reporter",
    version="0.1.0",
    author="Carlos Gustavo Lopez Pombo",
    author_email="clpombo@gmail.com",
    description="An implementation of an instrumentation-based runtime event reporter.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/invap/rt-reporter/",
    packages=find_packages(),
    install_requires=read_requirements("./requirements/running_requirements.txt")
    + read_requirements("requirements/development_only_requirements.txt"),
    classifiers=[
        "Development status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: GNU Affero General Public License v3 or later",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.12",
)
