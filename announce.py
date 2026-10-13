"""Posts every new GitHub Release of the owner's repositories on Discord.

announced.json keeps the tags already posted, per repository. A repository seen for the first time is only
recorded (its old releases are not posted), so adding a new script never floods the channel.
Repositories that still have their own .github/workflows/discord-release.yml are skipped (they post by themselves).
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request

env = os.environ.get
OWNER = env('OWNER')
PREFIX = env('REPO_PREFIX') or 'fks-'
STATE_FILE = 'announced.json'


def request(url, data=None, headers=None, method=None):
    req = urllib.request.Request(url, data=json.dumps(data).encode() if data is not None else None,
                                 method=method or ('POST' if data is not None else 'GET'),
                                 headers={'User-Agent': 'fks-release-bot', 'Content-Type': 'application/json', **(headers or {})})
    with urllib.request.urlopen(req) as res:
        raw = res.read()
        return json.loads(raw) if raw else {}


def github(path):
    headers = {'Accept': 'application/vnd.github+json'}
    if env('GH_TOKEN'):
        headers['Authorization'] = 'Bearer ' + env('GH_TOKEN')
    return request('https://api.github.com' + path, headers=headers)


def has_own_workflow(repo):
    try:
        github(f'/repos/{OWNER}/{repo}/contents/.github/workflows/discord-release.yml')
        return True
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False
        raise


def message(repo, release):
    tag = release['tag_name']
    version = tag[1:] if tag[:1] in ('v', 'V') else tag
    body = (release.get('body') or '').replace('\r', '').strip()

    # GitHub release notes -> Discord markdown (Discord has no ## headings inside embeds)
    body = re.sub(r'^#{1,6}\s*(.+)$', r'**\1**', body, flags=re.M)
    body = re.sub(r'^\s*[\*-]\s+', '• ', body, flags=re.M)
    body = re.sub(r'https://github\.com/([^/\s]+)/([^/\s]+)/pull/(\d+)', r'[PR #\3](https://github.com/\1/\2/pull/\3)', body)
    if len(body) > 3900:
        body = body[:3900].rsplit('\n', 1)[0] + '\n…'
    if not body:
        body = '**Full Changelog:** ' + release['html_url']

    try:
        color = int((env('COLOR') or 'F2C14E').lstrip('#'), 16)
    except ValueError:
        color = 0xF2C14E

    return {
        'content': f'# {repo} {version}\nhttps://github.com/{OWNER}/{repo}',
        'embeds': [{'title': version, 'url': release['html_url'], 'description': body, 'color': color}],
        'allowed_mentions': {'parse': []},
    }


def post(msg):
    if env('BOT_TOKEN') and env('CHANNEL_ID'):
        auth = {'Authorization': 'Bot ' + env('BOT_TOKEN')}
        api = f'https://discord.com/api/v10/channels/{env("CHANNEL_ID")}/messages'
        sent = request(api, msg, auth)
        try:  # Announcement channel: publish so following servers receive it
            request(f'{api}/{sent["id"]}/crosspost', {}, auth)
        except Exception as e:
            print('  not published to followers (not an Announcement channel?):', e)
    elif env('WEBHOOK'):
        msg['username'] = env('NAME') or 'FK Changelog'
        if env('AVATAR'):
            msg['avatar_url'] = env('AVATAR')
        request(env('WEBHOOK').rstrip('/') + '?wait=true', msg)
    else:
        sys.exit('Add the DISCORD_RELEASE_WEBHOOK secret (or DISCORD_BOT_TOKEN + DISCORD_CHANNEL_ID).')


def main():
    try:
        with open(STATE_FILE, encoding='utf-8') as f:
            state = json.load(f)
    except (FileNotFoundError, ValueError):
        state = {}

    force = (env('FORCE_REPO') or '').strip()
    repos = [r for r in github(f'/users/{OWNER}/repos?per_page=100&type=owner')
             if r['name'].startswith(PREFIX) and r['name'] != env('SELF') and not r['archived'] and not r['private']]

    for r in sorted(repos, key=lambda r: r['name']):
        name = r['name']
        releases = [x for x in github(f'/repos/{OWNER}/{name}/releases?per_page=20') if not x['draft'] and not x['prerelease']]
        tags = [x['tag_name'] for x in releases]

        if name == force and releases:
            print(f'{name}: announcing {releases[0]["tag_name"]} (manual run)')
            post(message(name, releases[0]))
            state[name] = sorted(set(state.get(name, [])) | set(tags))
            continue

        if name not in state:
            print(f'{name}: first time seen, recording {len(tags)} release(s) without posting')
            state[name] = sorted(tags)
            continue

        new = [x for x in reversed(releases) if x['tag_name'] not in state[name]]  # oldest first
        if not new:
            continue
        if has_own_workflow(name):
            print(f'{name}: has its own discord-release.yml, skipped')
            state[name] = sorted(set(state[name]) | set(tags))
            continue
        for x in new:
            print(f'{name}: announcing {x["tag_name"]}')
            post(message(name, x))
            state[name] = sorted(set(state[name]) | {x['tag_name']})

    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2, sort_keys=True)
        f.write('\n')


if __name__ == '__main__':
    main()
