PROJECT ?= tv.kodi.Kodi

.PHONY: build build-i386 flatpak install run clean

update-addons:
	cd tools && python3 addon_updater.py -r
build:
	flatpak-builder build-dir $(PROJECT).yml --repo=repo --force-clean --ccache 2>&1 | tee -a build.log
build-i386:
	flatpak-builder build-dir $(PROJECT).yml --repo=repo --force-clean --ccache --arch=i386 2>&1 | tee -a build-i386.log
flatpak:
	flatpak build-bundle repo $(PROJECT).flatpak $(PROJECT)
install:
	flatpak install local $(PROJECT)
run:
	flatpak update -y $(PROJECT)
	flatpak run $(PROJECT)
clean:
	rm -rf .flatpak-builder/cache
