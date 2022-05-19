#!/usr/bin/env python3

import os
import time
from ponytail import Follow


def test_follow_rotated_file_expire(tmp_path):
    tmp_file = tmp_path / "testfile"
    tmp_file2 = tmp_path / "testfile2"

    f = Follow(tmp_file, watch_rotated_file_seconds=1)
    g = f.readlines(none_on_no_data=True) 
    assert g.__next__() is None

    fp = open(tmp_file, 'a')
    assert g.__next__() is None
    fp.write('Line 1\n')
    fp.flush()
    assert g.__next__() == 'Line 1\n'
    fp.write('Line 2\n')
    fp.flush()
    fp.write('Line 3\n')
    fp.flush()
    assert g.__next__() == 'Line 2\n'
    assert g.__next__() == 'Line 3\n'

    os.rename(tmp_file, tmp_file2)
    assert g.__next__() is None
    fp.write('Line 4\n')
    fp.flush()
    assert g.__next__() == 'Line 4\n'

    fp_new = open(tmp_file, 'a')
    assert g.__next__() is None
    fp_new.write('Line 5\n')
    fp_new.flush()
    assert g.__next__() == 'Line 5\n'
    assert g.__next__() is None

    fp.write('Line 6\n')
    fp.flush()
    fp_new.write('Line 7\n')
    fp_new.flush()
    assert g.__next__() == 'Line 6\n'
    assert g.__next__() == 'Line 7\n'
    assert g.__next__() is None

    time.sleep(2)
    assert g.__next__() is None

    fp.write('Line 8\n')
    fp.flush()
    fp_new.write('Line 9\n')
    fp_new.flush()
    assert g.__next__() == 'Line 9\n'
    assert g.__next__() is None
