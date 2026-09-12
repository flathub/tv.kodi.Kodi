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

Then build via

```
flatpak run org.flatpak.Builder build-dir --user --ccache --force-clean --install tv.kodi.Kodi.yml
```

Then you can run it via the command line:

```
flatpak run tv.kodi.Kodi
```

or just search for the installed app on your system

## Debugging BD-J

The `tv.kodi.Kodi.bdj` extension ships libbluray's `bd_info`, which reports
whether BD-J was detected and whether a Java VM was found. Kodi's launcher sets
up the environment automatically, but other commands do not, so source the
extension's `env.sh` first:

```
flatpak run --command=sh tv.kodi.Kodi -c '. /app/share/kodi/extra/bdj/env.sh; bd_info /path/to/BDMV-or-iso'
```

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
