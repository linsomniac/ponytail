#!/usr/bin/env python3

import os
import sys
import time

import pytest

from ponytail import Follow


def test_follow_rotated_file_expire(tmp_path):
    tmp_file = tmp_path / "testfile"
    tmp_file2 = tmp_path / "testfile2"

    f = Follow(tmp_file, watch_rotated_file_seconds=1)
    g = f.readlines(none_on_no_data=True)
    assert g.__next__() is None

    fp = open(tmp_file, "a")
    assert g.__next__() is None
    fp.write("Line 1\n")
    fp.flush()
    assert g.__next__() == "Line 1\n"
    fp.write("Line 2\n")
    fp.flush()
    fp.write("Line 3\n")
    fp.flush()
    assert g.__next__() == "Line 2\n"
    assert g.__next__() == "Line 3\n"

    os.rename(tmp_file, tmp_file2)
    assert g.__next__() is None
    fp.write("Line 4\n")
    fp.flush()
    assert g.__next__() == "Line 4\n"

    fp_new = open(tmp_file, "a")
    assert g.__next__() is None
    fp_new.write("Line 5\n")
    fp_new.flush()
    assert g.__next__() == "Line 5\n"
    assert g.__next__() is None

    fp.write("Line 6\n")
    fp.flush()
    fp_new.write("Line 7\n")
    fp_new.flush()
    assert g.__next__() == "Line 6\n"
    assert g.__next__() == "Line 7\n"
    assert g.__next__() is None

    time.sleep(2)
    assert g.__next__() is None

    fp.write("Line 8\n")
    fp.flush()
    fp.close()
    fp = fp_new
    fp.write("Line 9\n")
    fp.flush()
    assert g.__next__() == "Line 9\n"
    assert g.__next__() is None

    f = Follow(tmp_file, watch_rotated_file_seconds=1)
    g = f.readlines(none_on_no_data=True)
    assert g.__next__() == "Line 5\n"
    assert g.__next__() == "Line 7\n"
    assert g.__next__() == "Line 9\n"

    fp.truncate(0)
    fp.write("Line 10\n")
    fp.flush()
    assert g.__next__() is None
    assert g.__next__() == "Line 10\n"


def test_follow_offset_file(tmp_path):
    tmp_file = tmp_path / "testfile"
    offset_file = tmp_path / "testfile.offset"
    tmp_file2 = tmp_path / "testfile2"

    f = Follow(tmp_file, offset_filename=offset_file, watch_rotated_file_seconds=1)
    g = f.readlines(none_on_no_data=True)
    assert g.__next__() is None

    fp = open(tmp_file, "a")
    assert g.__next__() is None
    fp.write("Line 1\n")
    fp.flush()
    assert g.__next__() == "Line 1\n"
    fp.write("Line 2\n")
    fp.flush()
    fp.write("Line 3\n")
    fp.flush()
    assert g.__next__() == "Line 2\n"
    assert g.__next__() == "Line 3\n"
    f.save_offset()
    fp.flush()

    f = Follow(tmp_file, offset_filename=offset_file, watch_rotated_file_seconds=1)
    g = f.readlines(none_on_no_data=True)
    assert g.__next__() is None

    fp.write("Line 4\n")
    fp.flush()
    assert g.__next__() == "Line 4\n"
    f.save_offset()

    fp.truncate(0)
    fp.write("Line 5\n")
    fp.flush()

    f = Follow(tmp_file, offset_filename=offset_file, watch_rotated_file_seconds=1)
    g = f.readlines(none_on_no_data=True)
    assert g.__next__() == "Line 5\n"
    f.save_offset()

    os.rename(tmp_file, tmp_file2)
    fp = open(tmp_file, "a")
    fp.write("Line 6\n")
    fp.write("Line 7\n")
    fp.flush()

    f = Follow(tmp_file, offset_filename=offset_file, watch_rotated_file_seconds=1)
    g = f.readlines(none_on_no_data=True)
    assert g.__next__() == "Line 6\n"
    assert g.__next__() == "Line 7\n"


@pytest.mark.skipif(sys.platform != "win32", reason="Windows sharing semantics")
def test_follow_does_not_block_windows_log_rotation(tmp_path):
    tmp_file = tmp_path / "testfile"
    rotated_file = tmp_path / "testfile.1"
    tmp_file.write_text("Line 1\n")

    f = Follow(tmp_file, watch_rotated_file_seconds=60)
    g = f.readlines(none_on_no_data=True)

    try:
        assert g.__next__() == "Line 1\n"

        os.rename(tmp_file, rotated_file)
        with open(rotated_file, "a") as fp:
            fp.write("Line 2\n")
        tmp_file.write_text("Line 3\n")

        assert g.__next__() == "Line 2\n"
        assert g.__next__() is None
        assert g.__next__() == "Line 3\n"
    finally:
        g.close()
        if f.file:
            f.file.close()
