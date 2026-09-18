# Kodi Flatpak

Kodi is an award-winning free and open source software media player and
entertainment hub for digital media. Available as a native application for
Android, Linux, BSD, macOS, iOS, tvOS and Windows operating systems, Kodi runs
on most common processor architectures. This repository packages it through
Flatpak.

## Installing

End-user instructions, including the beta channel, the optional BD-J extension
and where Kodi keeps its data, are on the
[Kodi wiki](https://kodi.wiki/view/HOW-TO:Install_Kodi_for_Linux#Flatpak).

## Building

Install the builder, then let it pull the runtime, SDK and SDK extensions the
manifest asks for (currently `org.freedesktop.Sdk` 26.08 and the OpenJDK 17
extension used by the BD-J extension):

```
flatpak install flathub org.flatpak.Builder
flatpak run org.flatpak.Builder --install-deps-from=flathub --install-deps-only build-dir tv.kodi.Kodi.yml
```

Build into the local `repo`, then add it as a remote and install from it. The
addon extensions are pulled from the same repo automatically. The flatpak
branch follows the git branch like Flathub does, `stable` from `master` and
`beta` from any branch containing `beta`; override with `BRANCH=`:

```
make build
make install
make run
```

`make uninstall` removes the local install and remote again; the app data in
`~/.var/app` is shared with any Flathub install of Kodi and is left alone.
Builder output is appended to `build.log`. When rerunning after fixing a
failed build, pass `BUILDER_FLAGS=--disable-download` to reuse the cached
sources rather than re-check them. To test on another machine, serve `repo`
over HTTP and use that URL with `flatpak remote-add`.

## Debugging

Start Kodi on the Flatpak SDK with debug logging:

```
flatpak run --devel tv.kodi.Kodi --debug
```

`--devel` swaps the Platform runtime for the SDK, which includes tools such as
`gdb`, `strace` and `valgrind`. `--debug` turns on Kodi's debug log, written to
`~/.var/app/tv.kodi.Kodi/data/temp/kodi.log`.

Kodi ships stripped. Install the debug symbols to get useful backtraces (use
`//beta` for the beta channel):

```
flatpak install flathub tv.kodi.Kodi.Debug//stable
```

For a local build, `make debug` installs the symbols from `repo` and starts
Kodi with `--devel` and `--debug` in one step.

Attach `gdb` to the running Kodi. Get the instance ID from `flatpak ps`:

```
flatpak enter <instance-id> sh -c 'exec gdb -p $(pgrep kodi.bin)'
```

If Kodi crashes while `gdb` is available, the launcher writes a backtrace to
`~/.var/app/tv.kodi.Kodi/data/kodi_crashlog-<date>.log`.

## Debugging BD-J

The `tv.kodi.Kodi.bdj` extension ships libbluray's `bd_info`, which reports
whether BD-J was detected and whether a Java VM was found. Kodi's launcher sets
up the environment automatically, but other commands do not, so source the
extension's `env.sh` first:

```
flatpak run --command=sh tv.kodi.Kodi -c '. /app/share/kodi/extra/bdj/env.sh; bd_info /path/to/BDMV-or-iso'
```

## Maintenance

Preparing an update is a sequence of small commits, one per step, followed by
a local build and test:

```
make update-sources
make update-addons
make build && make install && make run
```

`update-sources` runs `flatpak-external-data-checker`, which edits the
manifest in place; install it once with
`flatpak install flathub org.flathub.flatpak-external-data-checker`.

`update-addons` updates the binary addons from `repo-binary-addons`, rewires
them as extensions and regenerates `addon-list.txt`. It needs a
`GITHUB_TOKEN` (exported or in `.env`) and the PyGithub and python-dotenv
modules. `uv run` uses the system Python when no `.venv` exists, so distro
packages suffice; otherwise create one:

```
uv venv
uv pip install PyGithub python-dotenv
```

Kodi itself is only bumped by the checker when a release tag appears. While
the beta branch tracks Kodi master, update the `commit:` under the
`xbmc/xbmc.git` source by hand after `update-addons`, before building.

## Contributing

The list of binary addons in each branch of Kodi may be found
[here](https://github.com/xbmc/repo-binary-addons/), and dependencies
[here](https://github.com/xbmc/xbmc/tree/master/tools/depends/target). Kodi
releases are found [here](https://github.com/xbmc/xbmc/releases).

You can contribute by updating addons, modules and the Kodi version.
