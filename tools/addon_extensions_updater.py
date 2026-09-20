#!/usr/bin/env python3
#
# Wire the addon modules listed in the manifest as flatpak extensions: set
# PACKAGE_ZIP + install prefix in each <id>.json, add the metainfo post-install,
# and regenerate the manifest tail from add-extensions: to EOF.

import json
import os
import re

MANIFEST = "../tv.kodi.Kodi.yml"
PREFIX = "-DCMAKE_INSTALL_PREFIX=/app/lib/kodi/addons"
GEN = "../../tools/gen-addon-metainfo.sh"

# non-addon extensions, emitted first
EXTRA_EXTENSIONS = """\
  tv.kodi.Kodi.bdj:
    directory: share/kodi/extra/bdj
    bundle: true
    autodelete: true
    no-autodownload: true
"""
EXTRA_CLEANUP = ["  - mkdir -p ${FLATPAK_DEST}/share/kodi/extra\n"]

# opt-in (no-autodownload) cores are parked on branch extensions-opt-in-addons
OPT_IN = ()


def extension_id(addon):
    # flatpak ids: no segment may start with a digit
    return "tv.kodi.Kodi.Addon." + re.sub(r"\.([0-9])", r"._\1", addon)


def no_autodownload(addon):
    return "true" if addon in OPT_IN else "false"


def module_ids(manifest_text):
    """Addon modules referenced by the manifest."""
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
    """Flatpak has no per-arch extensions; such modules stay in the base app."""
    with open(module_path(module)) as f:
        data = json.load(f)
    return any(
        k in data for k in ("only_arches", "only-arches", "skip_arches", "skip-arches")
    )


def wire_addon_json(module, ids):
    """Idempotently add PACKAGE_ZIP/prefix opts, the metainfo source and post-installs."""
    with open(module_path(module)) as f:
        data = json.load(f)

    config_opts = data.setdefault("config-opts", [])
    config_opts[:] = [
        o for o in config_opts if o == PREFIX or not o.startswith("-DCMAKE_INSTALL_PREFIX=")
    ]
    for opt in ("-DPACKAGE_ZIP=ON", PREFIX, "-DCMAKE_PREFIX_PATH=/app"):
        if opt not in config_opts:
            config_opts.append(opt)

    sources = data.setdefault("sources", [])
    if not any(s.get("type") == "file" and s.get("path") == GEN for s in sources):
        sources.append({"type": "file", "path": GEN})

    # $FLATPAK_BUILDER_BUILDDIR is the source root even for builddir: true
    post = data.setdefault("post-install", [])
    for aid in ids:
        cmd = f"bash $FLATPAK_BUILDER_BUILDDIR/gen-addon-metainfo.sh {aid}"
        if cmd not in post:
            post.append(cmd)

    with open(module_path(module), "w") as f:
        f.write(json.dumps(data, indent=4))
        f.write("\n")


def render_extensions(ext_ids):
    lines = ["add-extensions:\n", EXTRA_EXTENSIONS]
    for addon in ext_ids:
        lines += [
            f"  {extension_id(addon)}:\n",
            f'    directory: lib/kodi/addons/{addon}\n',
            "    bundle: true\n",
            "    autodelete: true\n",
            f"    no-autodownload: {no_autodownload(addon)}\n",
        ]
    lines += [
        "cleanup-commands:\n",
        *EXTRA_CLEANUP,
        "  - mkdir -p ${FLATPAK_DEST}/lib/kodi/addons\n",
    ]
    return "".join(lines)


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    with open(MANIFEST) as f:
        manifest = f.read()

    ext_ids = []
    for module in module_ids(manifest):
        if is_arch_restricted(module):
            continue
        ids = provided_ids(module)
        wire_addon_json(module, ids)
        ext_ids.extend(ids)
    ext_ids = sorted(set(ext_ids))

    # generated tail: add-extensions: to EOF
    head = manifest.split("\nadd-extensions:", 1)[0].rstrip("\n") + "\n"
    with open(MANIFEST, "w") as f:
        f.write(head)
        f.write(render_extensions(ext_ids))


if __name__ == "__main__":
    main()
