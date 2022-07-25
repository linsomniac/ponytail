#!/usr/bin/env python3

"""Python "tail -F" like functionality, targeted for processing log data,
with a goal of being reliable and robust.

Written by Sean Reifschneider, May 2022
"""

import time
import os
import re
from typing import Union, Generator, TextIO


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

    def __init__(
        self,
        filename: str,
        offset_filename: Union[str, None] = None,
        watch_rotated_file_seconds: int = 300,
        errors: Union[str, None] = None,
    ) -> None:
        """File watcher.

        Args:
            filename:                   Filename to watch.
            offset_filename:            If given, a file name to write offset information
                    to.  This file is written either whenever the end of file is reached
                    during reading, or when the "save_offset()" method is called.  If
                    you break out of the read loop (say because of Control-C), it is best
                    to save the offset.
            watch_rotated_file_seconds: After detecting the file has been rotated,
                    watch the old file for this many seconds to see if new data
                    has been written to it after the rotation.
            errors: As in "open()", what to do on encoding errors (default will
                    raise a UnicodeDecodeError exception, can also be "replace" or
                    "ignore".  See the Python "open()" documentation for more
                    information.
        """
        self.filename = filename
        self.watch_rotated_file_seconds = watch_rotated_file_seconds
        self.offset_filename = offset_filename
        self.file = None
        self.state = None
        self.open_errors = errors

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

    def save_offset(self) -> None:
        """Write an offset file if a filename has been given."""
        state = Follow.FileState(self.filename)
        if self.offset_filename is None:
            return
        if self.file is None:
            return
        if state is None or state.dev_no is None or state.inode_no is None:
            return

        tmp_filename = str(self.offset_filename) + ".tmp"
        with open(tmp_filename, "w") as fp:
            fp.write(
                "inode_no={} dev_no={} offset={}\n".format(
                    state.inode_no, state.dev_no, self.file.tell()
                )
            )
        os.rename(tmp_filename, self.offset_filename)

    def _load_offset(self, file: TextIO, state: FileState) -> None:
        """INTERNAL: Update the file position if there an offset file exists with a position.  This will
        detect when the file has been rotated or truncated and start over.

        Args:
            file:  File object to seek to saved offset.
            state: Current FileState object.
        """
        if self.offset_filename is None:
            return
        if not os.path.exists(self.offset_filename):
            return
        if state.inode_no is None or state.dev_no is None or state.size is None:
            return

        line = open(self.offset_filename, "r").readline()

        m = re.search(r"inode_no=(\d+) dev_no=(\d+) offset=(\d+)", line)
        if not m:
            return

        inode_no = int(m.group(1))
        dev_no = int(m.group(2))
        offset = int(m.group(3))
        if inode_no != state.inode_no or dev_no != state.dev_no or offset > state.size:
            return
        file.seek(offset)

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
        updated_since_save = False

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

            self.state = Follow.FileState(self.filename)

            if not self.file and not self.state.file_exists:
                if none_on_no_data:
                    yield None
                else:
                    time.sleep(1)
                continue

            if not self.file:
                open_kwargs = {}
                if self.open_errors:
                    open_kwargs = {"errors": self.open_errors}
                self.file = open(self.filename, "r", **open_kwargs)
                self._load_offset(self.file, self.state)

            current_pos = self.file.tell()

            if self._has_file_rotated(self.state, old_state):
                if old_file:
                    old_file.close()
                old_file = self.file
                close_old_file_after = time.time() + self.watch_rotated_file_seconds
                old_state = None
                self.file = None
                continue

            if self.state.size is not None and self.state.size < current_pos:
                self.file.seek(0)

            old_state = self.state
            self.state = None

            while True:
                line = self.file.readline()
                if not line:
                    if updated_since_save:
                        self.save_offset()
                        updated_since_save = False
                    if none_on_no_data:
                        yield None
                    else:
                        time.sleep(1)
                    break

                yield line
                updated_since_save = True
