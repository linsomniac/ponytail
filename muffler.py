#!/usr/bin/env python3

import time
import os
from typing import Union


class Tail:
    class FileState:
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

    def __init__(self, filename: str) -> None:
        self.filename = filename
        self.state = Tail.FileState(filename)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return

    def _has_file_rotated(
        self, new_state: FileState, old_state: Union[FileState, None]
    ) -> bool:
        if not new_state.file_exists:
            return True

        if old_state is None:
            return False

        if new_state.dev_no != old_state.dev_no:
            return True
        if new_state.inode_no != old_state.inode_no:
            return True

        return False

    def readlines(self):
        old_file = None
        old_state = None
        file = None

        while True:
            if old_file:
                while True:
                    line = old_file.readline()
                    if not line:
                        break
                    yield line

            state = Tail.FileState(self.filename)

            if not file and not state.file_exists:
                time.sleep(1)
                continue

            if not file:
                file = open(self.filename, "r")

            current_pos = file.tell()

            if self._has_file_rotated(state, old_state):
                if old_file:
                    old_file.close()
                old_file = file
                old_state = None
                file = None
                print("File rotated")
                continue

            if state.size is not None and state.size < current_pos:
                print("File restarted")
                file.seek(0)

            old_state = state
            del state

            while True:
                line = file.readline()
                if not line:
                    time.sleep(1)
                    break
                yield line


if __name__ == '__main__':
    import sys

    with Tail("/tmp/tailtest") as t:
        for line in t.readlines():
            print(f"Got line: {line.strip()}")
            sys.stdout.flush()