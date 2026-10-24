#!/usr/bin/env python3
# Usage: gen_dev_manifest.py <manifest> <allowlist> <output> [addon-id...]

import os
import re
import sys

ENTRY = re.compile(r"  - addons/([^/]+)/\1\.json$")
EXT_HEADER = re.compile(r"  [^ #]")
EXT_DIR = re.compile(r"    directory: lib/kodi/addons/(\S+)$")


def read_allowlist(path):
    with open(path) as f:
        return {line.split("#", 1)[0].strip() for line in f} - {""}


def provided_ids(base, module):
    p = os.path.join(base, "addons", module, "provides.txt")
    if os.path.isfile(p):
        with open(p) as f:
            return {line.strip() for line in f if line.strip()}
    return {module}


def ext_kept(block, provided):
    for line in block:
        m = EXT_DIR.match(line.rstrip("\r\n"))
        if m:
            return m.group(1) in provided
    return True


def main(manifest, allowlist, output, *extra):
    # newline="" keeps every kept line byte-identical
    with open(manifest, newline="") as f:
        lines = f.readlines()

    modules = {m.group(1) for line in lines if (m := ENTRY.match(line.rstrip("\r\n")))}
    keep = read_allowlist(allowlist) | set(extra)
    unknown = keep - modules
    if unknown:
        sys.exit(f"not in {manifest}: {' '.join(sorted(unknown))}")
    base = os.path.dirname(manifest)
    provided = set().union(*(provided_ids(base, m) for m in keep))

    res, block, section = [], [], None

    def flush():
        if block and ext_kept(block, provided):
            res.extend(block)
        block.clear()

    for line in lines:
        text = line.rstrip("\r\n")
        if text[:1] not in ("", " ", "#"):
            section = text.split(":", 1)[0]
        if section == "add-extensions":
            if EXT_HEADER.match(text):
                flush()
                block.append(line)
                continue
            if block and text.startswith("    "):
                block.append(line)
                continue
        flush()
        m = ENTRY.match(text)
        if section == "modules" and m and m.group(1) not in keep:
            continue
        res.append(line)
    flush()

    with open(output, "w", newline="") as f:
        f.writelines(res)
    print(f"{output}: {len(keep)} of {len(modules)} addon modules")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        sys.exit(f"usage: {sys.argv[0]} <manifest> <allowlist> <output> [addon-id...]")
    main(*sys.argv[1:])
