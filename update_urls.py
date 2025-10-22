#!/usr/bin/env python3
"""
Script to update external URLs in json.json to local file paths.
Uses consolidated utilities from utils/common.py.
"""
from utils.common import update_media_urls, load_json_posts, save_json_posts


def main():
    # Paths
    input_file = 'json.json'
    output_file = 'json_local.json'
    backup_file = 'json.json.backup'

    print(f"Reading {input_file}...")

    # Read the original JSON using consolidated utility
    data = load_json_posts(input_file)
    print(f"Loaded {len(data)} media items")

    # Create backup
    print(f"Creating backup at {backup_file}...")
    save_json_posts(data, backup_file)

    # Update URLs to local paths using consolidated utility
    print("Updating URLs to local paths...")
    updated_data = update_media_urls(data)

    # Count updates
    url_count = 0
    for item in updated_data:
        if 'mediaUrl' in item:
            url_count += 1
        if 'childPosts' in item:
            url_count += len(item['childPosts'])

    print(f"Updated {url_count} media URLs")

    # Write updated JSON
    print(f"Writing updated JSON to {output_file}...")
    save_json_posts(updated_data, output_file)

    print("\nDone! Files created:")
    print(f"  - {output_file} (updated with local paths)")
    print(f"  - {backup_file} (backup of original)")
    print("\nYou can now use json_local.json for your local website.")


if __name__ == '__main__':
    main()
