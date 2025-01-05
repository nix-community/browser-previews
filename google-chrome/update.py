#! /usr/bin/env python3

# Based on
# https://github.com/NixOS/nixpkgs/blob/59719f787e94f39e64e9086d08eaedd8a9e61b22/pkgs/applications/networking/browsers/chromium/update.py

"""This script automatically updates google-chrome via upstream-info.nix."""
# Usage: ./update.py [--commit]

import base64
import json
import re
import subprocess
import sys

from collections import OrderedDict

from builtins import iter, len, open, print, sorted
from looseversion import LooseVersion
from os.path import abspath, dirname
from urllib.request import urlopen

RELEASES_URL = 'https://versionhistory.googleapis.com/v1/chrome/platforms/linux/channels/all/versions/all/releases'
DEB_URL = 'https://dl.google.com/linux/chrome/deb/pool/main/g'

PIN_PATH = dirname(abspath(__file__)) + '/upstream-info.nix'
COMMIT_MESSAGE_SCRIPT = dirname(abspath(__file__)) + '/get-commit-message.py'
NIXPKGS_PATH = subprocess.check_output(["git", "rev-parse", "--show-toplevel"], cwd=dirname(PIN_PATH)).strip()


def load_as_json(path):
    """Loads the given nix file as JSON."""
    out = subprocess.check_output(['nix-instantiate', '--eval', '--strict', '--json', path])
    return json.loads(out)


def save_dict_as_nix(path, dict_input):
    """Saves the given dict/JSON as nix file."""
    json_string = json.dumps(dict_input)
    nix = subprocess.check_output(
        ['nix-instantiate', '--eval', '--expr', '{ json }: builtins.fromJSON json', '--argstr', 'json', json_string])
    formatted = subprocess.check_output(['nixfmt'], input=nix)
    with open(path, 'w') as out:
        out.write(formatted.decode())


def prefetch_src_sri_hash(attr_path, version):
    """Prefetches the fixed-output-derivation source tarball and returns its SRI-Hash."""
    print(f'nix-build (FOD prefetch) {attr_path} {version}')
    out = subprocess.run(
        ["nix-build", "--expr",
         f'(import ./. {{}}).{attr_path}.browser.passthru.recompressTarball {{ version = "{version}"; }}'],
        cwd=NIXPKGS_PATH,
        stderr=subprocess.PIPE
    ).stderr.decode()

    for line in iter(out.split("\n")):
        match = re.match(r"\s+got:\s+(.+)$", line)
        if match:
            print(f'Hash: {match.group(1)}')
            return match.group(1)
    print(f'{out}\n\nError: Expected hash in nix-build stderr output.', file=sys.stderr)
    sys.exit(1)


def nix_prefetch_url(url, algo='sha256'):
    """Prefetches the content of the given URL."""
    print(f'nix store prefetch-file {url}')
    out = subprocess.check_output(['nix', 'store', 'prefetch-file', '--json', '--hash-type', algo, url])
    return json.loads(out)['hash']


def nix_prefetch_git(url, rev):
    """Prefetches the requested Git revision of the given repository URL."""
    print(f'nix-prefetch-git {url} {rev}')
    out = subprocess.check_output(['nix-prefetch-git', '--quiet', '--url', url, '--rev', rev])
    return json.loads(out)


def get_file_revision(revision, file_path):
    """Fetches the requested Git revision of the given Chromium file."""
    url = f'https://chromium.googlesource.com/chromium/src/+/refs/tags/{revision}/{file_path}?format=TEXT'
    with urlopen(url) as http_response:
        response = http_response.read()
        return base64.b64decode(response)


def get_chromedriver(cd_channel):
    """Get the latest chromedriver builds given a channel"""
    # See https://chromedriver.chromium.org/downloads/version-selection#h.4wiyvw42q63v
    chromedriver_versions_url = \
        f'https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json'
    print(f'GET {chromedriver_versions_url}')
    with urlopen(chromedriver_versions_url) as http_response:
        chromedrivers = json.load(http_response)
        cd_channel = chromedrivers['channels'][cd_channel]
        downloads = cd_channel['downloads']['chromedriver']

        def get_chromedriver_url(platform):
            for download in downloads:
                if download['platform'] == platform:
                    return download['url']

        return {
            'version': cd_channel['version'],
            'hash_linux': nix_prefetch_url(get_chromedriver_url('linux64')),
            'hash_darwin': nix_prefetch_url(get_chromedriver_url('mac-x64')),
            'hash_darwin_aarch64': nix_prefetch_url(get_chromedriver_url('mac-arm64'))
        }


def channel_name_to_attr_name(channel_name):
    if channel_name == 'stable':
        return 'chrome'
    if channel_name == 'beta':
        return 'chromeBeta'
    if channel_name == 'dev':
        return 'chromeDev'
    print(f'Error: Unexpected channel: {channel_name}', file=sys.stderr)
    sys.exit(1)


def get_channel_key(item):
    """Orders Chromium channels by their name."""
    channel_name = item[0]
    if channel_name == 'stable':
        return 0
    if channel_name == 'beta':
        return 1
    if channel_name == 'dev':
        return 2
    if channel_name == 'ungoogled-chromium':
        return 3
    print(f'Error: Unexpected channel: {channel_name}', file=sys.stderr)
    sys.exit(1)


def print_updates(channels_old, channels_new):
    """Print a summary of the updates."""
    print('Updates:')
    for channel_name in channels_old:
        version_old = channels_old[channel_name]["version"]
        version_new = channels_new[channel_name]["version"]
        if LooseVersion(version_old) < LooseVersion(version_new):
            attr_name = channel_name_to_attr_name(channel_name)
            print(f'- {attr_name}: {version_old} -> {version_new}')


def main():
    channels = {}
    last_channels = load_as_json(PIN_PATH)

    print(f'GET {RELEASES_URL}', file=sys.stderr)
    with urlopen(RELEASES_URL) as resp:
        releases = json.load(resp)['releases']

        for release in releases:
            channel_name = re.findall("chrome/platforms/linux/channels/(.*)/versions/", release['name'])[0]

            # If we've already found a newer release for this channel, we're
            # no longer interested in it.
            if channel_name in channels:
                continue

            # We only look for channels that are listed in our version pin file.
            if channel_name not in last_channels:
                continue

            # If we're back at the last release we used, we don't need to
            # keep going -- there's no new version available, and we can
            # just reuse the info from last time.
            if release['version'] == last_channels[channel_name]['version']:
                channels[channel_name] = last_channels[channel_name]
                continue

            channel = {'version': release['version']}
            if channel_name == 'dev':
                google_chrome_suffix = 'unstable'
            elif channel_name == 'ungoogled-chromium':
                google_chrome_suffix = 'stable'
            else:
                google_chrome_suffix = channel_name

            try:
                # channel['hash'] = prefetch_src_sri_hash(
                #     channel_name_to_attr_name(channel_name),
                #     release["version"]
                # )
                channel['hash_deb_amd64'] = nix_prefetch_url(
                    f'{DEB_URL}/google-chrome-{google_chrome_suffix}/' +
                    f'google-chrome-{google_chrome_suffix}_{release["version"]}-1_amd64.deb')
            except subprocess.CalledProcessError:
                # This release isn't actually available yet.  Continue to
                # the next one.
                print(
                    f'Release not available yet: google-chrome-{google_chrome_suffix}_{release["version"]}-1_amd64.deb'
                )
                continue

            if channel_name == 'stable':
                channel['chromedriver'] = get_chromedriver('Stable')

            channels[channel_name] = channel

    sorted_channels = OrderedDict(sorted(channels.items(), key=get_channel_key))
    if len(sys.argv) == 2 and sys.argv[1] == '--commit':
        for channel_name in sorted_channels.keys():
            version_old = last_channels[channel_name]['version']
            version_new = sorted_channels[channel_name]['version']
            print(f'Creating commits for {channel_name} using "Old" version ({version_old}) and "New" version ({version_new})...')
            if LooseVersion(version_old) < LooseVersion(version_new):
                last_channels[channel_name] = sorted_channels[channel_name]
                save_dict_as_nix(PIN_PATH, last_channels)
                attr_name = channel_name_to_attr_name(channel_name)
                commit_message = f'{attr_name}: {version_old} -> {version_new}'
                if channel_name == 'stable':
                    body = subprocess.check_output([COMMIT_MESSAGE_SCRIPT, version_new]).decode('utf-8')
                    commit_message += '\n\n' + body
                # `JSON_PATH`?
                subprocess.run(['git', 'add', PIN_PATH], check=True)
                subprocess.run(['git', 'commit', '--file=-'], input=commit_message.encode(), check=True)
    else:
        save_dict_as_nix(PIN_PATH, sorted_channels)
        print_updates(last_channels, sorted_channels)


main()
