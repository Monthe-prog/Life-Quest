from __future__ import annotations

from app.models import Achievement, CharacterProfile, CharacterStat, SkillUnlock, User, UserProfile
from app.modules.auth.bootstrap import BASE_ACHIEVEMENTS, BASE_SKILLS, BASE_STATS, bootstrap_user_defaults


def test_bootstrap_user_defaults_creates_expected_records() -> None:
    user = User(id="user-123", email="operator@example.com", password_hash="hash")
    defaults = bootstrap_user_defaults(user)

    assert len(defaults) == 2 + len(BASE_STATS) + len(BASE_ACHIEVEMENTS) + len(BASE_SKILLS)
    assert sum(isinstance(item, UserProfile) for item in defaults) == 1
    assert sum(isinstance(item, CharacterProfile) for item in defaults) == 1
    assert sum(isinstance(item, CharacterStat) for item in defaults) == len(BASE_STATS)
    assert sum(isinstance(item, Achievement) for item in defaults) == len(BASE_ACHIEVEMENTS)
    assert sum(isinstance(item, SkillUnlock) for item in defaults) == len(BASE_SKILLS)
    assert all(getattr(item, "user_id", user.id) == user.id for item in defaults)
