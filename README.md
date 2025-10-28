# Kodi Flatpak

Kodi is an award-winning free and open source software media player and
entertainment hub for digital media. Available as a native application for
Android, Linux, BSD, macOS, iOS, tvOS and Windows operating systems, Kodi runs
on most common processor architectures. This repository packages it through
Flatpak.

## Building

Then build via

```
flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
flatpak remote-add --if-not-exists flathub-beta https://flathub.org/beta-repo/flathub-beta.flatpakrepo
flatpak -y uninstall tv.kodi.Kodi
flatpak -y install org.flatpak.Builder/x86_64/stable
flatpak -y install org.freedesktop.Platform/x86_64/24.08
cd
rm -rf tv.kodi.Kodi
git clone -b beta --recursive https://github.com/andykimpe1/tv.kodi.Kodi.git
cd tv.kodi.Kodi
flatpak run org.flatpak.Builder build-dir --user --ccache --force-clean --install tv.kodi.Kodi.yml
```

Then you can run it via the command line:

```
flatpak run tv.kodi.Kodi
```

or just search for the installed app on your system

The following binary addons do not compile, and are excluded:

- `audiodecoder.dumb`
- `game.libretro.2048`

## Contributing

The list of binary addons in each branch of Kodi may be found
[here](https://github.com/xbmc/repo-binary-addons/), and dependencies
[here](https://github.com/xbmc/xbmc/tree/master/tools/depends/target). Kodi
releases are found [here](https://github.com/xbmc/xbmc/releases).

Please use `uv` to run the included scripts.

You need to have the `PyGithub` and `dotenv` Python module installed, to run the update script:

```sh
uv venv
uv pip install dotenv
uv pip install PyGithub
```

`make update-addons` can help updating existing addons and also list missing ones. It will need a `GITHUB_TOKEN` environment variable set to a valid GitHub token. You can do this via an `.env` file in the root of the repository or by exporting the variable in your shell.

You can contribute by updating addons, modules and the Kodi version.
