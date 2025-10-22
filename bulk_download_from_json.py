#!/usr/bin/env python3
"""
Bulk Media Downloader from Grok JSON
Reads your existing JSON file and downloads all media with proper authentication
"""

import os
import json
import sys
import requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

class BulkDownloader:
    def __init__(self, session_cookie):
        self.session = requests.Session()
        self.session.cookies.set('session', session_cookie, domain='grok.com')

        # Also set cookie for assets subdomain
        self.session.cookies.set('session', session_cookie, domain='assets.grok.com')

        self.output_dir = Path('grok_downloads')
        self.stats = {'downloaded': 0, 'failed': 0, 'skipped': 0}

    def get_file_extension(self, url, mime_type=None):
        """Determine file extension from URL or MIME type"""
        if mime_type:
            if 'video' in mime_type:
                return 'mp4'
            if 'image' in mime_type:
                return 'png'

        path = urlparse(url).path
        if '.mp4' in path:
            return 'mp4'
        if '.png' in path or 'content' in path:
            return 'png'

        return 'bin'

    def download_file(self, url, filepath):
        """Download a single media file"""
        # Skip if already exists
        if filepath.exists() and filepath.stat().st_size > 0:
            return 'skipped'

        try:
            response = self.session.get(url, stream=True, timeout=30)
            response.raise_for_status()

            filepath.parent.mkdir(parents=True, exist_ok=True)

            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            return 'success'

        except Exception as e:
            print(f'  ❌ {filepath.name}: {e}')
            return 'failed'

    def load_json(self, json_path):
        """Load posts from JSON file"""
        print(f'\n📄 Loading JSON file: {json_path}')

        with open(json_path, 'r') as f:
            posts = json.load(f)

        total_children = sum(len(p.get('childPosts', [])) for p in posts)
        print(f'  ✓ Loaded {len(posts)} posts with {total_children} children')

        return posts

    def download_all(self, posts, max_workers=5):
        """Download all media files from posts"""
        print(f'\n📦 Preparing downloads...')

        # Collect all download tasks
        download_tasks = []

        for post in posts:
            user_id = post.get('userId', 'unknown')[:8]
            post_id = post.get('id', 'unknown')[:8]

            # Parent media
            if post.get('mediaUrl'):
                ext = self.get_file_extension(
                    post['mediaUrl'],
                    post.get('mimeType')
                )
                filepath = self.output_dir / user_id / post_id / f'parent.{ext}'
                download_tasks.append((post['mediaUrl'], filepath))

            # Child media
            for idx, child in enumerate(post.get('childPosts', [])):
                if child.get('mediaUrl'):
                    child_id = child.get('id', 'unknown')[:8]
                    ext = self.get_file_extension(
                        child['mediaUrl'],
                        child.get('mimeType')
                    )
                    filepath = self.output_dir / user_id / post_id / f'child_{idx:02d}_{child_id}.{ext}'
                    download_tasks.append((child['mediaUrl'], filepath))

        total_files = len(download_tasks)
        print(f'  Found {total_files} files to download')
        print(f'  Downloading with {max_workers} parallel workers...\n')

        # Download with progress
        completed = 0
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self.download_file, url, path): (url, path)
                for url, path in download_tasks
            }

            for future in as_completed(futures):
                completed += 1
                result = future.result()

                if result == 'success':
                    self.stats['downloaded'] += 1
                elif result == 'skipped':
                    self.stats['skipped'] += 1
                else:
                    self.stats['failed'] += 1

                # Show progress every 10 files or at the end
                if completed % 10 == 0 or completed == total_files:
                    print(f'  Progress: {completed}/{total_files} '
                          f'({self.stats["downloaded"]} ok, '
                          f'{self.stats["skipped"]} skipped, '
                          f'{self.stats["failed"]} failed)')

        print(f'\n✅ Downloads complete!')
        print(f'   Downloaded: {self.stats["downloaded"]} files')
        print(f'   Skipped: {self.stats["skipped"]} (already existed)')
        print(f'   Failed: {self.stats["failed"]}')
        print(f'   Output: {self.output_dir.absolute()}')


def get_session_cookie():
    """Get session cookie from user with simple instructions"""
    print('\n' + '='*70)
    print('🍪 GETTING YOUR SESSION COOKIE (One-Time Setup)')
    print('='*70)
    print('\n1. Open https://grok.com in your browser')
    print('2. Press F12 to open DevTools')
    print('3. Click "Application" tab (or "Storage" in Firefox)')
    print('4. Expand "Cookies" → click "https://grok.com"')
    print('5. Find the row with Name: "session"')
    print('6. Double-click the Value to select it')
    print('7. Copy it (Cmd+C or Ctrl+C)')
    print('\n' + '='*70 + '\n')

    cookie = input('Paste your session cookie here: ').strip()

    if not cookie:
        print('\n❌ No cookie provided. Cannot download without authentication.')
        sys.exit(1)

    return cookie


def main():
    print('='*70)
    print('📦 GROK BULK MEDIA DOWNLOADER')
    print('='*70)

    # Get JSON file
    if len(sys.argv) < 2:
        print('\n❌ Usage: python3 bulk_download_from_json.py <json_file>')
        print('\nExample:')
        print('  python3 bulk_download_from_json.py grok_43p_220c_1234567890.json')
        print('\nOr drag-and-drop your JSON file onto this script!')
        sys.exit(1)

    json_path = sys.argv[1]

    if not Path(json_path).exists():
        print(f'\n❌ File not found: {json_path}')
        sys.exit(1)

    # Get session cookie
    session_cookie = get_session_cookie()

    # Create downloader
    downloader = BulkDownloader(session_cookie)

    # Load JSON
    posts = downloader.load_json(json_path)

    # Download all media
    downloader.download_all(posts, max_workers=5)

    print('\n' + '='*70)
    print('✅ ALL DONE!')
    print('='*70)
    print(f'\nYour media files are in: {downloader.output_dir.absolute()}')
    print('\nFolder structure:')
    print('  grok_downloads/')
    print('    ├── {user_id}/')
    print('    │   └── {post_id}/')
    print('    │       ├── parent.png')
    print('    │       ├── child_00_xxx.mp4')
    print('    │       └── child_01_xxx.mp4')
    print()


if __name__ == '__main__':
    main()
