from app.models import Achievement, CharacterProfile, CharacterStat, SkillUnlock, User, UserProfile

BASE_STATS = [
    ("strength", "STRENGTH"),
    ("wealth", "WEALTH"),
    ("intellect", "INTELLECT"),
    ("wisdom", "WISDOM"),
    ("charisma", "CHARISMA"),
]

BASE_ACHIEVEMENTS = [
    ("first_streak", "First Streak"),
    ("first_level_up", "First Level Up"),
    ("boss_slayer", "Boss Slayer"),
]

BASE_SKILLS = [
    ("deep_focus_mode", "intellect", 2),
    ("speed_reader", "intellect", 5),
    ("pattern_seeker", "intellect", 8),
    ("polymath", "intellect", 12),
    ("oracle_pact", "intellect", 18),
]


def bootstrap_user_defaults(user: User) -> list[object]:
    defaults: list[object] = [
        UserProfile(user_id=user.id),
        CharacterProfile(user_id=user.id),
    ]

    defaults.extend(CharacterStat(user_id=user.id, stat_key=key, label=label) for key, label in BASE_STATS)
    defaults.extend(
        Achievement(user_id=user.id, achievement_key=key, label=label)
        for key, label in BASE_ACHIEVEMENTS
    )
    defaults.extend(
        SkillUnlock(user_id=user.id, skill_key=key, stat_key=stat_key, required_level=level)
        for key, stat_key, level in BASE_SKILLS
    )
    return defaults

