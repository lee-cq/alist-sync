from alist_sdk import AlistPath

import sys

print(sys.path)

from alist_sync.worker import Worker


w = Worker(
    transfer_type="copy",
    source_path=AlistPath(
        "http://192.168.3.10:5244/onedrive/Music/flac/凤凰传奇-黎明的光.flac"
    ),
    target_path=AlistPath("http://192.168.3.10:5244/Drive-New/test/凤凰传奇-黎明的光.flac"),
    backup_path=None,
)

w.run()
print(">>> Done")