#!/usr/bin/env bash
#
# Generate a flatpak AppStream metainfo component for a Kodi binary addon.
#
# Run as a post-install step inside the addon build sandbox, after the packaged
# addon has been relocated to $FLATPAK_DEST/lib/kodi/addons/<id>. Reads that
# addon's addon.xml and writes
#   $FLATPAK_DEST/share/metainfo/tv.kodi.Kodi.Addon.<id>.metainfo.xml
# where <id> has any digit-leading segment underscore-prefixed (AppStream/
# flatpak component ids may not have a segment starting with a digit).
#
# Usage: gen-addon-metainfo.sh <addon_id>

set -e

addon="${1:?addon id required}"
dest="${FLATPAK_DEST:?FLATPAK_DEST not set}"
addon_xml="${dest}/lib/kodi/addons/${addon}/addon.xml"

# component id: prefix "_" to any dot-separated segment starting with a digit
cid="tv.kodi.Kodi.Addon.$(echo "${addon}" | sed -E 's/\.([0-9])/._\1/g')"

# xpath string extraction from addon.xml
x() { xmllint --xpath "string(${1})" "${addon_xml}" 2>/dev/null || true; }
# xml-escape text content (&, <, >)
esc() { sed -e 's/&/\&amp;/g' -e 's/</\&lt;/g' -e 's/>/\&gt;/g'; }

meta='//extension[@point="xbmc.addon.metadata"]'

name=$(x "/addon/@name")
provider=$(x "/addon/@provider-name")
source=$(x "${meta}/source")
license=$(x "${meta}/license")
# a few addons ship a LICENSE file but omit <license> from addon.xml; pin the
# SPDX id from the addon's own LICENSE here (only when the tag is absent, so an
# upstream <license> still wins if one is added later).
case "${addon}" in
    pvr.freebox)        license="${license:-MIT}" ;;              # MIT License
    pvr.sledovanitv.cz) license="${license:-GPL-2.0-or-later}" ;; # GPLv2, "or later" in src/Addon.h
esac
# prefer an English summary, fall back to any summary, then to the name
summary=$(x "${meta}/summary[@lang='en_GB']")
[ -n "${summary}" ] || summary=$(x "${meta}/summary[@lang='en_US']")
[ -n "${summary}" ] || summary=$(x "(${meta}/summary)[1]")
[ -n "${summary}" ] || summary="${name}"
# AppStream forbids URLs in <summary>; strip any and tidy leftover whitespace
# and trailing punctuation (also avoids an unwanted trailing "." in the summary)
summary=$(printf '%s' "${summary}" | sed -E 's#https?://[^[:space:]]+##g; s/[[:space:]]+/ /g; s/^[[:space:]]+//; s/[[:space:]]*[.,;:-]*[[:space:]]*$//')
[ -n "${summary}" ] || summary="${name}"

# map the license strings addon.xml emits to SPDX ids/expressions; already-valid
# SPDX ids (GPL-2.0-or-later, GPL-2.0-only, MIT, Zlib, ...) fall through unchanged.
# custom/non-SPDX licenses become LicenseRef-* so the metainfo stays valid.
case "${license}" in
    GPLv2|GPLv2+|GPL2|"GPL v2.0"|"GNU General Public License. Version 2, June 1991")
        license="GPL-2.0-or-later" ;;
    GPLv3|GPL3)
        license="GPL-3.0-or-later" ;;
    LGPLv2.1|LGPLv2.1+|LGPL-2.1)
        license="LGPL-2.1-or-later" ;;
    zlib)
        license="Zlib" ;;
    "Zlib|GPLv2")
        license="Zlib OR GPL-2.0-or-later" ;;
    "GPL-2.0-or-later, GPL-3.0-or-later, Apache-2.0")
        license="GPL-2.0-or-later AND GPL-3.0-or-later AND Apache-2.0" ;;
    "CC BY-SA 4.0, GNU GENERAL PUBLIC LICENSE Version 2.0")
        license="CC-BY-SA-4.0 AND GPL-2.0-or-later" ;;
    MAME)
        license="LicenseRef-MAME" ;;
    "MAME Noncommercial")
        license="LicenseRef-MAME-Noncommercial" ;;
    "Non-commercial")
        license="LicenseRef-Non-commercial" ;;
    "Public Domain")
        license="LicenseRef-public-domain" ;;
    BSD)
        license="LicenseRef-BSD" ;;
    "")
        echo "gen-addon-metainfo: ${addon}: addon.xml declares no <license>; refusing to guess" >&2
        exit 1 ;;
esac

# homepage url: prefer <source>, then <website>. AppStream requires a real web
# URL for the homepage, so when the addon declares neither (or a non-http value)
# pin the upstream repo here. TODO: send PRs adding <source> to these upstreams,
# then drop the matching entries below. https://kodi.tv/ is the last resort.
homepage="${source}"
[ -n "${homepage}" ] || homepage=$(x "${meta}/website")
case "${homepage}" in
    http://*|https://*) ;;
    *)
        case "${addon}" in
            pvr.argustv)           homepage="https://github.com/kodi-pvr/pvr.argustv" ;;
            pvr.freebox)           homepage="https://github.com/aassif/pvr.freebox" ;;
            pvr.sledovanitv.cz)    homepage="https://github.com/palinek/pvr.sledovanitv.cz" ;;
            screensaver.asterwave) homepage="https://github.com/xbmc/screensaver.asterwave" ;;
            screensaver.greynetic) homepage="https://github.com/xbmc/screensaver.greynetic" ;;
            screensaver.rsxs.*)    homepage="https://github.com/xbmc/screensavers.rsxs" ;;
            *)                     homepage="https://kodi.tv/" ;;
        esac
        ;;
esac

name_esc=$(printf '%s' "${name}" | esc)
provider_esc=$(printf '%s' "${provider}" | esc)
summary_esc=$(printf '%s' "${summary}" | esc)
homepage_esc=$(printf '%s' "${homepage}" | esc)
license_esc=$(printf '%s' "${license}" | esc)

install -dm755 "${dest}/share/metainfo"
cat >"${dest}/share/metainfo/${cid}.metainfo.xml" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<component type="addon">
  <id>${cid}</id>
  <extends>tv.kodi.Kodi</extends>
  <name>Kodi: ${name_esc}</name>
  <summary>${summary_esc}</summary>
  <description><p>${summary_esc}</p><p>${name_esc} is a binary add-on for Kodi.</p></description>
  <url type="homepage">${homepage_esc}</url>
  <developer id="tv.kodi"><name>${provider_esc}</name></developer>
  <metadata_license>FSFAP</metadata_license>
  <project_license>${license_esc}</project_license>
</component>
EOF
