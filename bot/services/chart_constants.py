"""Точки и аспекты как в отчёте AuthorityAstrology (My_AstrologyMap.pdf)."""

from kerykeion.settings.config_constants import ALL_ACTIVE_ASPECTS

# Планеты, узлы, астероиды, углы, Vertex, Part of Fortune (Selena в Kerykeion нет)
PDF_ACTIVE_POINTS = [
    "Sun",
    "Moon",
    "Mercury",
    "Venus",
    "Mars",
    "Jupiter",
    "Saturn",
    "Uranus",
    "Neptune",
    "Pluto",
    "True_North_Lunar_Node",
    "True_South_Lunar_Node",
    "Mean_Lilith",
    "Chiron",
    "Ceres",
    "Pallas",
    "Juno",
    "Vesta",
    "Pholus",
    "Ascendant",
    "Descendant",
    "Medium_Coeli",
    "Imum_Coeli",
    "Vertex",
    "Pars_Fortunae",
]

PDF_ACTIVE_ASPECTS = ALL_ACTIVE_ASPECTS

MAJOR_ASPECT_NAMES = frozenset(
    {"conjunction", "opposition", "trine", "sextile", "square"}
)

MINOR_ASPECT_NAMES = frozenset(
    {
        "quintile",
        "semi-sextile",
        "semi-square",
        "sesquiquadrate",
        "biquintile",
        "quincunx",
    }
)

# Порядок вывода позиций планет (как в PDF)
PLANET_POSITION_ORDER = [
    ("sun", "Sun"),
    ("moon", "Moon"),
    ("mercury", "Mercury"),
    ("venus", "Venus"),
    ("mars", "Mars"),
    ("jupiter", "Jupiter"),
    ("saturn", "Saturn"),
    ("uranus", "Uranus"),
    ("neptune", "Neptune"),
    ("pluto", "Pluto"),
    ("true_north_lunar_node", "True_North_Lunar_Node"),
    ("true_south_lunar_node", "True_South_Lunar_Node"),
    ("mean_lilith", "Mean_Lilith"),
    ("ceres", "Ceres"),
    ("juno", "Juno"),
    ("pallas", "Pallas"),
    ("vesta", "Vesta"),
    ("chiron", "Chiron"),
    ("pholus", "Pholus"),
    ("ascendant", "Ascendant"),
    ("descendant", "Descendant"),
    ("medium_coeli", "Medium_Coeli"),
    ("imum_coeli", "Imum_Coeli"),
    ("vertex", "Vertex"),
    ("pars_fortunae", "Pars_Fortunae"),
]
