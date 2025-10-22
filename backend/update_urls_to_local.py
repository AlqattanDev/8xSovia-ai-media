#!/usr/bin/env python3
"""
Update database URLs from https:// to https_/ format for local serving.
"""
import asyncio
from sqlalchemy import select, update
from app.database import AsyncSessionLocal
from app.models import MediaPost, ChildPost


def convert_url_to_local(url: str) -> str:
    """Convert https:// URL to https_/ local path format."""
    if url.startswith('https://'):
        return url.replace('https://', 'https_/', 1)
    return url


async def update_media_urls():
    """Update all media URLs in database to local format."""
    async with AsyncSessionLocal() as db:
        # Update parent posts
        result = await db.execute(
            select(MediaPost).where(MediaPost.media_url.like('https://%'))
        )
        parent_posts = result.scalars().all()

        print(f"Found {len(parent_posts)} parent posts with remote URLs")

        for post in parent_posts:
            old_url = post.media_url
            new_url = convert_url_to_local(old_url)
            post.media_url = new_url
            print(f"  Updated post {post.id}")
            print(f"    From: {old_url}")
            print(f"    To:   {new_url}")

        # Update child posts
        child_result = await db.execute(
            select(ChildPost).where(ChildPost.media_url.like('https://%'))
        )
        child_posts = child_result.scalars().all()

        print(f"\nFound {len(child_posts)} child posts with remote URLs")

        for child in child_posts:
            old_url = child.media_url
            new_url = convert_url_to_local(old_url)
            child.media_url = new_url
            print(f"  Updated child post {child.id}")
            print(f"    From: {old_url}")
            print(f"    To:   {new_url}")

        # Commit changes
        await db.commit()

        print(f"\n✓ Updated {len(parent_posts)} parent posts and {len(child_posts)} child posts")
        print("All URLs now use local https_/ format")


if __name__ == "__main__":
    asyncio.run(update_media_urls())
