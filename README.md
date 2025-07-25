# The Runtime Reporter
This project contains an implementation of a Runtime Reporter (RR). The rationale behind this tool is that it captures the events reported by the software under test (SUT) along its execution and saves them in event log files (to be discussed below, in Section [Operation](#operation)), for performing runtime verification using the [Runtime Monitor](https://github.com/invap/rt-monitor/) (RM). This implementation of a reporter tool is conceived for working with programs which output the occurrence of events through appropriate instrumentation with the help of a reporter API (for example, the [C reporter API](https://github.com/invap/c-reporter-api/)).

## Structure the project
The RR project is organized as follows:
```graphql
rt-reporter/
├── rt_reporter/                            # Package folder
│   ├── communication_channel.py            # Information for configuring the communication channel
│   ├── communication_channel_conf.py       # Main module for lauching the SUT and building the event logs
│   └── rt_reporter_sh                      # Entry point of the command line interface of the RR
├── COPYING                                 # Licence of the project 
├── pyproject.toml                          # Configuration file (optional, recommended)
├── README.md                               # Read me file of the project
├── requirements.txt                        # Package requirements of the project
└── setup.py                                # Metadata and build configuration
```


## Installation
In this section we will review relevant aspects of how to setup this project, both for developing new features for the RR, and for using it in the runtime verification of other software artifacts.

### Base Python installation

1. Python v.3.12+ (https://www.python.org/)
2. PIP v.24.3.1+ (https://pip.pypa.io/en/stable/installation/)
3. Setup tools v.75.3.0+ / Poetry v.2.1.1+ (https://python-poetry.org)


### Setting up the project manually
To create a Python virtual environment, follow these steps:

1. **Open a terminal or command prompt:**
Start by opening your terminal (on MacOS or Linux) or Command Prompt/PowerShell (on Windows).

2. **Navigate to your project directory:**
If you have a specific directory for your project, navigate to it using the cd command:
```bash
cd path/to/your/project
```
3. **Create a Python virtual environment:**
Run one of the following commands, depending on your version of Python:
	- For Python 3.3 and newer:
	```bash
	python -m venv env
	```
	Replace `env` with whatever name you'd like for your environment folder (common names include venv, .venv, or env).
	- For Older Versions (Python 2):
		- You may need to install `virtualenv` first if you're using Python 2:
		```bash
		pip install virtualenv
		```
		- Then, create the virtual environment with:
		```bash
		virtualenv env
		```
4. **Activate the virtual environment:**
To activate the virtual environment, use one of the following commands based on your operating system:
	- On Mac OS and Linux:
	```bash
	source env/bin/activate
	```
	- On Windows:
	```bash
	.\env\Scripts\activate
	```
	Once activated, you’ll see the environment name in parentheses at the beginning of your command prompt.
5. **Install packages in the virtual environment:**
With the environment activated, you can now install packages using `pip`, and they’ll be isolated to this environment.
```bash
pip install package_name
```
Perform this command for each of the packages required replacing `package_name` with the name of each package in the file [`requirements.txt`](https://github.com/invap/rt-reporter/blob/main/requirements.txt) or just run:
```bash
pip install -r requirements.txt
```
**Content of [`requirements.txt`](https://github.com/invap/rt-reporter/blob/main/requirements.txt):**
- Pygments~=2.18.0
- black~=24.10.0
- certifi~=2024.8.30
- charset-normalizer~=3.4.0
- click~=8.1.7
- docutils~=0.21.2
- idna~=3.10
- importlib_metadata~=8.5.0
- jaraco.classes~=3.4.0
- jaraco.context~=6.0.1
- jaraco.functools~=4.1.0
- keyring~=25.5.0
- markdown-it-py~=3.0.0
- mdurl~=0.1.2
- more-itertools~=10.5.0
- mypy-extensions~=1.0.0
- nh3~=0.2.18
- packaging~=24.1
- pathspec~=0.12.1
- pip~=24.3.1
- pkginfo~=1.10.0
- platformdirs~=4.3.6
- pynput~=1.7.7
- pyobjc-core~=10.3.1
- pyobjc-framework-ApplicationServices~=10.3.1
- pyobjc-framework-Cocoa~=10.3.1
- pyobjc-framework-CoreText~=10.3.1
- pyobjc-framework-Quartz~=10.3.1
- readme_renderer~=44.0
- requests~=2.32.3
- requests-toolbelt~=1.0.0
- rfc3986~=2.0.0
- rich~=13.9.4
- setuptools~=75.3.0
- six~=1.16.0
- twine~=5.1.1
- urllib3~=2.2.3
- wxPython~=4.2.2
- zipp~=3.20.2
7. **Do something with RR...**
8. **Deactivate the virtual environment:**
To exit the virtual environment, simply type:
```bash
deactivate
```
Your environment will remain in the project folder for you to reactivate as needed.


### Setting up the project using Poetry
This section provide instructions for setting up the project using [Poetry](https://python-poetry.org)
1. **Install Poetry:** find instructions for your system [here](https://python-poetry.org) 
2. **Add [`pyproject.toml`](https://github.com/invap/rt-reporter/blob/main/pyproject.toml):** the content of the `pyproject.toml` file needed for setting up the project using poetry is shown below.
```toml
[tool.poetry]
name = "rt-reporter"
version = "0.1.0"
description = "This project contains an implementation of a Runtime Reporter (RR). The rationale behind this tool is that it captures the events reported by the software under test (SUT) along its execution and saves them in event log files (to be discussed below, in Section [Operation](#operation)), for performing runtime verification using the [Runtime Monitor](https://github.com/invap/rt-monitor/) (RM). This implementation of a reporter tool is conceived for working with programs which output the occurrence of events through appropriate instrumentation with the help of a reporter API (for example, the [C reporter API](https://github.com/invap/c-reporter-api/))."
authors = ["Carlos Gustavo Lopez Pombo <clpombo@gmail.com>"]
readme = "README.md"
license = "GNU AFFERO GENERAL PUBLIC LICENSE Version 3, 19 November 2007"
repository = "https://github.com/invap/rt-reporter"

[[tool.poetry.packages]]
include = "rt_reporter"
from = "./"

[tool.poetry.dependencies]
python = ">=3.12"
pygments =">=2.18.0,<2.19.0"
black =">=24.10.0,<24.11.0"
certifi =">=2024.8.30,<2024.9.0"
charset-normalizer =">=3.4.0,<3.5.0"
click =">=8.1.7,<8.2.0"
docutils =">=0.21.2,<0.22.0"
idna =">=3.10,<4.0"
importlib-metadata =">=8.5.0,<8.6.0"
jaraco-classes =">=3.4.0,<3.5.0"
jaraco-context =">=6.0.1,<6.1.0"
jaraco-functools =">=4.1.0,<4.2.0"
keyring =">=25.5.0,<25.6.0"
markdown-it-py =">=3.0.0,<3.1.0"
mdurl =">=0.1.2,<0.2.0"
more-itertools =">=10.5.0,<10.6.0"
mypy-extensions =">=1.0.0,<1.1.0"
nh3 =">=0.2.18,<0.3.0"
packaging =">=24.1,<25.0"
pathspec =">=0.12.1,<0.13.0"
pip =">=24.3.1,<24.4.0"
pkginfo =">=1.10.0,<1.11.0"
platformdirs =">=4.3.6,<4.4.0"
pynput =">=1.7.7,<1.8.0"
pyobjc-core =">=10.3.1,<10.4.0"
pyobjc-framework-applicationservices =">=10.3.1,<10.4.0"
pyobjc-framework-cocoa =">=10.3.1,<10.4.0"
pyobjc-framework-coretext =">=10.3.1,<10.4.0"
pyobjc-framework-quartz =">=10.3.1,<10.4.0"
readme-renderer =">=44.0,<45.0"
requests =">=2.32.3,<2.33.0"
requests-toolbelt =">=1.0.0,<1.1.0"
rfc3986 =">=2.0.0,<2.1.0"
rich =">=13.9.4,<13.10.0"
setuptools =">=75.3.0,<75.4.0"
six =">=1.16.0,<1.17.0"
twine =">=5.1.1,<5.2.0"
urllib3 =">=2.2.3,<2.3.0"
wxpython =">=4.2.2,<4.3.0"
zipp =">=3.20.2,<3.21.0"

[build-system]
requires = ["poetry-core>=1.0.0"]
build-backend = "poetry.core.masonry.api"
```
3. **Install the project:** To install the Python project using Poetry, navigate to the directory where the project is and run:
   ```bash	
   poetry install
   ```
3. **Activate the virtual environment**: To activate the virtual environment created by the previous command run:
   ```bash
   poetry env use [your_python_command]
   poetry env activate
   ```
this will ensure you are using the right Python virtual machine and then, activate the virtual environment.


### Using the project with docker
1. **Build the image:**
    ```bash
    docker build . -t rt-reporter-env
    ```
2. **Run the container:**
	```bash
	docker run -it -v$PWD:/home/workspace rt-reporter-env
	```
3. **Do something with RR...**


### Linting Python code (with Black)
A linter in Python is a tool that analyzes your code for potential errors, code quality issues, and stylistic inconsistencies. Linters help enforce a consistent code style and identify common programming mistakes, which can improve the readability and maintainability of your code. They’re especially useful in team environments to maintain coding standards.

Though primarily an auto-formatter, `Black` enforces a consistent code style and handles many linting issues by reformatting your code directly.

1. **Activate the virtual environment in your project directory:**
2. **Run linter (black):**
	- For correcting the code:
	```bash
	black .
	```
	- For checking but not correcting the code:
	```bash
	black . --check
	```


### Testing the implementation
Tu run the unit tests of the project use the command `python -m unittest discover -s . -t .`.

When executed, it performs Python unit tests with the `unittest` module, utilizing the `discover` feature to automatically find and execute test files.
- `python -m unittest`:
Runs the `unittest` module as a script. This is a built-in Python module used for testing. When called with `-m`, it allows you to execute tests directly from the command line.
- `discover`:
Tells `unittest` to search for test files automatically. This is useful when you have many test files, as it eliminates the need to specify each test file manually. By default, `unittest` discover will look for files that start with "test" (e.g., `test_example.py`).
- `-s .`:
The `-s` option specifies the start directory for test discovery.
Here, `.` means the current directory, so `unittest` will start looking for tests in the current directory and its subdirectories.
- `-t .`:
The `-t` option sets the top-level directory of the project.
Here, `.` also indicates the current directory. This is mainly useful when the start directory (`-s`) is different from the project's root. For simple projects, the start directory and top-level directory are often the same.

**In summary, this command tells Python’s `unittest` module to:**
Look in the current directory (`-s .`) for any test files that match the naming pattern `test*.py`.
Run all the tests it finds, starting from the current directory (`-t .`) and treating it as the top-level directory.


### Build the application as a library with poetry
To build a package from the Python project follow these steps:
Now that your configuration files are set, you can build the package using poetry running the build command in the root directory of the project:
```bash
poetry build
```
This will create two files in a new `dist` directory:
- A source distribution: [rt_reporter-0.1.0.tar.gz](https://github.com/invap/rt-reporter/blob/main/dist/rt_reporter-0.1.0.tar.gz)
- A wheel distribution: [rt_reporter-0.1.0-py3-none-any.whl](https://github.com/invap/rt-reporter/blob/main/dist/rt_reporter-0.1.0-py3-none-any.whl)


### Build the application as a library with setuptools
To build a package from the Python project follow these steps:

1. **The `setup.py` file:**
the [`setup.py`](https://github.com/invap/rt-reporter/blob/main/setup.py) file is the main configuration file for packaging in Python. See the content of the file below:
```python
from setuptools import setup, find_packages


def read_requirements(file):
    with open(file, 'r') as f:
        return f.read().splitlines()


setup(
    name="rt_reporter",
    version="0.1.0",
    author="Carlos Gustavo Lopez Pombo",
    author_email="clpombo@gmail.com",
    description="An implementation of an instrumentation-based runtime event reporter.",
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
    python_requires='>=3.12',
)
```
2. **Add `pyproject.toml` (Optional but Recommended):** 
the content of the `pyproject.toml` file for building the project using setuptools is shown below:
```toml
[build-system]
requires = ["setuptools", "wheel"]
build-backend = "setuptools.build_meta"
```
This configuration tells Python to use `setuptools` and `wheel` for building the package.
3. **Build the package:**
Now that your configuration files are set, you can build the package using setuptools and wheel.
- Install the necessary tools (if not already installed):
```bash
pip install setuptools wheel
```
- Run the build command in the root directory (where setup.py is located):
```bash
python setup.py sdist bdist_wheel
```
This will create two files in a new dist/ directory:
- A source distribution: [rt_reporter-0.1.0.tar.gz](https://github.com/invap/rt-reporter/blob/main/dist/rt_reporter-0.1.0.tar.gz)
- A wheel distribution: [rt_reporter-0.1.0-py3-none-any.whl](https://github.com/invap/rt-reporter/blob/main/dist/rt_reporter-0.1.0-py3-none-any.whl)


### Install the application as a library locally
Follow the steps below for installing the RR as a local library:
1. **Build the application as a library:**
Follow the steps in Section [Build the application as a library](#build-the-application-as-a-library)
2. **Install the package locally:** 
Use the command `pip install dist/rt_reporter-0.1.0-py3-none-any.whl`.

### Distribute the application as a library
Follow the steps below for distributing the RR as a library in PyPI:
1. **Build the application as a library:**
Follow the steps in Section [Build the application as a library](#build-the-application-as-a-library)
2. **Upload the package to PyPI:**
If you want to make your package publicly available, you can upload it to the Python Package Index (PyPI).
	- Install twine (a tool for uploading packages):
	```bash
	pip install twine
	```
	- Upload the package:
	```bash
	twine upload dist/*
	```
	This command will prompt you to enter your PyPI credentials. Once uploaded, others can install your package with `pip install your-package-name`.


## Relevant information about the implementation
The RR provides the basic functionality; once the SUT is chossen, the former runs the latter within a thread and captures its output pipe for pocessing the events and writing them in the corresponding event log files. The main log file is named `?_log.csv`, where `?` is the name of the SUT; for monitoring purposes this log file must be declared with the reference name "main" in the [event reports map file](https://github.com/invap/rt-monitor/blob/main/README.md#event-logs-map-file "Event reports map file") required by the [RM](https://github.com/invap/rt-monitor "Runtime Monitor") to execute the verification. The event log files produced by the self-loggable components receive their name from the name declared in the self-loggable component log initialization event, suffixed with `_log.csv`.

The SUT is assumed to be instrumented for ouputing a stream of predefined event types. Event types are defined as part of the reporting API; for example, in the case of the [C reporter API](https://github.com/invap/c-reporter-api/), the definition can be found in [Line 16](https://github.com/invap/c-reporter-api/blob/main/include/data_channel_defs.h#L16 "Event types") of file [`data_channel_defs.h`](https://github.com/invap/c-reporter-api/blob/main/include/data_channel_defs.h) as a C enumerated type:
```c
//classification of the different types of events
typedef enum {
	timed_event, 
	state_event, 
	process_event, 
	component_event, 
	end_of_report_event
} eventType;
```
which are naturally recognized as integers by the code fragment from [Line 78](https://github.com/invap/rt-reporter/blob/main/reporter_communication_channel.py#L78) to [Line 107](https://github.com/invap/rt-reporter/blob/main/reporter_communication_channel.py#L107) where appropriate action is taken for each type of event, according to the association {(0, `timed_event`), (1, `state_event`), (2, `process_event`), (3, `component_event`), (4, `end_of_report_event`)}. 
Each event arrives packed in a reporter package (see code fragment from [Line 17](https://github.com/invap/c-reporter-api/blob/main/include/data_channel_defs.h#L17) to [Line 21](https://github.com/invap/c-reporter-api/blob/main/include/data_channel_defs.h#L21) of file [`data_channel_defs.c`](https://github.com/invap/c-reporter-api/blob/main/include/data_channel_defs.h)) labeled with the event type they contain and timestamped.
Whenever a reporter package is unpacked by the reporter (see code fragment from [Line 64](https://github.com/invap/rt-reporter/blob/main/src/reporter_communication_channel.py#L64) to [Line 68](https://github.com/invap/rt-reporter/blob/main/src/reporter_communication_channel.py#L68) of file [`reporter_communication_channel.py`](https://github.com/invap/rt-reporter/blob/main/src/reporter_communication_channel.py)) we obtain: 1) a `[timestamp]`, 2) an event type (interpreted as an integer), and 3) an `[event]`. According to the event type obtained after unpacking the reporter package, appropriate logging actions are taken:
- case 0: records the line "[timestamp],timed_event,[event]" in file corresponding to the main event report file. `[event]` provide details of the timed event reported and has the shape `[clock action],[clock variable]` where `[clock action]` is in the set {clock_start, clock_pause, clock_resume, clock_reset} and `[clock variable]` is the name of a free clock variable occurring in any property of the structured sequential process (see Section [Syntax for writing properties](https://github.com/invap/rt-monitor/blob/main/README.md#syntax-for-writing-properties "Syntax for writing properties") for details on the language for writing properties of structured sequential processes),
- case 1: records the line "[timestamp],state_event,[event]" in file corresponding to the main event report file. `[event]` provide details of the state event reported and has the shape `variable_value_assigned,[variable name],[value]` where `[variable name]` is the name of a free state variable occurring in any property of the structured sequential process (see Section [Syntax for writing properties](https://github.com/invap/rt-monitor/blob/main/README.md#syntax-for-writing-properties "Syntax for writing properties") for details on the language for writing properties of structured sequential processes),
- case 2: records the line "[timestamp],process_event,[event]" in file corresponding to the main event report file. `[event]` provide details of the process event reported and has the shape `task_started,[name]`, `task_finished,[name]` or `checkpoint_reached,[name]`, where `[name]` is a unique identifier corresponding to a task o checkpoint, respectively, in the structured sequential process (see Section [Structured Sequential Process](https://github.com/invap/rt-monitor/blob/main/README.md#structured-sequential-process "Structured Sequential Process") for details on the language for declaring structured sequential processes),
- case 3: records the line "[timestamp],component_event,[event]" in file corresponding to the main event report file. `[event]` provide details of the component event reported and has the shape `[component name],[function name],[parameter list]`, where `[component name]` is a unique identifier corresponding to a component declared in the specification of the analysis framework (see Section [Specification language for describing the analysis framework](https://github.com/invap/rt-monitor/blob/main/README.md#specification-language-for-describing-the-analysis-framework "Specification language for describing the analysis framework") for details on the language for specifying the analysis framework), `[function name]` is the name of a function implemented by the component, and `[parameter list]` is the list of parameters required by the function `[function name]`, separated by commas, see for example the code fragment from [Line 70](https://github.com/invap/rt-monitor-example-app/blob/main/buggy%20app/main.c#L70) to [Line 76](https://github.com/invap/rt-monitor-example-app/blob/main/buggy%20app/main.c#L76) of the function [`main`](https://github.com/invap/rt-monitor-example-app/blob/main/buggy%20app/main.c#L17), in the file [`main.c`](https://github.com/invap/rt-monitor-example-app/blob/main/buggy%20app/main.c), where the invocation of function `sample` is followed by a code fragment reporting a component event:
```c
value = sample ();
// [ INSTRUMENTACION: Component event. ]
pause(&reporting_clk);
sprintf(str, "adc,sample,%d",value);
report(component_event,str);
resume(&reporting_clk);
//
```
- case 4: in this case, no line is written to any event log because the event reported is the initialization of the event log file of a self-loggable component; thus, `[event]` only contains the name of the self-loggable component so the reporter can open a file named `[event]_log.csv` for writing,
- case 5: in this case `[event]` has the shape `[component name],[component event]', thus the reporter writes the line "[timestamp],[component event]" in the event log file corresponding to `[component name]`, and
- case 6: this event type correspond to an `end_of_report_event` event and no further information is required:
- in any other case: records the line "[timestamp],invalid,[event]" in file corresponding to the main event log file.

Other reporter APIs, like the [Rust reporter API](https://github.com/invap/rust_reporter-api) provide analogous implementations.


## Usage
The command line interface for the RR is very simple, see the help output below:
```txt
> python -m rt_reporter.rt_reporter_sh --help
usage: The Runtime Reporter [--help] [--timeout [TIMEOUT]] sut [event_report]

Reports events of a software artifact to be used by The Runtime Monitor.

positional arguments:
  sut                   Path to the executable binary.
  event_report          Path to the output event report, in csv format.

options:
  --help                Show this help message and exit.
  --timeout [TIMEOUT]   Timeout for the acquisition process in seconds.
  --host [HOST ADDRESS] Sets the RabbitMQ server host IP address, localhost for default.
  --port [PORT NUMBER]  Sets the RabbitMQ server port number, 5673 for default.

Example: python -m rt_reporter.rt_reporter_sh path/to/sut --host rabbitmq.invap.com.ar --port 4242 --timeout 5
```


#### Errors
This section shows a list of errors that can be yielded by the command line interface:
- Error -1, "Erroneous number of arguments.": the command line interface expects exactly one parameter that is taken as the SUT to be reported; if it is passed zero or more than 1 parameter this error is yielded.
- Error -2: "File not found.": the command line interface expects the only parameter passed to be a file containing the SUT to be reported; if it is not present, this error is yielded.

In Mac OS the execution of the RR migth output the message "This process is not trusted! Input event monitoring will not be possible until it is added to accessibility clients.". This happens when an application attempts to monitor keyboard or mouse input without having the necessary permissions because Mac OS restricts access to certain types of input monitoring for security and privacy reasons. To solve it you need to grant accessibility permissions to the application running the program (e.g., Terminal, iTerm2, or a Python IDE). Here’s how:
1. Open System Preferences:
	- Go to **Apple menu** --> **System Preferences** --> **Security & Privacy**.
2. Go to Accessibility Settings:
	- In the **Privacy** tab, select **Accessibility** from the list on the left.
3. Add Your Application:
	- If you are running the RR from **Terminal**, **iTerm2**, or a specific **IDE** (like PyCharm or VS Code), you will need to add that application to the list of allowed applications.
	- Click the **lock icon** at the bottom left and enter your password to make changes.
	- Then, click the `+` button, navigate to the application (e.g., Terminal or Python IDE), and add it to the list.
4. Restart the Application:
	- After adding it to the Accessibility list, restart the application to apply the new permissions.
Once you’ve done this, the message should go away, and pynput should be able to detect keyboard and mouse events properly.


## License

Copyright (c) 2024 INVAP

Copyright (c) 2024 Fundacion Sadosky

This software is licensed under the Affero General Public License (AGPL) v3. If you use this software in a non-profit context, you can use the AGPL v3 license.

If you want to include this software in a paid product or service, you must negotiate a commercial license with us.

### Benefits of dual licensing:

It allows organizations to use the software for free for non-commercial purposes.

It provides a commercial option for organizations that want to include the software in a paid product or service.

It ensures that the software remains open source and available to everyone.

### Differences between the licenses:

The AGPL v3 license requires that any modifications or derivative works be released under the same license.

The commercial license does not require that modifications or derivative works be released under the same license, but it may include additional terms and conditions.

### How to access and use the licenses:

The AGPL v3 license is available for free on our website.

The commercial license can be obtained by contacting us at info@fundacionsadosky.org.ar

### How to contribute to the free open source version:

Contributions to the free version can be submitted through GitHub.
You shall sign a DCO (Developer Certificate of Origin) for each submission from all the members of your organization. The OCD will be an option during submission at GitHub.

### How to purchase the proprietary version:

The proprietary version can be purchased by contacting us at info@fundacionsadosky.org.ar


