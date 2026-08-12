import os
import json
import requests
from collections import defaultdict
from xml.sax.saxutils import escape as svg_escape
# ============================================================
# Configuration from environment
# ============================================================

TOKEN = os.environ["STATS_TOKEN"]

CACHE_FILE = os.environ.get(
    "REPO_CACHE_FILE",
    "repo_cache.json"
)

LANGUAGE_LIMIT = int(
    os.environ.get("LANGUAGE_LIMIT", "10")
)

IGNORE = {
    language.strip()
    for language in os.environ.get(
        "LANGUAGES_IGNORE",
        ""
    ).split(",")
    if language.strip()
}

SVG_FILE = os.environ.get(
    "SVG_FILE",
    "language-metrics.svg"
)

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2026-03-10",
}


# ============================================================
# GitHub API helper
# ============================================================

def github_get(url, params=None):
    response = requests.get(
        url,
        headers=HEADERS,
        params=params,
        timeout=30,
    )

    response.raise_for_status()

    return response.json()


# ============================================================
# Load / create cache
# ============================================================

# def load_cache():
#
#     if not os.path.exists(CACHE_FILE):
#         return None
#
#     # Empty file = no cache
#     if os.path.getsize(CACHE_FILE) == 0:
#         return None
#
#     try:
#         with open(CACHE_FILE, "r", encoding="utf-8") as f:
#             data = json.load(f)
#
#         # Empty JSON object/list/etc = no cache
#         if not data:
#             return None
#
#         return data
#
#     except (json.JSONDecodeError, OSError):
#         print("Cache exists but is invalid. Rebuilding it.")
#         return None


def fetch_from_github():

    print("No cache found.")
    print("Fetching repositories from GitHub...\n")

    repos = []

    page = 1

    while True:

        batch = github_get(
            "https://api.github.com/user/repos",
            {
                "visibility": "all",
                "affiliation": "owner",
                "per_page": 100,
                "page": page,
            },
        )

        if not batch:
            break

        repos.extend(batch)

        page += 1


    cached_repos = []

    for repo in repos:

        full_name = repo["full_name"]

        print(f"Fetching languages: {full_name}")

        languages = github_get(
            f"https://api.github.com/repos/"
            f"{full_name}/languages"
        )

        cached_repos.append({
            "name": repo["name"],
            "full_name": full_name,
            "private": repo["private"],
            "fork": repo["fork"],
            "languages": languages,
        })


    cache = {
        "repositories": cached_repos
    }


    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(
            cache,
            f,
            indent=2,
        )


    print(f"\nSaved cache to: {CACHE_FILE}")

    return cache


# ============================================================
# Get cached data
# ============================================================

# cache = load_cache()
#
# if cache is not None:
#
#     print(f"Using cached data: {CACHE_FILE}")
#
# else:


cache = fetch_from_github()


# ============================================================
# Aggregate languages
# ============================================================

languages = defaultdict(int)
all_languages = set()
for repo in cache["repositories"]:

    # Ignore forks
    if repo["fork"]:
        continue

    for language, byte_count in repo["languages"].items():

        all_languages.add(language.lower()) # For count only

        # Ignore configured languages
        if language.lower() in IGNORE:
            continue

        languages[language] += byte_count


# ============================================================
# Sort
# ============================================================

languages = sorted(
    languages.items(),
    key=lambda x: x[1],
    reverse=True,
)
language_count = len(all_languages)
print(languages)
print(language_count)
languages = languages[:LANGUAGE_LIMIT]

total = sum(
    byte_count
    for _, byte_count in languages
)


# ============================================================
# Output
# ============================================================

def format_bytes(value):

    if value >= 1024 * 1024:
        return f"{value / (1024 * 1024):.2f} MB"

    if value >= 1024:
        return f"{value / 1024:.1f} KB"

    return f"{value} B"


print("\n==========================================")
print("         MOST USED LANGUAGES")
print("==========================================\n")

for language, byte_count in languages:

    percentage = (
        byte_count / total * 100
        if total
        else 0
    )

    print(
        f"{language:<25}"
        f"{format_bytes(byte_count):>12}"
        f"  {percentage:6.2f}%"
    )

print("\n==========================================")
print(f"Repositories in cache: {len(cache['repositories'])}")
print(f"Language limit:         {LANGUAGE_LIMIT}")
print(f"Ignored:                {', '.join(IGNORE) or 'None'}")
print(f"Cache:                  {CACHE_FILE}")
print("==========================================")


# ============================================================
# SVG generation
# ============================================================

SVG_WIDTH = 576

COLUMNS = 2
COLUMN_WIDTH = 270
COLUMN_GAP = 12

ROW_HEIGHT = 23

# Layout:
#
#   24 languages
#
#   [ language graph ]
#
#        Most used languages
#
#   language grid
#

LANGUAGE_COUNT_HEIGHT = 28
GRAPH_HEIGHT = 8
GRAPH_GAP = 10
TITLE_HEIGHT = 30

HEADER_HEIGHT = (
    LANGUAGE_COUNT_HEIGHT
    + GRAPH_HEIGHT
    + GRAPH_GAP
    + TITLE_HEIGHT
)

PADDING_X = 12
PADDING_TOP = 8
PADDING_BOTTOM = 8

ROWS = (
    len(languages) + COLUMNS - 1
) // COLUMNS

SVG_HEIGHT = (
    PADDING_TOP
    + HEADER_HEIGHT
    + (ROWS * ROW_HEIGHT)
    + PADDING_BOTTOM
)


# ------------------------------------------------------------
# Colors
# ------------------------------------------------------------

TEXT = "#c9d1d9"
MUTED = "#8b949e"
TITLE = "#0099ff"

BAR_X = PADDING_X
BAR_Y = PADDING_TOP + LANGUAGE_COUNT_HEIGHT + 5
BAR_WIDTH = SVG_WIDTH - (PADDING_X * 2)
BAR_HEIGHT = GRAPH_HEIGHT
BAR_RADIUS = 4


# ------------------------------------------------------------
# Language colors
# ------------------------------------------------------------

LANGUAGE_COLORS = {
    "c": "#555555",
    "c++": "#f34b7d",
    "cmake": "#DA3434",
    "css": "#563D7C",
    "dart": "#00B4AB",
    "go": "#00ADD8",
    "haskell": "#5E5086",
    "html": "#E34C26",
    "java": "#b07219",
    "javascript": "#f1e05a",
    "kotlin": "#A97BFF",
    "lisp": "#3FB68B",
    "lua": "#000080",
    "objective-c": "#438eff",
    "ocaml": "#3be133",
    "python": "#3572A5",
    "qml": "#44a51c",
    "ruby": "#701516",
    "rust": "#dea584",
    "scss": "#c6538c",
    "shell": "#89e051",
    "swift": "#F05138",
    "typescript": "#3178c6",
    "zig": "#ec915c",
}

# ------------------------------------------------------------
# SVG
# ------------------------------------------------------------

svg = []

svg.append(
    f'''
    <svg
        xmlns="http://www.w3.org/2000/svg"
        width="{SVG_WIDTH}"
        height="{SVG_HEIGHT}"
        viewBox="0 0 {SVG_WIDTH} {SVG_HEIGHT}">
    '''
)


# ------------------------------------------------------------
# Fonts
# ------------------------------------------------------------

svg.append(
    f"""
    <style>

    .language-count {{
        font-family:
            -apple-system,
            BlinkMacSystemFont,
            "Segoe UI",
            Helvetica,
            Arial,
            sans-serif;

        font-size: 14px;
        fill: {TITLE};
        font-weight: 600;
    }}

    .title {{
        font-family:
            -apple-system,
            BlinkMacSystemFont,
            "Segoe UI",
            Helvetica,
            Arial,
            sans-serif;

        font-size: 16px;
        font-weight: 600;
    }}

    .language {{
        font-family:
            -apple-system,
            BlinkMacSystemFont,
            "Segoe UI",
            Helvetica,
            Arial,
            sans-serif;

        font-size: 13px;
        font-weight: 600;
    }}

    .value {{
        font-family:
            -apple-system,
            BlinkMacSystemFont,
            "Segoe UI",
            Helvetica,
            Arial,
            sans-serif;

        font-size: 12px;
    }}

    </style>
    """
)

# ============================================================
# Language count
# ============================================================

svg.append(
    f'''
    <text
        x="{PADDING_X}"
        y="{PADDING_TOP + 15}"
        class="language-count"
        fill="{TEXT}">
        {language_count} languages
    </text>
    '''
)


# ============================================================
# Stacked language graph
# ============================================================

current_x = BAR_X


for index, (language, byte_count) in enumerate(
    languages
):

    percentage = (
        byte_count / total * 100
        if total
        else 0
    )

    width = (
        BAR_WIDTH * percentage / 100
    )

    if width <= 0:
        continue

    color = LANGUAGE_COLORS.get(
        language.lower(),
        "#8b949e"
    )

    is_first = index == 0
    is_last = index == len(languages) - 1

    r = BAR_RADIUS


    # --------------------------------------------------------
    # First segment
    # Round ONLY the left side
    # --------------------------------------------------------

    if is_first:

        svg.append(
            f'''
            <path
                d="
                    M {current_x + r:.2f} {BAR_Y}
                    H {current_x + width:.2f}
                    V {BAR_Y + BAR_HEIGHT}
                    H {current_x + r:.2f}
                    A {r} {r} 0 0 1
                      {current_x:.2f}
                      {BAR_Y + BAR_HEIGHT - r:.2f}
                    V {BAR_Y + r:.2f}
                    A {r} {r} 0 0 1
                      {current_x + r:.2f}
                      {BAR_Y}
                    Z
                "
                fill="{color}"
            />
            '''
        )


    # --------------------------------------------------------
    # Last segment
    # Round ONLY the right side
    # --------------------------------------------------------

    elif is_last:

        svg.append(
            f'''
            <path
                d="
                    M {current_x:.2f} {BAR_Y}
                    H {current_x + width - r:.2f}
                    A {r} {r} 0 0 1
                      {current_x + width:.2f}
                      {BAR_Y + r:.2f}
                    V {BAR_Y + BAR_HEIGHT - r:.2f}
                    A {r} {r} 0 0 1
                      {current_x + width - r:.2f}
                      {BAR_Y + BAR_HEIGHT:.2f}
                    H {current_x:.2f}
                    Z
                "
                fill="{color}"
            />
            '''
        )


    # --------------------------------------------------------
    # Middle segments
    # Completely square
    # --------------------------------------------------------

    else:

        svg.append(
            f'''
            <rect
                x="{current_x:.2f}"
                y="{BAR_Y}"
                width="{width:.2f}"
                height="{BAR_HEIGHT}"
                fill="{color}"
            />
            '''
        )


    current_x += width


# ============================================================
# Most used languages title
# ============================================================

TITLE_Y = (
    BAR_Y
    + BAR_HEIGHT
    + GRAPH_GAP
    + 14
)

svg.append(
    f'''
    <text
        x="{SVG_WIDTH / 2}"
        y="{TITLE_Y}"
        text-anchor="middle"
        class="title"
        fill="{TITLE}">
        Most used languages
    </text>
    '''
)


# ============================================================
# Language grid
# ============================================================

GRID_Y = (
    TITLE_Y
    + 20
)


for index, (language, byte_count) in enumerate(
    languages
):

    percentage = (
        byte_count / total * 100
        if total
        else 0
    )

    column = index % COLUMNS
    row = index // COLUMNS

    x = (
        PADDING_X
        + column * (
            COLUMN_WIDTH + COLUMN_GAP
        )
    )

    y = (
        GRID_Y
        + row * ROW_HEIGHT
    )

    color = LANGUAGE_COLORS.get(
        language.lower(),
        "#8b949e"
    )


    # --------------------------------------------------------
    # Language dot
    # --------------------------------------------------------

    svg.append(
        f'''
        <circle
            cx="{x + 5}"
            cy="{y + 5}"
            r="4"
            fill="{color}"
        />
        '''
    )


    # --------------------------------------------------------
    # Language name
    # --------------------------------------------------------

    svg.append(
        f'''
        <text
            x="{x + 15}"
            y="{y + 9}"
            class="language"
            fill="{TEXT}">
            {svg_escape(language)}
        </text>
        '''
    )


    # --------------------------------------------------------
    # Bytes
    # --------------------------------------------------------

    svg.append(
        f'''
        <text
            x="{x + 165}"
            y="{y + 9}"
            class="value"
            fill="{MUTED}">
            {format_bytes(byte_count)}
        </text>
        '''
    )


    # --------------------------------------------------------
    # Percentage
    # --------------------------------------------------------

    svg.append(
        f'''
        <text
            x="{x + COLUMN_WIDTH}"
            y="{y + 9}"
            text-anchor="end"
            class="value"
            fill="{MUTED}">
            {percentage:.2f}%
        </text>
        '''
    )


# ============================================================
# Finish SVG
# ============================================================

svg.append("</svg>")


# ============================================================
# Write SVG
# ============================================================

with open(
    SVG_FILE,
    "w",
    encoding="utf-8"
) as f:

    f.write("\n".join(svg))


print(f"Generated: {SVG_FILE}")
