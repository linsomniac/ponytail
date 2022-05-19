# Ponytail

## Overview

Python "tail -F" like functionality, targeted for processing log data,
with a goal of being reliable and robust.

Create an object to follow a file.

Features:
    - Detects if file is truncated and starts over at the beginning.
    - Detects file rename and new file created (for log rotation).
    - Continues reading old file after rotation to catch stragglers written there.
    - Can write an optional "offset" file so it can pick up from where it left off.

## Arguments:

Follow(filename, offset\_filename=None, watch\_rotated\_file\_seconds=300):

- filename: Filename to open and read data from.
- offset\_filename: If given, a file name to write offset information to.  This file is written either
  whenever the end of file is reached during reading, or when the "save\_offset()" method is called.  If
  you break out of the read loop (say because of Control-C), it is best to save the offset.
- watch\_rotated\_file\_seconds: After detecting the file has been rotated, watch the old file for this
  many seconds to see if new data has been written to it after the rotation.

Follow().readline(none\_on\_no\_data):

- none\_on\_no\_data: If true, instead of sleeping and continuing, it will return None if data is not ready.

Follow().save_offset()

- No arguments

## Example

```python
f = ponytail.Follow('/var/log/syslog')
for line in f.readlines():
    print(line.rstrip())
```

More exhaustive example:

```python
f = ponytail.Follow('/var/log/syslog', offset_filename='/tmp/syslog.offset', watch_rotated_file_seconds=10)
for line in f.readlines():
    print(line.rstrip())
```

The above will save the processed offset to a file, and later processing will pick up where the
previous run left off.  It will also stop watching the old file after a rotation, after 10 seconds
(default is 300).
