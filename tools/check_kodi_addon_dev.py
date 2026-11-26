#!/usr/bin/env python3
# Usage: check_kodi_addon_dev.py <manifest>
# kodi-addon-dev configures Kodi for the addons before Kodi is built, so it needs
# Kodi's patches up to the last one that touches the addon headers or cmake setup.

import os
import re
import sys

MODULE = re.compile(r"  [^\s#]")
# what the kodi-addon-dev component installs, and what configure reads
DEVKIT = (
    "xbmc/addons/kodi-dev-kit/",
    "xbmc/addons/AddonBindings.cmake",
    "cmake/",
    "CMakeLists.txt",
    "version.txt",
    "tools/depends/target/",
)
FILE_LISTS = ("cmake/installdata/", "cmake/treedata/")


def module(lines, name):
    start = lines.index(f"  - name: {name}")
    end = next((i for i in range(start + 1, len(lines)) if MODULE.match(lines[i])), len(lines))
    return lines[start:end]


def patches(manifest, block):
    # patch sources, each with its option lines
    out = []
    for i, line in enumerate(block):
        if line.strip() != "- type: patch":
            continue
        source = [line]
        for opt in block[i + 1 :]:
            if not opt.startswith("        "):
                break
            source.append(opt)
        if any(o.strip().startswith(("paths:", "strip-components:", "options:")) for o in source):
            sys.exit(f"{manifest}: kodi patch with paths, strip-components or options, extend {sys.argv[0]}")
        out.append(source)
    return out


def patched(text):
    # paths in a patch, with the a/, b/ or other first component removed
    for line in text.splitlines():
        if line.startswith("diff --git "):
            names = line[11:].split(" ")
        elif line.startswith(("--- ", "+++ ")):
            names = [line[4:].split("\t")[0]]
        elif line.startswith(("rename from ", "rename to ", "copy from ", "copy to ")):
            yield line.split(" ", 2)[2].strip().strip('"')
            continue
        else:
            continue
        for name in names:
            name = name.strip().strip('"')
            if name != "/dev/null" and "/" in name:
                yield name.split("/", 1)[1]


def touches_devkit(manifest, source):
    path = next(o.split(":", 1)[1].strip() for o in source if o.strip().startswith("path:"))
    with open(os.path.join(os.path.dirname(manifest), path), errors="replace") as f:
        return any(p.startswith(DEVKIT) and not p.startswith(FILE_LISTS) for p in patched(f.read()))


def main(manifest):
    with open(manifest) as f:
        lines = f.read().split("\n")
    kodi = patches(manifest, module(lines, "kodi"))
    dev = patches(manifest, module(lines, "kodi-addon-dev"))
    last = max((i + 1 for i, s in enumerate(kodi) if touches_devkit(manifest, s)), default=0)
    if dev != kodi[:last]:
        want = "none" if not last else "\n".join(l for s in kodi[:last] for l in s)
        sys.exit(f"{manifest}: kodi-addon-dev needs these patches of kodi's:\n{want}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(f"usage: {sys.argv[0]} <manifest>")
    main(sys.argv[1])
