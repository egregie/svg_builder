# -*- coding: utf-8 -*-
"""Rename surviving photos to photo_NNN.jpg (CR v3.4 §2).

Order = natural by the original numeric id parsed from 'photo_<N>@...'.
New name = 'photo_' + f'{i:03d}' + '.jpg', i starting at 1.
Two-pass (temp -> final) so no rename collides with an existing source name.

Usage: python ops/scripts/rename_photos.py <folder> [--apply]
"""
import os
import re
import sys
import json

EXTS = ('.jpg', '.jpeg', '.png', '.webp')


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    folder = sys.argv[1]
    apply = '--apply' in sys.argv

    files = [f for f in os.listdir(folder)
             if f.lower().endswith(EXTS) and os.path.isfile(os.path.join(folder, f))]

    def orig_id(name):
        m = re.search(r'photo_(\d+)', name)
        return int(m.group(1)) if m else 10 ** 9

    files.sort(key=lambda n: (orig_id(n), n.lower()))

    plan = [(old, f"photo_{i:03d}.jpg") for i, old in enumerate(files, 1)]

    for old, new in plan:
        print(f"  {old:50s} -> {new}")
    print(f"\nTotal: {len(plan)} file(s).")

    os.makedirs('ops/logs', exist_ok=True)
    with open('ops/logs/rename_photos.json', 'w', encoding='utf-8') as f:
        json.dump([{'old': o, 'new': n} for o, n in plan], f,
                  ensure_ascii=False, indent=2)

    if not apply:
        print("\n[DRY-RUN] No files renamed. Re-run with --apply.")
        return

    # Pass 1: to unique temp names. Pass 2: temp -> final.
    tmp = []
    for i, (old, new) in enumerate(plan):
        t = f"__tmp_{i:03d}__.jpg"
        os.rename(os.path.join(folder, old), os.path.join(folder, t))
        tmp.append((t, new))
    for t, new in tmp:
        os.rename(os.path.join(folder, t), os.path.join(folder, new))
    print(f"\n[APPLIED] Renamed {len(plan)} file(s) to photo_NNN.jpg.")


if __name__ == '__main__':
    main()
