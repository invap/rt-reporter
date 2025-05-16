# Copyright (c) 2024 Fundacion Sadosky, info@fundacionsadosky.org.ar
# Copyright (c) 2024 INVAP, open@invap.com.ar
# SPDX-License-Identifier: AGPL-3.0-or-later OR Fundacion-Sadosky-Commercial
import argparse
import os
import sys
import threading
from pathlib import Path

from pynput import keyboard

from rt_reporter.communication_channel import CommunicationChannel

# Stop event for finishing the reporting process
stop_event = threading.Event()


def on_press(key):
    global stop_event
    try:
        # Check if the key has a `char` attribute (printable key)
        if key.char == "s":
            stop_event.set()
    except AttributeError:
        # Handle special keys (like ctrl, alt, etc.) here if needed
        pass


def _run_acquisition(process_thread):
    global stop_event
    # Start the listener in a separate thread
    listener = keyboard.Listener(on_press=on_press)
    listener.start()
    # Configure the monitor by setting up control event.
    process_thread.set_event(stop_event)
    # Events setup for managing the running mode.
    stop_event.clear()
    # Starts the acquisition thread.
    process_thread.start()
    # Waiting for the verification process to finish, either naturally or manually.
    process_thread.join()
    listener.stop()


def main():
    # Argument processing
    parser = argparse.ArgumentParser(
        prog="The Runtime Reporter",
        description="Reports events of a software artifact to be used by The Runtime Monitor.",
        epilog="Example: python -m rt_reporter.rt_reporter_sh path/to/sut --event_report path/to/output.csv --timeout 5"
    )
    parser.add_argument(
        "sut",
        type=str,
        help="Path to the executable binary."
    )
    parser.add_argument(
        "event_report",
        type=str,
        nargs="?",
        help="Path to the output event report, in csv format."
    )
    parser.add_argument(
        "-t", "--timeout",
        type=int,
        nargs="?",
        help="Timeout for the acquisition process in seconds."
    )
    # Parse arguments
    args = parser.parse_args()
    input_path = Path(args.sut)
    valid, message = validate_input_path(input_path)
    if not valid:
        print(f"Executable binary file error. {message}", file=sys.stderr)
        exit(-1)
    if args.event_report is not None:
        output_path = Path(args.event_report)
        valid, message = validate_output_path(output_path)
        if not valid:
            print(f"Event report file error. {message}", file=sys.stderr)
            exit(-2)
        else:
            if output_path.is_file():
                directory = str(output_path.parent)
                filename_without_extension = output_path.stem
                extension = output_path.suffix
                if extension != ".csv" or extension != "":
                    extension = ".csv"
            else:
                directory = str(output_path.parent)
                filename_without_extension = input_path.name
                extension = ".csv"
    else:
        directory = str(input_path.parent)
        filename_without_extension = input_path.name
        extension = ".csv"
    if args.timeout is None:
        timeout = 0
    else:
        timeout = args.timeout
    sut_file_path = str(input_path)
    output_file_path = directory+"/"+filename_without_extension+extension
    print(sut_file_path)
    print(output_file_path)

    # Creates the thread for the communication channel.
    acquirer = CommunicationChannel(
        output_file_path, sut_file_path, timeout
    )
    # Create a new thread to read from the pipe
    process_thread = threading.Thread(
        target=_run_acquisition,
        args=[acquirer]
    )
    # Starts the monitor thread
    process_thread.start()
    # Waiting for the verification process to finish, either naturally or manually.
    process_thread.join()


def validate_input_path(path):
    try:
        path.resolve()  # Normalize and validate
    except (OSError, RuntimeError):
        return False, "Invalid path syntax or characters."
    # Check existence
    if not path.exists():
        return False, "Path does not exist."
    # Check if it's a file
    if not path.is_file():
        return False, "Path is not a file."
    # Check read permission
    if not os.access(path, os.R_OK):
        return False, "No read permission."
    return True, "Path is valid."


def validate_output_path(path):
    try:
        path.resolve()  # Normalize and validate
    except (OSError, RuntimeError):
        return False, "Invalid path syntax or characters."
    # Check existence
    if not path.exists():
        return False, "Path does not exist."
    # Check read permission
    if not os.access(path, os.R_OK):
        return False, "No read permission."
    return True, "Path is valid."


if __name__ == "__main__":
    main()
