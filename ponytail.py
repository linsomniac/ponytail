#!/usr/bin/env python3

"""Python "tail -F" like functionality, targeted for processing log data,
with a goal of being reliable and robust.

Written by Sean Reifschneider, May 2022
"""

import time
import os
from typing import Union, Generator


class Follow:
    """Create an object to follow a file.

    Features:
        - Detects if file is truncated and starts over at the beginning.
        - Detects file rename and new file created (for log rotation).
        - Continues reading old file after rotation to catch stragglers written there.
        - Can write an optional "offset" file so it can pick up from where it left off.

    f = Follow('/var/log/syslog')
    for line in f.readlines():
        print(line.rstrip())
    """

    class FileState:
        """Internal class for representing the state of a file."""

        def __init__(self, filename: str) -> None:
            self.dev_no = None
            self.inode_no = None
            self.size = None
            try:
                stat = os.stat(filename)
                self.file_exists = True
                self.dev_no = stat.st_dev
                self.inode_no = stat.st_ino
                self.size = stat.st_size
            except FileNotFoundError:
                self.file_exists = False

    def __init__(self, filename: str, watch_rotated_file_seconds: int = 300) -> None:
        """File watcher.

        Args:
            filename: Filename to watch.
            watch_rotated_file_seconds: After detecting the file has been rotated,
                    watch the old file for this many seconds to see if new data
                    has been written to it after the rotation.
        """
        self.filename = filename
        self.watch_rotated_file_seconds = watch_rotated_file_seconds

    def _has_file_rotated(
        self, new_state: FileState, old_state: Union[FileState, None]
    ) -> bool:
        """INTERNAL: Detect if file has been rotated.

        Args:
            new_state: Current file state.
            old_state: None or the previous state of the file.

        Returns:
            True if it believes the file has been rotated, False otherwise.
        """
        if not new_state.file_exists:
            return True

        if old_state is None:
            return False

        if new_state.dev_no != old_state.dev_no:
            return True
        if new_state.inode_no != old_state.inode_no:
            return True

        return False


    def readlines(
        self, none_on_no_data: bool = False
    ) -> Generator[Union[str, None], None, None]:
        """Returns lines in the file.  When reaching EOF, it will wait for more
        data to be written, so this will never terminate.

        Args:
            none_on_no_data: If true, instead of sleeping and continuing,
                    it will return None if data is not ready.

        Returns: Yields strings representing the lines in the file, or None as
                described with "none_on_no_data".
        """
        old_file = None
        close_old_file_after = 0
        old_state = None
        file = None

        while True:
            if old_file:
                while True:
                    line = old_file.readline()
                    if not line:
                        break
                    yield line

                if time.time() > close_old_file_after:
                    close_old_file_after = 0
                    old_file.close()
                    old_file = None

            state = Follow.FileState(self.filename)

            if not file and not state.file_exists:
                if none_on_no_data:
                    yield None
                else:
                    time.sleep(1)
                continue

            if not file:
                file = open(self.filename, "r")

            current_pos = file.tell()

            if self._has_file_rotated(state, old_state):
                if old_file:
                    old_file.close()
                old_file = file
                close_old_file_after = time.time() + self.watch_rotated_file_seconds
                old_state = None
                file = None
                continue

            if state.size is not None and state.size < current_pos:
                file.seek(0)

            old_state = state
            del state

            while True:
                line = file.readline()
                if not line:
                    if none_on_no_data:
                        yield None
                    else:
                        time.sleep(1)
                    break
                yield line
