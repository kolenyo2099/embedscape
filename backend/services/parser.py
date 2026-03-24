"""
File parsing services for CSV and NDJSON
"""
import io
import json
from typing import Any
import pandas as pd


def parse_csv(content: bytes) -> tuple[list[dict], list[str]]:
    """Parse CSV content into list of dicts and column names"""
    try:
        # Try UTF-8 first, then fallback encodings
        for encoding in ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']:
            try:
                text = content.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            raise ValueError("Could not decode file with any supported encoding")

        df = pd.read_csv(io.StringIO(text))
        # Replace NaN with empty strings
        df = df.fillna('')
        # Convert all columns to string type for consistency
        for col in df.columns:
            df[col] = df[col].astype(str)

        columns = df.columns.tolist()
        data = df.to_dict('records')

        return data, columns

    except Exception as e:
        raise ValueError(f"CSV parsing failed: {str(e)}")


def parse_ndjson(content: bytes) -> tuple[list[dict], list[str]]:
    """Parse NDJSON content, flattening social media exports"""
    try:
        text = content.decode('utf-8')
    except UnicodeDecodeError:
        text = content.decode('utf-8-sig')

    lines = text.strip().split('\n')
    data = []

    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
            # Only apply social media flattening if the data looks like a Zeeschuimer/social export
            if _is_social_media_export(row):
                row = flatten_social_media_data(row)
            else:
                # Stringify nested values for consistent handling downstream
                row = {k: _safe_str(v) if isinstance(v, (dict, list)) else v for k, v in row.items()}
            data.append(row)
        except json.JSONDecodeError:
            continue

    if not data:
        raise ValueError("No valid JSON lines found")

    # Collect all unique keys across all rows
    all_keys = set()
    for row in data:
        all_keys.update(row.keys())

    columns = sorted(list(all_keys))

    return data, columns


def _is_social_media_export(row: dict) -> bool:
    """Detect if a row is from a social media export (Zeeschuimer or similar)"""
    # Zeeschuimer exports have a 'data' key with nested platform data
    if 'data' not in row:
        return False
    data = row.get('data')
    if not isinstance(data, dict):
        return False
    # Check for known social media indicators
    has_source_platform = 'source_platform' in row
    has_twitter_fields = data.get('__typename') == 'Tweet' or 'legacy' in data
    has_tiktok_fields = 'author' in data and 'uniqueId' in data.get('author', {})
    has_instagram_fields = 'caption' in data or 'image_versions2' in data
    return has_source_platform or has_twitter_fields or has_tiktok_fields or has_instagram_fields


def flatten_social_media_data(row: dict[str, Any]) -> dict[str, Any]:
    """
    Flatten nested social media data structures (Instagram, Twitter/X, TikTok).
    Handles Zeeschuimer exports and similar formats.
    """
    flattened = {}
    data = row.get('data', {})
    metadata = row

    # Copy top-level metadata
    for key, value in metadata.items():
        if key != 'data':
            flattened[key] = _safe_str(value)

    # Detect platform
    platform = _detect_platform(metadata, data)
    flattened['_detected_platform'] = platform

    # Extract text content
    flattened['text'] = _extract_text(data, platform)
    flattened['caption'] = flattened['text']

    # Extract user info
    user_info = _extract_user(data, platform)
    flattened.update(user_info)

    # Extract media
    media = _extract_media(data, platform)
    if media:
        flattened['image_url'] = media[0].get('url', '')
        flattened['video_url'] = media[0].get('video_url', '')
        flattened['alt_text'] = media[0].get('alt_text', '')
    else:
        flattened['image_url'] = ''
        flattened['video_url'] = ''
        flattened['alt_text'] = ''

    flattened['has_media'] = len(media) > 0
    flattened['media_count'] = len(media)

    # Extract metrics
    metrics = _extract_metrics(data, platform)
    flattened.update(metrics)

    # Extract hashtags
    hashtags = _extract_hashtags(data, platform)
    flattened['hashtags'] = ', '.join(hashtags)

    # Extract timestamp
    flattened['created_at'] = _extract_timestamp(data, platform)

    # IDs
    flattened['id'] = _safe_str(
        data.get('id') or data.get('rest_id') or data.get('pk') or
        _safe_get(data, 'legacy.id_str') or ''
    )

    return flattened


def _safe_str(value: Any) -> str:
    """Convert value to string safely"""
    if value is None:
        return ''
    if isinstance(value, (dict, list)):
        return json.dumps(value)
    return str(value)


def _safe_get(obj: dict, path: str, default: Any = '') -> Any:
    """Safely get nested value using dot notation"""
    if not obj:
        return default
    keys = path.split('.')
    current = obj
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        elif isinstance(current, list):
            try:
                idx = int(key)
                current = current[idx]
            except (ValueError, IndexError):
                return default
        else:
            return default
    return current if current is not None else default


def _detect_platform(metadata: dict, data: dict) -> str:
    """Detect social media platform from data structure"""
    source = str(metadata.get('source_platform', '')).lower()
    if 'twitter' in source or 'x.com' in source:
        return 'twitter'
    if 'instagram' in source:
        return 'instagram'
    if 'tiktok' in source:
        return 'tiktok'

    # Structure-based detection
    if data.get('__typename') == 'Tweet' or _safe_get(data, 'legacy.full_text'):
        return 'twitter'
    if data.get('author', {}).get('uniqueId') or data.get('video', {}).get('playAddr'):
        return 'tiktok'
    if _safe_get(data, 'caption.text') or data.get('owner', {}).get('username'):
        return 'instagram'

    return 'unknown'


def _extract_text(data: dict, platform: str) -> str:
    """Extract main text content based on platform"""
    if platform == 'twitter':
        return (
            _safe_get(data, 'legacy.full_text') or
            data.get('full_text', '') or
            data.get('text', '')
        )
    elif platform == 'tiktok':
        return data.get('desc', '') or _safe_get(data, 'contents.0.desc', '')
    elif platform == 'instagram':
        return _safe_get(data, 'caption.text', '') or data.get('accessibility_caption', '')
    else:
        return (
            _safe_get(data, 'legacy.full_text') or
            _safe_get(data, 'caption.text') or
            data.get('desc', '') or
            data.get('text', '') or
            data.get('body', '')
        )


def _extract_user(data: dict, platform: str) -> dict[str, Any]:
    """Extract user information"""
    if platform == 'twitter':
        user = _safe_get(data, 'core.user_results.result', {})
        legacy = user.get('legacy', {}) if isinstance(user, dict) else {}
        return {
            'username': legacy.get('screen_name', '') or user.get('screen_name', ''),
            'full_name': legacy.get('name', '') or user.get('name', ''),
            'followers_count': legacy.get('followers_count', 0),
            'verified': user.get('is_blue_verified', False) or legacy.get('verified', False)
        }
    elif platform == 'tiktok':
        author = data.get('author', {})
        stats = data.get('authorStats', {})
        return {
            'username': author.get('uniqueId', ''),
            'full_name': author.get('nickname', ''),
            'followers_count': stats.get('followerCount', 0),
            'verified': author.get('verified', False)
        }
    elif platform == 'instagram':
        owner = data.get('owner', {}) or data.get('user', {})
        return {
            'username': owner.get('username', ''),
            'full_name': owner.get('full_name', ''),
            'followers_count': owner.get('follower_count', 0),
            'verified': owner.get('is_verified', False)
        }
    return {'username': '', 'full_name': '', 'followers_count': 0, 'verified': False}


def _extract_media(data: dict, platform: str) -> list[dict]:
    """Extract media URLs"""
    media = []

    if platform == 'twitter':
        legacy_media = _safe_get(data, 'legacy.entities.media', [])
        extended_media = _safe_get(data, 'legacy.extended_entities.media', [])
        all_media = extended_media if extended_media else legacy_media

        if isinstance(all_media, list):
            for m in all_media:
                media.append({
                    'type': m.get('type', 'photo'),
                    'url': m.get('media_url_https', '') or m.get('media_url', ''),
                    'video_url': _safe_get(m, 'video_info.variants.0.url', ''),
                    'alt_text': m.get('ext_alt_text', '')
                })

    elif platform == 'tiktok':
        video = data.get('video', {})
        if video.get('cover') or video.get('originCover'):
            media.append({
                'type': 'video',
                'url': video.get('cover') or video.get('originCover', ''),
                'video_url': video.get('playAddr', ''),
                'alt_text': ''
            })

    elif platform == 'instagram':
        candidates = _safe_get(data, 'image_versions2.candidates', [])
        if isinstance(candidates, list) and candidates:
            media.append({
                'type': 'photo',
                'url': candidates[0].get('url', ''),
                'video_url': '',
                'alt_text': data.get('accessibility_caption', '')
            })

        video_versions = data.get('video_versions', [])
        if isinstance(video_versions, list) and video_versions:
            media.append({
                'type': 'video',
                'url': candidates[0].get('url', '') if candidates else '',
                'video_url': video_versions[0].get('url', ''),
                'alt_text': ''
            })

    return media


def _extract_metrics(data: dict, platform: str) -> dict[str, int]:
    """Extract engagement metrics"""
    if platform == 'twitter':
        legacy = data.get('legacy', {})
        return {
            'likes': legacy.get('favorite_count', 0),
            'retweets': legacy.get('retweet_count', 0),
            'comments': legacy.get('reply_count', 0),
            'views': int(_safe_get(data, 'views.count', '0') or 0)
        }
    elif platform == 'tiktok':
        stats = data.get('stats', {}) or data.get('statsV2', {})
        return {
            'likes': int(stats.get('diggCount', 0) or 0),
            'retweets': 0,
            'comments': int(stats.get('commentCount', 0) or 0),
            'views': int(stats.get('playCount', 0) or 0),
            'shares': int(stats.get('shareCount', 0) or 0)
        }
    elif platform == 'instagram':
        return {
            'likes': data.get('like_count', 0),
            'retweets': 0,
            'comments': data.get('comment_count', 0),
            'views': data.get('view_count', 0) or data.get('play_count', 0)
        }
    return {'likes': 0, 'retweets': 0, 'comments': 0, 'views': 0}


def _extract_hashtags(data: dict, platform: str) -> list[str]:
    """Extract hashtags"""
    hashtags = []

    if platform == 'twitter':
        entities = _safe_get(data, 'legacy.entities.hashtags', [])
        if isinstance(entities, list):
            hashtags = [h.get('text', '') for h in entities if h.get('text')]

    elif platform == 'tiktok':
        challenges = data.get('challenges', [])
        if isinstance(challenges, list):
            hashtags = [c.get('title', '') for c in challenges if c.get('title')]

    elif platform == 'instagram':
        caption = _safe_get(data, 'caption.text', '')
        import re
        matches = re.findall(r'#[\w\u00C0-\u024F]+', caption)
        hashtags = [m.replace('#', '') for m in matches]

    return list(set(hashtags))


def _extract_timestamp(data: dict, platform: str) -> str:
    """Extract timestamp"""
    from datetime import datetime

    if platform == 'twitter':
        return _safe_get(data, 'legacy.created_at', '')
    elif platform == 'tiktok':
        ts = data.get('createTime')
        if ts:
            return datetime.fromtimestamp(int(ts)).isoformat()
    elif platform == 'instagram':
        ts = data.get('taken_at')
        if ts:
            return datetime.fromtimestamp(int(ts)).isoformat()

    return ''
