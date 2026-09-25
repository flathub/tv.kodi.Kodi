#!/usr/bin/env bash
#
# Post-install: write AppStream metainfo for a packaged Kodi addon from its
# addon.xml. Usage: gen-addon-metainfo.sh <addon_id>

set -e

addon="${1:?addon id required}"
dest="${FLATPAK_DEST:?FLATPAK_DEST not set}"
addon_xml="${dest}/lib/kodi/addons/${addon}/addon.xml"

# AppStream ids: no segment may start with a digit
cid="tv.kodi.Kodi.Addon.$(echo "${addon}" | sed -E 's/\.([0-9])/._\1/g')"

x() { xmllint --xpath "string(${1})" "${addon_xml}" 2>/dev/null || true; }
esc() { sed -e 's/&/\&amp;/g' -e 's/</\&lt;/g' -e 's/>/\&gt;/g'; }

meta='//extension[@point="xbmc.addon.metadata"]'

name=$(x "/addon/@name")
provider=$(x "/addon/@provider-name")
source=$(x "${meta}/source")
license=$(x "${meta}/license")
summary=$(x "${meta}/summary[@lang='en_GB']")
[ -n "${summary}" ] || summary=$(x "${meta}/summary[@lang='en_US']")
[ -n "${summary}" ] || summary=$(x "(${meta}/summary)[1]")
[ -n "${summary}" ] || summary="${name}"
# AppStream forbids URLs in <summary>
summary=$(printf '%s' "${summary}" | sed -E 's#https?://[^[:space:]]+##g; s/[[:space:]]+/ /g; s/^[[:space:]]+//; s/[[:space:]]*[.,;:-]*[[:space:]]*$//')
[ -n "${summary}" ] || summary="${name}"

# libretro/libretro-super#2116
case "${addon}:${license}" in
    game.libretro.lrps2:GPL) license="GPL-3.0-or-later" ;;
esac

# addon.xml license strings -> SPDX; custom ones become LicenseRef-*
case "${license}" in
    GPLv2|GPLv2+|GPL2|"GPL v2.0"|"GNU General Public License. Version 2, June 1991")
        license="GPL-2.0-or-later" ;;
    GPLv3|GPL3)
        license="GPL-3.0-or-later" ;;
    LGPLv2.1|LGPLv2.1+|LGPL-2.1)
        license="LGPL-2.1-or-later" ;;
    MPLv2.0|MPL2)
        license="MPL-2.0" ;;
    "Artistic License")
        license="Artistic-2.0" ;;
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
    GPL-2.0-only|GPL-2.0-or-later|GPL-3.0-only|GPL-3.0-or-later|LGPL-2.1-or-later|MIT|MPL-2.0|Zlib|BSD-3-Clause|Apache-2.0)
        ;;
    *)
        echo "gen-addon-metainfo: ${addon}: unknown license '${license}'; add an SPDX mapping" >&2
        exit 1 ;;
esac

# homepage must be a web URL; pin upstreams that declare none (TODO: fix upstream)
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
