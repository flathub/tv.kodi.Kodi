PROJECT ?= tv.kodi.Kodi

.PHONY: update-addons build flatpak install run clean

update-addons:
	cd tools && uv run addon_updater.py --release --zip
	cd tools && uv run addon_extensions_updater.py
	for d in addons/*/; do id=$${d#addons/}; id=$${id%/}; \
		case $$id in pvr.*) continue;; esac; \
		if [ -f "$$d/provides.txt" ]; then cat "$$d/provides.txt"; else echo "$$id"; fi; \
	done | sort -u > addon-list.txt
build:
	flatpak-builder build-dir $(PROJECT).yml --repo=repo --force-clean --ccache 2>&1 | tee -a build.log; test $${PIPESTATUS[0]} = 0
flatpak:
	flatpak build-bundle repo $(PROJECT).flatpak $(PROJECT)
install:
	flatpak install local $(PROJECT)
run:
	flatpak update -y $(PROJECT)
	flatpak run $(PROJECT)
clean:
	rm -rf .flatpak-builder/cache
