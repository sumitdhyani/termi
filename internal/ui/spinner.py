import sys
import threading
import time


FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]


def start_spinner(text: str) -> callable:
    """
    Start a terminal spinner with the given text.
    Returns a stop function that clears the spinner when called.
    """
    stop_event = threading.Event()
    line_len = len(text) + 4  # spinner + space + buffer

    def spin():
        i = 0
        while not stop_event.is_set():
            frame = FRAMES[i % len(FRAMES)]
            sys.stdout.write(f"\r{frame} {text}")
            sys.stdout.flush()
            i += 1
            time.sleep(0.08)

    thread = threading.Thread(target=spin, daemon=True)
    thread.start()

    def stop():
        stop_event.set()
        thread.join()
        # Hard clear line
        sys.stdout.write("\r" + " " * line_len + "\r")
        sys.stdout.flush()

    return stop
