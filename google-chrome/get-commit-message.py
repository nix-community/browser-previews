#!/usr/bin/env python3

# This script prints the Git commit message for stable channel updates.
# Usage: ./get-commit-message.py [version]

# Based on
# https://github.com/NixOS/nixpkgs/blob/92559b7330a56778dde383225bae47e225de4861/pkgs/applications/networking/browsers/chromium/get-commit-message.py

import re
import sys
import textwrap

from collections import OrderedDict

import feedparser
import requests
from builtins import len, list, print


releasesBlogFeed = 'https://chromereleases.googleblog.com/feeds/posts/default'


def stderr(s):
    sys.stderr.write(f'{s}\n')


stderr(f'Fetching feed from <{releasesBlogFeed}>...')
feed = feedparser.parse(releasesBlogFeed)
stderr(f'fetched {len(feed.entries)} articles.')
html_tags = re.compile(r'<[^>]+>')
target_version = sys.argv[1] if len(sys.argv) == 2 else None

stderr(f'Looking for posts mentioning target version "{target_version}"...')

for entry in feed.entries:
    stderr(f'\nChecking entry link <{entry.link}>...')
    url = requests.get(entry.link).url.split('?')[0]
    if entry.title != 'Stable Channel Update for Desktop':
        if target_version and entry.title == '':
            # Workaround for a special case (Chrome Releases bug?):
            if 'the-stable-channel-has-been-updated-to' not in url:
                stderr('Not the "blank title" special case; skipping.')
                continue
        else:
            stderr('Not "Stable Channel Update for Desktop"; skipping.')
            continue
    content = entry.content[0].value
    content = html_tags.sub('', content)  # Remove any HTML tags
    if re.search(r'Linux', content) is None:
        stderr('No mention of Linux; skipping.')
        continue
    # print(url)  # For debugging purposes
    version = re.search(r'\d+(\.\d+){3}', content).group(0)
    if target_version:
        if version != target_version:
            stderr(f'Entry version "{version} does not match target; skipping." ')
            continue
    else:
        print('chromium: TODO -> ' + version + '\n')
    print(url)
    if fixes := re.search(r'This update includes .+ security fix(es)?\.', content):
        fixes = fixes.group(0)
        if zero_days := re.search(r'Google is aware( of reports)? th(e|at) .+ in the wild\.', content):
            fixes += " " + zero_days.group(0)
        print('\n' + '\n'.join(textwrap.wrap(fixes, width=72)))
    if cve_list := re.findall(r'CVE-[^: ]+', content):
        cve_list = list(OrderedDict.fromkeys(cve_list))  # Remove duplicates but preserve the order
        cve_string = ' '.join(cve_list)
        print("\nCVEs:\n" + '\n'.join(textwrap.wrap(cve_string, width=72)))
    sys.exit(0)  # We only care about the most recent stable channel update

stderr("Error: No match.")
sys.exit(1)
