from setuptools import setup, find_packages


def read_requirements(file):
    with open(file, "r") as f:
        return f.read().splitlines()


setup(
    name="rt_reporter",
    version="0.1.0",
    author="Carlos Gustavo Lopez Pombo",
    author_email="clpombo@gmail.com",
    description="This project contains an implementation of a Runtime Reporter (RR). The rationale behind this tool is that it captures the events reported by the software under test (SUT) along its execution and saves them in event log files (to be discussed below, in Section [Operation](#operation)), for performing runtime verification using the [Runtime Monitor](https://github.com/invap/rt-monitor/) (RM). This implementation of a reporter tool is conceived for working with programs which output the occurrence of events through appropriate instrumentation with the help of a reporter API (for example, the [C reporter API](https://github.com/invap/c-reporter-api/)).",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/invap/rt-reporter/",
    packages=find_packages(),
    install_requires=read_requirements("./requirements.txt"),
    classifiers=[
        "Development status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: GNU Affero General Public License v3 or later",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.12",
)
