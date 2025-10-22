#!/usr/bin/env python3
"""
Check database for media URLs and identify which files need to be downloaded locally.
Generates a download list for missing files.
"""
import asyncio
import os
from urllib.parse import urlparse
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models import MediaPost, ChildPost


def url_to_local_path(url: str, base_dir: str = "/Users/alialqattan/Downloads/8xSovia") -> str:
    """Convert URL to expected local file path."""
    # Check if it's already in local format (starts with https_/)
    if url.startswith('https_/'):
        return os.path.join(base_dir, url)

    # Check if it's a full HTTP URL
    if url.startswith('http'):
        parsed = urlparse(url)
        local_path = os.path.join(
            base_dir,
            "https_",
            parsed.netloc,
            parsed.path.lstrip('/')
        )
        return local_path

    # Already a local path
    return url


def local_path_to_url(local_path: str, base_dir: str = "/Users/alialqattan/Downloads/8xSovia") -> str:
    """Convert local path back to download URL."""
    # Remove base directory and https_/ prefix
    if local_path.startswith(base_dir):
        local_path = local_path[len(base_dir):].lstrip('/')

    if local_path.startswith('https_/'):
        local_path = local_path[6:]  # Remove 'https_/'
        return 'https://' + local_path

    return local_path


async def check_missing_media():
    """Check all media URLs in database and identify missing local files."""
    async with AsyncSessionLocal() as db:
        # Get all media posts
        result = await db.execute(select(MediaPost))
        media_posts = result.scalars().all()

        # Get all child posts
        child_result = await db.execute(select(ChildPost))
        child_posts = child_result.scalars().all()

        print(f"Checking {len(media_posts)} parent posts and {len(child_posts)} child posts...")
        print()

        # Track statistics
        total_checked = 0
        remote_urls = 0
        local_files_exist = 0
        local_files_missing = 0
        missing_urls = []

        # Check parent posts
        print("=" * 80)
        print("PARENT POSTS")
        print("=" * 80)

        for post in media_posts:
            total_checked += 1
            url = post.media_url
            local_path = url_to_local_path(url)

            # Check if this is a remote URL or already local format
            if url.startswith('http'):
                remote_urls += 1

                if os.path.exists(local_path):
                    local_files_exist += 1
                    print(f"✓ EXISTS: {post.id}")
                    print(f"  Local: {local_path}")
                else:
                    local_files_missing += 1
                    missing_urls.append(url)  # Already proper URL
                    print(f"✗ MISSING: {post.id}")
                    print(f"  URL: {url}")
                    print(f"  Expected: {local_path}")
                print()
            elif url.startswith('https_/'):
                # Database has local path format - need to check file and convert to URL if missing
                remote_urls += 1

                if os.path.exists(local_path):
                    local_files_exist += 1
                    print(f"✓ EXISTS: {post.id}")
                    print(f"  Local: {local_path}")
                else:
                    local_files_missing += 1
                    # Convert local path format to proper download URL
                    download_url = local_path_to_url(url)
                    missing_urls.append(download_url)
                    print(f"✗ MISSING: {post.id}")
                    print(f"  URL (DB format): {url}")
                    print(f"  Download URL: {download_url}")
                    print(f"  Expected: {local_path}")
                print()

        # Check child posts
        print("=" * 80)
        print("CHILD POSTS")
        print("=" * 80)

        for child in child_posts:
            total_checked += 1
            url = child.media_url
            local_path = url_to_local_path(url)

            # Check if this is a remote URL or already local format
            if url.startswith('http'):
                remote_urls += 1

                if os.path.exists(local_path):
                    local_files_exist += 1
                    print(f"✓ EXISTS: {child.id}")
                    print(f"  Local: {local_path}")
                else:
                    local_files_missing += 1
                    missing_urls.append(url)  # Already proper URL
                    print(f"✗ MISSING: {child.id}")
                    print(f"  URL: {url}")
                    print(f"  Expected: {local_path}")
                print()
            elif url.startswith('https_/'):
                # Database has local path format - need to check file and convert to URL if missing
                remote_urls += 1

                if os.path.exists(local_path):
                    local_files_exist += 1
                    print(f"✓ EXISTS: {child.id}")
                    print(f"  Local: {local_path}")
                else:
                    local_files_missing += 1
                    # Convert local path format to proper download URL
                    download_url = local_path_to_url(url)
                    missing_urls.append(download_url)
                    print(f"✗ MISSING: {child.id}")
                    print(f"  URL (DB format): {url}")
                    print(f"  Download URL: {download_url}")
                    print(f"  Expected: {local_path}")
                print()

        # Summary
        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Total media items checked: {total_checked}")
        print(f"Remote URLs in database: {remote_urls}")
        print(f"Local files exist: {local_files_exist}")
        print(f"Local files MISSING: {local_files_missing}")
        print()

        # Write missing URLs to file
        if missing_urls:
            output_file = "/Users/alialqattan/Downloads/8xSovia/missing_media_urls.txt"
            with open(output_file, 'w') as f:
                for url in missing_urls:
                    f.write(url + '\n')

            print(f"✓ Missing URLs written to: {output_file}")
            print(f"  ({len(missing_urls)} URLs)")
            print()
            print("Download these files and place them in the https_/ directory structure.")
        else:
            print("✓ All media files exist locally!")

        print("=" * 80)


if __name__ == "__main__":
    asyncio.run(check_missing_media())
