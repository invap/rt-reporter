# Copyright (c) 2024 Fundacion Sadosky, info@fundacionsadosky.org.ar
# Copyright (c) 2024 INVAP, open@invap.com.ar
# SPDX-License-Identifier: AGPL-3.0-or-later OR Fundacion-Sadosky-Commercial

import subprocess
import sys
import threading
from pynput import keyboard

from src.communication_channel_conf import CommunicationChannelConf
from src.reporter_communication_channel import ReporterCommunicationChannel

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
    # Building argument map
    if len(sys.argv) != 2:
        print("Erroneous number of arguments.", file=sys.stderr)
        exit(-1)
    try:
        open(sys.argv[1], "r")
    except FileNotFoundError:
        print("File not found.", file=sys.stderr)
        exit(-2)
    decoded_choice = sys.argv[1].rsplit("/", 1)
    files_path = decoded_choice[0]
    process_name = decoded_choice[0] + "/" + decoded_choice[1]
    # Creates the thread for the communication channel.
    acquirer = ReporterCommunicationChannel(
        files_path, process_name
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


if __name__ == "__main__":
    main()
