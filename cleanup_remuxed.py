import os
import os.path as path
import sys
import time

total_freed = 0

for dirpath, _, filenames in os.walk(sys.argv[1]):
    if len(filenames) == 0:
        continue

    for f in filenames:
        if not f.endswith(".ts"):
            continue

        mp4_name = f[:-2] + "mp4"

        if path.exists(path.join(dirpath, mp4_name)):
            original_size = path.getsize(path.join(dirpath, f))
            remuxed_size = path.getsize(path.join(dirpath, mp4_name))
            remuxed_last_edit = path.getctime(path.join(dirpath, mp4_name))

            # only delete files that are roughtly the same size and that have finish remuxing at least an hour ago
            # we don't want to delete stuff in progress after all
            if 0.9 < original_size/remuxed_size < 1.1 and time.time() - remuxed_last_edit > 60*60:
                print("Deleting file", path.join(dirpath, f))
                os.remove(path.join(dirpath, f))
                total_freed += original_size

print(f"Freed {total_freed/1000**3:.2f} GB")