#!/usr/bin/python3

import argparse
import glob
import json
import os.path
import pprint
import shutil
import sys
import tarfile

import requests
from dotenv import load_dotenv
from github import Auth, Github

addon_repo_base = "https://github.com/xbmc/repo-binary-addons"
addon_repo_branch = "Piers"
addon_repo_dir = "binary_addons_repo_tmp"
addon_repo_remote = "binary_addons_repo"

load_dotenv()

auth = Auth.Token(os.environ["GITHUB_TOKEN"])
g = Github(auth=auth)


def is_github_url(url: str) -> bool:
    return "github.com" in url


def _repo_name_from_url(url: str) -> str:
    repo_path = url.rstrip("/").replace(".git", "")
    return repo_path.split("/")[-2] + "/" + repo_path.split("/")[-1]


def get_current_github_rev(url: str, branch: str) -> str | None:
    """Return the HEAD commit SHA for branch in the GitHub repo at url."""
    repo_name = _repo_name_from_url(url)
    try:
        repo = g.get_repo(repo_name)
        return repo.get_branch(branch).commit.sha
    except Exception as e:
        if args.verbose:
            print(f"  could not resolve {repo_name}@{branch}: {e}")
    return None


def get_commit_date(url: str, sha: str):
    """Return the committer datetime for a commit SHA, or None if unresolved."""
    repo_name = _repo_name_from_url(url)
    try:
        repo = g.get_repo(repo_name)
        return repo.get_commit(sha).commit.committer.date
    except Exception as e:
        if args.verbose:
            print(f"  could not resolve date for {repo_name}@{sha[:12]}: {e}")
    return None


def resolve_commit(url: str, preferred_branch: str) -> str | None:
    """
    Try *preferred_branch* first; if that fails fall back to 'master' then
    'main'.  Returns the commit SHA, or None if all attempts fail.
    """
    commit = get_current_github_rev(url, preferred_branch)
    if commit:
        return commit
    for fallback in ("master", "main"):
        if preferred_branch == fallback:
            continue
        commit = get_current_github_rev(url, fallback)
        if commit:
            if args.verbose:
                print(f"  branch '{preferred_branch}' not found; used '{fallback}'")
            return commit
    return None


def commit_is_newer(url: str, current_sha: str, candidate_sha: str) -> bool:
    """
    Return True only if candidate_sha is chronologically newer than
    current_sha (by committer date).  If either date cannot be resolved the
    candidate is treated as *not* newer, so a known-good commit is retained
    rather than risk overwriting it with a stale one.
    """
    current_date = get_commit_date(url, current_sha)
    candidate_date = get_commit_date(url, candidate_sha)
    if current_date is None or candidate_date is None:
        return False
    return candidate_date > current_date


def check_platform(def_file: str) -> bool:
    platform_file = os.path.join(os.path.dirname(def_file), "platforms.txt")
    with open(platform_file, mode="r") as plat_file:
        platforms = plat_file.readline().split()
    if args.verbose:
        print(f"valid platforms for {def_file}: {platforms}")
    if ("all" in platforms or "linux" in platforms) and "!linux" not in platforms:
        return True
    return any(p.startswith("!") and p != "!linux" for p in platforms)


def get_addon_definition(def_name: str, def_file: str):
    if args.verbose:
        print("get_addon_definition from", def_file)
    if not check_platform(def_file):
        raise Exception("platform mismatch")
    with open(def_file, mode="r") as addon_def:
        a_name, a_url, a_rev = addon_def.readline().split()
        a_type = get_addon_type(a_url)
    if a_name != def_name or a_type == "unknown":
        raise Exception("addon_definition_error")
    if args.verbose:
        print(
            f"found addon details - name: {a_name}, url: {a_url}, "
            f"git_rev: {a_rev}, type: {a_type}"
        )
    if a_name and a_url and a_rev and a_type:
        return a_name, a_url, a_rev, a_type
    raise Exception("addon_definition_error")


def get_addon_type(addon_url: str) -> str:
    if addon_url.endswith((".tar.gz", ".tar.xz", ".tar.bz2", ".zip")):
        return "archive"
    if addon_url.startswith(("https://", "http://")) or addon_url.endswith(".git"):
        return "git"
    return "unknown"


def set_build_type(a_data: dict) -> dict:
    if "build-options" not in a_data:
        a_data["build-options"] = {}
    if "config-opts" not in a_data:
        a_data["config-opts"] = []
    if args.release:
        if "-DCMAKE_BUILD_TYPE=Release" not in a_data["config-opts"]:
            a_data["config-opts"].append("-DCMAKE_BUILD_TYPE=Release")
        a_data["build-options"]["no-debuginfo"] = True
        a_data["build-options"]["cflags"] = "-g0"
        a_data["build-options"]["cxxflags"] = "-g0"
        if a_data["name"] == "pvr.iptvsimple":
            a_data["build-options"]["cxxflags"] += " -Wp,-U_GLIBCXX_ASSERTIONS"
        elif a_data["name"] == "audiodecoder.dumb":
            a_data["build-options"]["cflags"] += " -fPIC"
            a_data["build-options"]["cxxflags"] += " -fPIC"
    else:
        if "-DCMAKE_BUILD_TYPE=Release" in a_data["config-opts"]:
            a_data["config-opts"].remove("-DCMAKE_BUILD_TYPE=Release")
        a_data["build-options"]["no-debuginfo"] = False
        cflags = a_data["build-options"].get("cflags", "").replace("-g0", "")
        cxxflags = a_data["build-options"].get("cxxflags", "").replace("-g0", "")
        if cflags.strip():
            a_data["build-options"]["cflags"] = cflags
        else:
            a_data["build-options"].pop("cflags", None)
        if cxxflags.strip():
            a_data["build-options"]["cxxflags"] = cxxflags
        else:
            a_data["build-options"].pop("cxxflags", None)
    return a_data


def update_addon_repo():
    if args.verbose:
        print("downloading binary addon repo")
    if os.path.isdir(addon_repo_dir):
        shutil.rmtree(addon_repo_dir)
    addon_repo_url = (
        addon_repo_base + "/archive/refs/heads/" + addon_repo_branch + ".tar.gz"
    )
    response = requests.get(addon_repo_url, stream=True)
    try:
        with tarfile.open(fileobj=response.raw, mode="r|gz") as tarball:
            tarball.extractall(addon_repo_dir)
    except tarfile.ReadError:
        print(
            f"Error downloading repository tarball {addon_repo_url}, "
            f"did you specify an existing branch from {addon_repo_base}?"
        )
        sys.exit(2)


def _apply_git_update(source: dict, url: str, branch: str) -> bool:
    """
    Resolve the latest commit for url@branch and write it into source.
    Returns True on success, False if the commit could not be resolved.
    """
    commit = resolve_commit(url, branch)
    if not commit:
        print(f"  Warning: could not resolve commit for {url}@{branch}")
        return False

    current = source.get("commit")
    if current and commit != current and not commit_is_newer(url, current, commit):
        print(
            f"  Warning: refusing to update {url} to {commit[:12]} "
            f"(resolved from '{branch}'); it is not newer than the recorded "
            f"commit {current[:12]}. Keeping existing commit."
        )
        rejected_updates[url] = (
            f"kept {current[:12]}, rejected {commit[:12]} (resolved from '{branch}')"
        )
        return False

    source["url"] = url
    source["type"] = "git"
    source["commit"] = commit
    source.pop("tag", None)
    if args.verbose:
        print(f"  → {url} @ {commit[:12]}")
    return True


def _update_module_git_sources(module: dict, fallback_branch: str) -> int:
    """
    Recursively update every git source within an inline module dict.
    String entries (paths to external JSON modules) are silently ignored.
    Returns the number of sources updated.
    """
    if not isinstance(module, dict):
        return 0
    updated = 0
    for source in module.get("sources", []):
        if source.get("type") != "git":
            continue
        url = source.get("url", "")
        if not url or not is_github_url(url):
            continue
        branch = source.get("branch", fallback_branch)
        if args.verbose:
            print(f"  module '{module.get('name', '?')}' git source: {url}@{branch}")
        if _apply_git_update(source, url, branch):
            updated += 1
    for sub in module.get("modules", []):
        updated += _update_module_git_sources(sub, fallback_branch)
    return updated


def update_addon_sources(
    addon_data: dict, main_url: str, main_rev: str, main_atype: str
) -> dict:
    """
    Update all updatable sources in addon_data:

    1. primary addon source — the first git/archive entry in
       addon_data["sources"].  URL and branch come from the binary addon repo
       definition (.txt file).

    2. all git sources inside module definitions
    """
    sources = addon_data.get("sources", [])

    # primary addon source
    primary_idx = next(
        (i for i, s in enumerate(sources) if s.get("type") in ("git", "archive")),
        None,
    )
    if primary_idx is not None:
        primary = sources[primary_idx]
        if main_atype == "git":
            if args.verbose:
                print(f"  primary source: {main_url}@{main_rev}")
            _apply_git_update(primary, main_url, main_rev)

    # module definitions
    for module in addon_data.get("modules", []):
        if isinstance(module, str):
            if args.verbose:
                print(f"  skipping external module reference: {module}")
            continue
        n = _update_module_git_sources(module, main_rev)
        if args.verbose and n:
            print(f"  updated {n} git source(s) in module '{module.get('name', '?')}'")

    return addon_data


pp = pprint.PrettyPrinter(indent=4)
parser = argparse.ArgumentParser()
parser.add_argument(
    "-u", "--update_repo", help="force updating binary addons repo", action="store_true"
)
parser.add_argument(
    "-v", "--verbose", help="enable verbose output", action="store_true"
)
parser.add_argument(
    "-b",
    "--branch",
    help="override repo branch (default: {})".format(addon_repo_branch),
)
parser.add_argument(
    "-r", "--release", help="enable release builds", action="store_true"
)
args = parser.parse_args()

if args.branch:
    addon_repo_branch = args.branch

if args.update_repo or not os.path.isdir(addon_repo_dir):
    update_addon_repo()

# find all available addons in repo
repo_file_list = glob.glob(
    addon_repo_dir + "/*-" + addon_repo_branch + "/*/*.txt", recursive=True
)
if len(repo_file_list) == 0:
    print("Warning: couldn't find any repository files, forcing repo update")
    update_addon_repo()
    repo_file_list = glob.glob(
        addon_repo_dir + "/*-" + addon_repo_branch + "/*/*.txt", recursive=True
    )

if args.verbose:
    print("{}: {}".format("addon_files", repo_file_list))

skipped_addons = dict()
missing_addons = list()
updated_addons = set()
rejected_updates = dict()

for f in repo_file_list:
    definition_file = os.path.basename(f)
    if definition_file == "platforms.txt":
        continue

    addon_id = definition_file.rsplit(".txt", maxsplit=1)[0]
    try:
        (name, url, rev, atype) = get_addon_definition(addon_id, f)
    except Exception as e:
        print(f"Error parsing addon definition in {definition_file}: {e} - skipping")
        skipped_addons[addon_id] = str(e)
        continue

    addon_json = os.path.join("../addons/", addon_id, addon_id + ".json")

    if not os.path.exists(addon_json):
        skipped_addons[addon_id] = "not found in existing flatpak addons"
        missing_addons.append(addon_id)
        continue

    print("updating", addon_id)
    updated_addons.add(addon_id)

    try:
        with open(addon_json, mode="r+") as jf:
            addon_data = json.load(jf)
            if args.verbose:
                print(addon_data)

            if addon_data["name"] != name:
                print(
                    f"  Error: skipping addon due to name mismatch: "
                    f"{name} vs {addon_data['name']}"
                )
                skipped_addons[addon_id] = (
                    f"name mismatch: {name} vs {addon_data['name']}"
                )
                continue

            addon_data = set_build_type(addon_data)
            addon_data = update_addon_sources(addon_data, url, rev, atype)

            jf.seek(0)
            jf.write(json.dumps(addon_data, indent=4))
            jf.write("\n")
            jf.truncate()
    except (json.JSONDecodeError, OSError) as e:
        print(f"  Warning: could not process {addon_json}: {e}")

addon_jsons = sorted(glob.glob(os.path.join("..", "addons", "*", "*.json")))
for json_path in addon_jsons:
    addon_id = os.path.basename(os.path.dirname(json_path))
    if addon_id in updated_addons:
        continue

    try:
        with open(json_path, "r+") as jf:
            addon_data = json.load(jf)

            sources = addon_data.get("sources", [])
            primary = next(
                (s for s in sources if s.get("type") == "git"),
                None,
            )
            if primary is None:
                continue

            url = primary.get("url", "")

            print(f"updating {addon_id}")

            addon_data = set_build_type(addon_data)
            branch = primary.get("branch", "master")
            addon_data = update_addon_sources(
                addon_data, url, branch, primary.get("type", "git")
            )

            jf.seek(0)
            jf.write(json.dumps(addon_data, indent=4))
            jf.write("\n")
            jf.truncate()
    except (json.JSONDecodeError, OSError) as e:
        print(f"  Warning: could not process {json_path}: {e}")

print("\n\n### DONE ###\nskipped addons:")
pp.pprint(skipped_addons)
print("\nmissing addons:")
pp.pprint(missing_addons)
print("\nrejected updates (resolved commit not newer than recorded):")
pp.pprint(rejected_updates)
