from app.core.config import settings


def build_invite_link(slug: str) -> str:
    return f"{settings.frontend_url.rstrip('/')}/e/{slug}"
