PROJECT ?= tv.kodi.Kodi
GIT_BRANCH := $(shell git rev-parse --abbrev-ref HEAD)
BRANCH ?= $(if $(findstring beta,$(GIT_BRANCH)),beta,stable)
BUILDER_FLAGS ?=
SHELL := /bin/bash

.PHONY: update-sources update-addons addon-list build flatpak install uninstall run debug clean

update-sources:
	flatpak run --filesystem="$$PWD" org.flathub.flatpak-external-data-checker --edit-only $(PROJECT).yml
update-addons:
	cd tools && uv run addon_updater.py -r -u --zip
	cd tools && uv run addon_extensions_updater.py
	$(MAKE) addon-list
addon-list:
	for d in addons/*/; do id=$${d#addons/}; id=$${id%/}; \
		case $$id in pvr.*|inputstream.airplay) continue;; esac; \
		if [ -f "$$d/provides.txt" ]; then cat "$$d/provides.txt"; else echo "$$id"; fi; \
	done | sort -u > addon-list.txt
build:
	set -o pipefail; flatpak run org.flatpak.Builder build-dir $(PROJECT).yml --user --repo=repo --default-branch=$(BRANCH) --force-clean --ccache $(BUILDER_FLAGS) 2>&1 | tee -a build.log
flatpak:
	flatpak build-bundle repo $(PROJECT).flatpak $(PROJECT) $(BRANCH)
install:
	flatpak remote-add --user --if-not-exists --no-gpg-verify local repo
	flatpak install --user --or-update local $(PROJECT)//$(BRANCH)
uninstall:
	flatpak uninstall --user $(PROJECT)//$(BRANCH)
	flatpak remote-delete --user local
run:
	flatpak run --user $(PROJECT)//$(BRANCH)
debug:
	flatpak install --user --or-update local $(PROJECT).Debug//$(BRANCH)
	flatpak run --user --devel $(PROJECT)//$(BRANCH) --debug
clean:
	rm -rf .flatpak-builder/cache
