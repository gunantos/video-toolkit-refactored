"""
Caption templating from config for per-platform customization
"""

from typing import Dict, Any, List

from core.config import get_config


def render_platform_caption(platform: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
    cfg = get_config()
    meta_title = metadata.get("title", "")
    meta_desc = metadata.get("description", "")
    tags: List[str] = metadata.get("tags", [])

    if platform == "tiktok":
        plat = getattr(cfg, "platforms", None)
        p = getattr(plat, platform, {}) if plat else {}
        hashtag_limit = getattr(p, "hashtag_limit", 8) if isinstance(p, dict) else p.get("hashtag_limit", 8) if p else 8
        hashtags_cfg = getattr(p, "hashtags", []) if isinstance(p, dict) else p.get("hashtags", []) if p else []
        use_tags = hashtags_cfg or tags
        use_tags = use_tags[:hashtag_limit]
        hashtags_line = " ".join(f"#{t}" for t in use_tags)
        template = (p.get("caption_template") if isinstance(p, dict) else None) or "{title}\n{hashtags}"
        caption = template.format(title=meta_title, hashtags=hashtags_line).strip()
        return {"caption": caption, "tags": use_tags}

    if platform == "telegram":
        plat = getattr(cfg, "platforms", None)
        p = getattr(plat, platform, {}) if plat else {}
        template = (p.get("caption_template") if isinstance(p, dict) else None) or "{title}"
        caption = template.format(title=meta_title)
        return {"caption": caption}

    if platform in ("youtube", "facebook", "dailymotion"):
        plat = getattr(cfg, "platforms", None)
        p = getattr(plat, platform, {}) if plat else {}
        template = (p.get("description_template") if isinstance(p, dict) else None) or "{title}\n\n{description}"
        caption = template.format(title=meta_title, description=meta_desc, tags=", ".join(tags))
        return {"caption": caption, "tags": tags}

    return {"caption": meta_title, "tags": tags}
