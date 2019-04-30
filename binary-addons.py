#!/usr/bin/env python3

import sys
import os
from glob import glob
import json
import subprocess
import threading


ADDON_SRC_PREFIX = 'src'


def addon_manifest(def_dir, addon):
    with open(os.path.join(def_dir, addon + '.txt'), 'r') as f:
        a, r, v = f.read().strip().split(' ')
        if not os.path.exists(addon):
            subprocess.check_output(['git', 'clone', '--branch={}'.format(v), '--single-branch', r])
        else:
            subprocess.check_output(['git', 'config', 'remote.origin.fetch', '+refs/heads/{v}:refs/remotes/origin/{v}'.format(v=v)], cwd=a)
        subprocess.check_output(['git', 'fetch', '--all', '-p'], cwd=a)
        t = subprocess.check_output(['git', 'describe', '--abbrev=0', '--tags', 'origin/{}'.format(v)], cwd=a)
        t = t.decode().strip()
        c = subprocess.check_output(['git', 'rev-parse', t], cwd=a)
        c = c.decode().strip()
        mf = {
            'name': addon,
            'buildsystem': 'cmake-ninja',
            'sources': [{
                'type': 'git',
                'url': r,
                'tag': t,
                'commit': c,
            }]
        }
        return mf


def write_manifest(addon_dir, target_path):
    addon_dict = addon_manifest(addon_dir, os.path.basename(addon_dir))
    with open(os.path.join(target_path, "%s.json" % os.path.basename(addon_dir)), 'w') as t:
        json.dump(addon_dict, t, indent=4)
        t.write('\n')


def create_manifest(repo_path, target_path):
    threads = []
    for p in glob(os.path.join(repo_path, '*', 'platforms.txt')):

        addon_dir = os.path.abspath(os.path.join(p, os.pardir))
        with open(p) as platforms_file:
            platforms = platforms_file.read().strip()
            platforms = platforms.split(" ")

            if set(platforms).intersection(["!linux"]):
                print("{} skipped ({})".format(os.path.basename(addon_dir), ', '.join(platforms)))
                continue
            elif not set(platforms).intersection(["all", "linux"]) and not all([p.startswith("!") for p in platforms]):
                print("{} skipped ({})".format(os.path.basename(addon_dir), ', '.join(platforms)))
                continue

        # print some progress
        print(os.path.basename(addon_dir))

        t = threading.Thread(target=write_manifest, args=(addon_dir, target_path))
        t.start()
        threads.append(t)

    [t.join() for t in threads]


if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise ValueError('invalid arguments')
    create_manifest(
        repo_path = sys.argv[1],
        target_path = sys.argv[2]
    )
