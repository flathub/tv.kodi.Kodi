#!/usr/bin/env bash

set -e

sed -i '/^add-extensions:/,$d' ../tv.kodi.Kodi.yml

ADDONS=""

for addon in ../addons/*; do
    ADDONS="${ADDONS} ${addon##*/}"
done

printf "add-extensions:\n" >>../tv.kodi.Kodi.yml
for addon in ${ADDONS}; do
    # leading numbers after separator must be prepended by _
    addon_id="tv.kodi.Kodi.Addon.$(echo ${addon} | sed 's/.\([0-9]\)/._\1/')"
    cat >>../tv.kodi.Kodi.yml <<EOF
  ${addon_id}:
    directory: "${addon}"
    add-ld-path: "."
    bundle: true
    autodelete: true
EOF
    case ${addon} in
        audio*|game.libretro|imagedecoder.*|inputstream.*|vfs.*)
            printf "    no-autodownload: false\n" >>../tv.kodi.Kodi.yml
            ;;
        *)
            printf "    no-autodownload: true\n" >>../tv.kodi.Kodi.yml
            ;;
    esac
done

printf "cleanup-commands:\n" >>../tv.kodi.Kodi.yml
printf "  - \"mkdir -pm755 \$FLATPAK_DEST/lib/kodi/addons\"\n" >>../tv.kodi.Kodi.yml
printf "  - \"mkdir -pm755 \$FLATPAK_DEST/share/kodi/addons\"\n" >>../tv.kodi.Kodi.yml
for addon in ${ADDONS}; do
    cat >>../tv.kodi.Kodi.yml <<EOF
  - "mkdir -pm755 \$FLATPAK_DEST/${addon}"
  - "ln -sf \$FLATPAK_DEST/${addon} \$FLATPAK_DEST/lib/kodi/addons/${addon}"
  - "ln -sf \$FLATPAK_DEST/${addon} \$FLATPAK_DEST/share/kodi/addons/${addon}"
EOF
done
