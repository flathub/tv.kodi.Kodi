#!/usr/bin/env python3
#
# Wire every built Kodi addon as a flatpak extension.
#
# Each addon is built with -DPACKAGE_ZIP=ON and installed (via the install
# prefix override) to lib/kodi/addons/<id> (Kodi's native binary-addon path), so
# a single flatpak extension can be mounted directly at that path -- no symlinks.
# This tool:
#   1. wires each addon module's <id>.json (idempotent): PACKAGE_ZIP + install
#      prefix config-opts, the metainfo generator file source, and a post-install
#      that generates the AppStream metainfo for each addon the module installs;
#   2. regenerates the add-extensions: and cleanup-commands: blocks in the
#      manifest from the current set of addons.
#
# The addon set is taken from the manifest's module list (the addons actually
# built), NOT the addons/ directory listing. Two special cases:
#   * collections -- a module dir with a provides.txt lists the real addon ids it
#     installs (one source builds many addons, e.g. screensavers.rsxs -> 22
#     screensaver.rsxs.*). Each provided id becomes its own extension.
#   * arch-restricted modules -- flatpak has no per-arch extensions, so a module
#     whose json declares only_arches/skip_arches CANNOT be an extension; it is
#     skipped here and stays a normal base-app module on its supported arch.
#
# Fully offline; safe to run without a GITHUB_TOKEN. Run from tools/.

import json
import os
import re

MANIFEST = "../tv.kodi.Kodi.yml"
PREFIX = "-DCMAKE_INSTALL_PREFIX=/app/lib/kodi/addons"
GEN = "../../tools/gen-addon-metainfo.sh"

# non-commercial cores: license-compatible to distribute but restrict commercial
# use, so ship them disabled/opt-in rather than auto-downloaded. everything else
# is free/permissive and auto-downloads.
OPT_IN = (
    "game.libretro.mame2000",
    "game.libretro.mame2003_plus",
    "game.libretro.mame2010",
    "game.libretro.genplus",
    "game.libretro.picodrive",
)


def extension_id(addon):
    # leading digit in any dot-separated segment must be prefixed with _
    return "tv.kodi.Kodi.Addon." + re.sub(r"\.([0-9])", r"._\1", addon)


def no_autodownload(addon):
    return "true" if addon in OPT_IN else "false"


def module_ids(manifest_text):
    """Addon module ids referenced in the manifest (the built set)."""
    return sorted(set(re.findall(r"- addons/([^/]+)/[^/]+\.json", manifest_text)))


def module_path(module):
    return os.path.join("..", "addons", module, module + ".json")


def provided_ids(module):
    """Addon ids a module installs: provides.txt lines if present, else the module."""
    p = os.path.join("..", "addons", module, "provides.txt")
    if os.path.isfile(p):
        with open(p) as f:
            return [line.strip() for line in f if line.strip()]
    return [module]


def is_arch_restricted(module):
    """True if the module's json restricts arches (can't be a per-arch extension)."""
    with open(module_path(module)) as f:
        data = json.load(f)
    return any(
        k in data for k in ("only_arches", "only-arches", "skip_arches", "skip-arches")
    )


def wire_addon_json(module, ids):
    """Add PACKAGE_ZIP/prefix config-opts, the metainfo source, and per-id metainfo
    post-install commands (appended, so existing post-install -- e.g. license
    installs -- is preserved)."""
    with open(module_path(module)) as f:
        data = json.load(f)

    config_opts = data.setdefault("config-opts", [])
    # drop any stale install-prefix so PREFIX below stays authoritative
    config_opts[:] = [o for o in config_opts if not o.startswith("-DCMAKE_INSTALL_PREFIX=")]
    for opt in ("-DPACKAGE_ZIP=ON", PREFIX, "-DCMAKE_PREFIX_PATH=/app"):
        if opt not in config_opts:
            config_opts.append(opt)

    sources = data.setdefault("sources", [])
    if not any(s.get("type") == "file" and s.get("path") == GEN for s in sources):
        sources.append({"type": "file", "path": GEN})

    # $FLATPAK_BUILDER_BUILDDIR is the source root (where the file source lands)
    # regardless of cwd, so this works for builddir:true addons too.
    post = data.setdefault("post-install", [])
    for aid in ids:
        cmd = f"bash $FLATPAK_BUILDER_BUILDDIR/gen-addon-metainfo.sh {aid}"
        if cmd not in post:
            post.append(cmd)

    with open(module_path(module), "w") as f:
        f.write(json.dumps(data, indent=4))
        f.write("\n")


def render_extensions(ext_ids):
    lines = ["add-extensions:\n"]
    for addon in ext_ids:
        lines += [
            f"  {extension_id(addon)}:\n",
            f'    directory: "lib/kodi/addons/{addon}"\n',
            '    add-ld-path: "."\n',
            "    bundle: true\n",
            "    autodelete: true\n",
            f"    no-autodownload: {no_autodownload(addon)}\n",
        ]
    lines += [
        "cleanup-commands:\n",
        '  - "mkdir -pm755 $FLATPAK_DEST/lib/kodi/addons"\n',
    ]
    return "".join(lines)


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    with open(MANIFEST) as f:
        manifest = f.read()

    ext_ids = []
    for module in module_ids(manifest):
        if is_arch_restricted(module):
            # can't be a per-arch extension; stays a base-app module
            continue
        ids = provided_ids(module)
        wire_addon_json(module, ids)
        ext_ids.extend(ids)
    ext_ids = sorted(set(ext_ids))

    # everything from the add-extensions: line to EOF is generated here
    head = manifest.split("\nadd-extensions:", 1)[0].rstrip("\n") + "\n"
    with open(MANIFEST, "w") as f:
        f.write(head)
        f.write(render_extensions(ext_ids))


if __name__ == "__main__":
    main()
