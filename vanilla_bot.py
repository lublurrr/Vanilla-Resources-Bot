"""
Vanilla Resource Bot — Discord bot for browsing the Vanilla Resource Library (VRL)
and the Vanilla Ultimate Archive (VUA).

Requirements:
    pip install discord.py

Configuration:
    Set DISCORD_BOT_TOKEN as an environment variable (e.g. in Railway Variables).

Data files (must be in the same folder as this script):
    vrl_resources.txt   — exported from Vanilla_Resource_Library.docx
    vua_cases.txt       — exported from Vanilla_Ultimate_Archive.docx
"""

import discord
from discord.ext import commands
from discord import app_commands
import os, random, re, pathlib, sys

# ──────────────────────────────────────────────
#  CONFIG
# ──────────────────────────────────────────────
BOT_TOKEN = "INSERT_BOT_TOKEN"

if not BOT_TOKEN:
    sys.exit("[ERROR] DISCORD_BOT_TOKEN environment variable is not set.")

MAIN_BANNER = "https://file.garden/abNCJyHSwTHZbA3u/Vanilla%20Bot%20Banners/vanillasourcebot"
VRL_BANNER  = "https://file.garden/abNCJyHSwTHZbA3u/Vanilla%20Bot%20Banners/vanillaresourcelibrary"
VUA_BANNER  = "https://file.garden/abNCJyHSwTHZbA3u/Vanilla%20Bot%20Banners/vanillaultimatearchive.png"

MAIN_COLOR  = 0x9B59B6   # purple
VRL_COLOR   = 0x7B3F00   # brown
VUA_COLOR   = 0x00FFFF   # cyan

LINKS = {
    "Vanilla Case List":        "https://docs.google.com/document/d/1DgFg6CTjKMST69qlyQuhFzqYMZlA7pUZ8MHcrREdnm8/edit?usp=sharing",
    "Vanilla Resource Library": "https://docs.google.com/document/d/1XS_D2jgcGp_61gl2dnAozOop3shUC06HEPOT3iuaU-s/edit?tab=t.0",
    "Vanilla Ultimate Archive": "https://docs.google.com/document/u/0/d/1qsdx5w8xxOmNuoyU0XQqZ9owFCZ5Xt2ihsLVP0tWqjw/edit",
    "VCL Tier List":            "https://tiermaker.com/create/vanilla-case-list-logos-17506473",
}

DATA_DIR = pathlib.Path(__file__).parent

# ──────────────────────────────────────────────
#  DATA LOADING
# ──────────────────────────────────────────────
def parse_vrl(path: pathlib.Path) -> dict[str, list[dict]]:
    data: dict[str, list[dict]] = {}
    current = None

    with open(path, encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            if line.startswith("===") and line.endswith("==="):
                current = line.strip("= ").lower()
                data[current] = []
                continue
            if current is None:
                continue

            parts = [p.strip() for p in line.split(" | ")]
            entry: dict = {"name": parts[0], "type": "", "creator": "", "description": "", "url": ""}
            for part in parts[1:]:
                if part.startswith("Type: "):
                    entry["type"] = part[6:]
                elif part.startswith("Creator: "):
                    entry["creator"] = part[9:]
                elif part.startswith("Desc: "):
                    entry["description"] = part[6:]
                elif part.startswith("URL: "):
                    entry["url"] = part[5:]
                elif part.startswith("Language: "):
                    entry["language"] = part[10:]
            data[current].append(entry)

    return data


def parse_vua(path: pathlib.Path) -> tuple[dict[int, list[dict]], list[str]]:
    cases_by_year: dict[int, list[dict]] = {}
    graveyard: list[str] = []
    current_year: int | None = None
    in_graveyard = False

    with open(path, encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue

            if line.startswith("=== GRAVEYARD ==="):
                in_graveyard = True
                current_year = None
                continue

            m = re.match(r"=== YEAR (\d+) ===", line)
            if m:
                current_year = int(m.group(1))
                in_graveyard = False
                cases_by_year.setdefault(current_year, [])
                continue

            if in_graveyard:
                graveyard.append(line)
                continue

            if current_year is not None:
                parts = [p.strip() for p in line.split(" | ")]
                entry: dict = {"name": parts[0], "creator": "", "url": ""}
                for part in parts[1:]:
                    if part.startswith("Creator: "):
                        entry["creator"] = part[9:]
                    elif part.startswith("URL: "):
                        entry["url"] = part[5:]
                cases_by_year[current_year].append(entry)

    return cases_by_year, graveyard


# Load at startup
VRL_DATA: dict[str, list[dict]] = parse_vrl(DATA_DIR / "vrl_resources.txt")
VUA_DATA, VUA_GRAVEYARD = parse_vua(DATA_DIR / "vua_cases.txt")

VRL_TOTAL = sum(len(v) for v in VRL_DATA.values())
VUA_TOTAL = sum(len(v) for v in VUA_DATA.values())

VUA_ALL_CASES: list[tuple[dict, int]] = [
    (c, year)
    for year, cases in VUA_DATA.items()
    for c in cases
    if c["url"]
]

print(f"[VRL] Loaded {VRL_TOTAL} resources across {len(VRL_DATA)} sections.")
print(f"[VUA] Loaded {VUA_TOTAL} cases across {len(VUA_DATA)} years + {len(VUA_GRAVEYARD)} graveyard entries.")


# ──────────────────────────────────────────────
#  HELPERS
# ──────────────────────────────────────────────
def vrl_embed(title: str = "Vanilla Resource Library", desc: str = "") -> discord.Embed:
    e = discord.Embed(title=title, description=desc, color=VRL_COLOR)
    e.set_image(url=VRL_BANNER)
    return e


def vua_embed(title: str = "Vanilla Ultimate Archive", desc: str = "") -> discord.Embed:
    e = discord.Embed(title=title, description=desc, color=VUA_COLOR)
    e.set_image(url=VUA_BANNER)
    return e


def resource_to_str(r: dict, show_creator: bool = False) -> str:
    base = f"**[{r['name']}]({r['url']})**" if r["url"] else f"**{r['name']}**"
    parts = [base]
    if r.get("type"):
        parts.append(f"*{r['type']}*")
    if show_creator and r.get("creator"):
        parts.append(f"by {r['creator']}")
    if r.get("description"):
        parts.append(f"— {r['description'][:120]}{'…' if len(r['description']) > 120 else ''}")
    return " ".join(parts)


def case_to_str(c: dict, show_creator: bool = False) -> str:
    base = f"**[{c['name']}]({c['url']})**" if c["url"] else f"**{c['name']}**"
    if show_creator and c.get("creator"):
        return f"{base} — by {c['creator']}"
    return base


def chunk_lines(lines: list[str], limit: int = 3800) -> list[str]:
    chunks, current = [], ""
    for line in lines:
        if len(current) + len(line) + 1 > limit:
            chunks.append(current)
            current = line + "\n"
        else:
            current += line + "\n"
    if current:
        chunks.append(current)
    return chunks or ["*(no results)*"]


# ──────────────────────────────────────────────
#  BOT SETUP
# ──────────────────────────────────────────────
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"[Bot] Logged in as {bot.user} ({bot.user.id})")


# ──────────────────────────────────────────────
#  LINKS BUTTON VIEW  (used by /help)
# ──────────────────────────────────────────────
class LinksView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        for label, url in LINKS.items():
            self.add_item(discord.ui.Button(label=label, url=url, style=discord.ButtonStyle.link))


# ──────────────────────────────────────────────
#  GENERIC PAGER
# ──────────────────────────────────────────────
class Pager(discord.ui.View):
    """Reusable prev/next paginator for any embed list."""

    def __init__(self, pages: list[str], build_embed_fn):
        super().__init__(timeout=180)
        self.pages        = pages
        self._build_embed = build_embed_fn
        self.index        = 0
        self._refresh()

    def _refresh(self):
        self.prev_btn.disabled = self.index == 0
        self.next_btn.disabled = self.index == len(self.pages) - 1

    def current_embed(self) -> discord.Embed:
        return self._build_embed(self.index, len(self.pages))

    @discord.ui.button(label="◀ Prev", style=discord.ButtonStyle.secondary)
    async def prev_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index -= 1
        self._refresh()
        await interaction.response.edit_message(embed=self.current_embed(), view=self)

    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.secondary)
    async def next_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index += 1
        self._refresh()
        await interaction.response.edit_message(embed=self.current_embed(), view=self)


# ──────────────────────────────────────────────
#  /help
# ──────────────────────────────────────────────
@bot.tree.command(name="help", description="Show all Vanilla Resource Bot commands and useful links.")
async def help_cmd(interaction: discord.Interaction):
    banner_embed = discord.Embed(color=MAIN_COLOR)
    banner_embed.set_image(url=MAIN_BANNER)

    content_embed = discord.Embed(
        description=(
            "**A bot for browsing the Vanilla Resource Library and the Vanilla Ultimate Archive**"
            " — two essential Attorney Online documents.\n"
            "⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
            f"📚 **{VRL_TOTAL}** VRL resources  •  🗂️ **{VUA_TOTAL}** VUA cases"
        ),
        color=MAIN_COLOR,
    )
    content_embed.add_field(
        name="📖 VRL Commands",
        value=(
            "`/guides` — Casing guides\n"
            "`/videos` — Video content\n"
            "`/otherlists` — Other case lists\n"
            "`/casemaking` — Casemaking resources\n"
            "`/translations` — Translated resources\n"
            "`/misc` — Miscellaneous resources\n"
            "`/search vrl <query>` — Search the VRL\n"
            "`/helpvrl` — Detailed VRL help"
        ),
        inline=True,
    )
    content_embed.add_field(
        name="🗃️ VUA Commands",
        value=(
            "`/year <year>` — All cases from a year\n"
            "`/roulettevua` — Random case\n"
            "`/search vua <query>` — Search the VUA\n"
            "`/helpvua` — Detailed VUA help"
        ),
        inline=True,
    )
    content_embed.add_field(
        name="🔗 Other Links",
        value="Use the buttons below to open any of the related documents.",
        inline=False,
    )

    await interaction.response.send_message(embeds=[banner_embed, content_embed], view=LinksView())


# ──────────────────────────────────────────────
#  /helpvrl  and  /helpvua
# ──────────────────────────────────────────────
@bot.tree.command(name="helpvrl", description="Detailed help for Vanilla Resource Library commands.")
async def help_vrl_cmd(interaction: discord.Interaction):
    banner_embed = discord.Embed(color=VRL_COLOR)
    banner_embed.set_image(url=VRL_BANNER)

    content_embed = discord.Embed(
        title="Vanilla Resource Library — Help",
        description=(
            f"A curated library of **{VRL_TOTAL} resources** for Attorney Online.\n\n"
            "**Commands**\n"
            "`/guides` — All casing guides\n"
            "`/videos` — Video content\n"
            "`/otherlists` — Other case lists\n"
            "`/casemaking` — Casemaking resources\n"
            "`/translations` — Translated resources\n"
            "`/misc` — Miscellaneous resources\n"
            "`/search vrl <query>` — Search the VRL\n"
        ),
        color=VRL_COLOR,
    )
    await interaction.response.send_message(embeds=[banner_embed, content_embed])


@bot.tree.command(name="helpvua", description="Detailed help for Vanilla Ultimate Archive commands.")
async def help_vua_cmd(interaction: discord.Interaction):
    banner_embed = discord.Embed(color=VUA_COLOR)
    banner_embed.set_image(url=VUA_BANNER)

    content_embed = discord.Embed(
        title="Vanilla Ultimate Archive — Help",
        description=(
            f"An archive of **{VUA_TOTAL} cases** spanning every year of Attorney Online.\n\n"
            "**Commands**\n"
            "`/year <year>` — All cases from a given year\n"
            "`/roulettevua` — Random case (with creator's credit).\nWARNING‼️ To check fully curated cases, use the VCL\n"
            "`/search vua <query>` — Search the VUA\n"
        ),
        color=VUA_COLOR,
    )
    await interaction.response.send_message(embeds=[banner_embed, content_embed])


# ──────────────────────────────────────────────
#  VRL SECTION COMMANDS
# ──────────────────────────────────────────────
async def _send_vrl_section(interaction: discord.Interaction, section_key: str, title: str):
    resources = VRL_DATA.get(section_key, [])
    if not resources:
        await interaction.response.send_message(f"No resources found for **{title}**.", ephemeral=True)
        return

    lines = [resource_to_str(r) for r in resources]
    pages = chunk_lines(lines)
    total = len(resources)

    def build(index: int, total_pages: int) -> discord.Embed:
        return vrl_embed(
            title=f"VRL — {title}  (page {index + 1}/{total_pages})",
            desc=f"**{total} resources**\n\n{pages[index]}"
        )

    pager = Pager(pages, build)
    await interaction.response.send_message(embed=pager.current_embed(), view=pager)


@bot.tree.command(name="guides", description="Browse all casing guides from the VRL.")
async def cmd_guides(interaction: discord.Interaction):
    await _send_vrl_section(interaction, "guides", "Guides")


@bot.tree.command(name="videos", description="Browse all video resources from the VRL.")
async def cmd_videos(interaction: discord.Interaction):
    await _send_vrl_section(interaction, "videos", "Videos")


@bot.tree.command(name="otherlists", description="Browse other case lists from the VRL.")
async def cmd_otherlists(interaction: discord.Interaction):
    await _send_vrl_section(interaction, "otherlists", "Other Case Lists")


@bot.tree.command(name="casemaking", description="Browse casemaking resources from the VRL.")
async def cmd_casemaking(interaction: discord.Interaction):
    await _send_vrl_section(interaction, "casemaking", "Casemaking")


@bot.tree.command(name="translations", description="Browse translated resources from the VRL.")
async def cmd_translations(interaction: discord.Interaction):
    await _send_vrl_section(interaction, "translations", "Translations")


@bot.tree.command(name="misc", description="Browse miscellaneous resources from the VRL.")
async def cmd_misc(interaction: discord.Interaction):
    await _send_vrl_section(interaction, "misc", "Miscellaneous")


# ──────────────────────────────────────────────
#  VUA COMMANDS
# ──────────────────────────────────────────────
@bot.tree.command(name="year", description="Browse all VUA cases from a specific year (paginated).")
@app_commands.describe(year="Year (e.g. 2020)")
async def cmd_year(interaction: discord.Interaction, year: int):
    cases = VUA_DATA.get(year)
    if cases is None:
        valid = ", ".join(str(y) for y in sorted(VUA_DATA.keys()))
        await interaction.response.send_message(
            f"No cases found for **{year}**.\nAvailable years: {valid}", ephemeral=True
        )
        return

    lines = [case_to_str(c) for c in cases]
    pages = chunk_lines(lines)
    total = len(cases)

    def build(index: int, total_pages: int) -> discord.Embed:
        return vua_embed(
            title=f"VUA — Cases from {year}  (page {index + 1}/{total_pages})",
            desc=f"**{total} cases**\n\n{pages[index]}"
        )

    pager = Pager(pages, build)
    await interaction.response.send_message(embed=pager.current_embed(), view=pager)


@bot.tree.command(name="roulettevua", description="Get a random case from the Vanilla Ultimate Archive.")
async def cmd_roulette(interaction: discord.Interaction):
    if not VUA_ALL_CASES:
        await interaction.response.send_message("No cases available.", ephemeral=True)
        return

    case, year = random.choice(VUA_ALL_CASES)

    embed = vua_embed(title="🎲 Random Case — Vanilla Ultimate Archive")
    embed.add_field(name="Case", value=f"[{case['name']}]({case['url']})", inline=False)
    embed.add_field(name="Creator(s)", value=case["creator"] or "Unknown", inline=True)
    embed.add_field(name="Year", value=str(year), inline=True)
    embed.add_field(name="⚠️ WARNING ⚠️", value="Play the case you received at your own discretion.", inline=False)
    await interaction.response.send_message(embed=embed)


# ──────────────────────────────────────────────
#  UNIFIED /search  (fully paginated)
# ──────────────────────────────────────────────
@bot.tree.command(name="search", description="Search the VRL or VUA.")
@app_commands.describe(
    source="Choose: vrl or vua",
    query="Your search term"
)
@app_commands.choices(source=[
    app_commands.Choice(name="vrl", value="vrl"),
    app_commands.Choice(name="vua", value="vua"),
])
async def cmd_search(interaction: discord.Interaction, source: app_commands.Choice[str], query: str):
    q = query.strip().lower()

    if source.value == "vrl":
        results = []
        for section, resources in VRL_DATA.items():
            for r in resources:
                haystack = f"{r['name']} {r.get('creator', '')} {r.get('description', '')}".lower()
                if q in haystack:
                    results.append((section, r))

        if not results:
            await interaction.response.send_message(
                f"No VRL resources matched **\"{query}\"**.", ephemeral=True
            )
            return

        lines = [f"[{section.upper()}] {resource_to_str(r, show_creator=True)}" for section, r in results]
        pages = chunk_lines(lines)
        total = len(results)

        def build(index: int, total_pages: int) -> discord.Embed:
            return vrl_embed(
                title=f"VRL Search — \"{query}\"  (page {index + 1}/{total_pages})",
                desc=f"**{total} result(s)**\n\n{pages[index]}"
            )

        pager = Pager(pages, build)
        await interaction.response.send_message(embed=pager.current_embed(), view=pager)

    else:  # vua
        results = []
        for year, cases in VUA_DATA.items():
            for c in cases:
                haystack = f"{c['name']} {c.get('creator', '')}".lower()
                if q in haystack:
                    results.append((year, c))

        if not results:
            await interaction.response.send_message(
                f"No VUA cases matched **\"{query}\"**.", ephemeral=True
            )
            return

        lines = [f"[{year}] {case_to_str(c, show_creator=True)}" for year, c in results]
        pages = chunk_lines(lines)
        total = len(results)

        def build(index: int, total_pages: int) -> discord.Embed:
            return vua_embed(
                title=f"VUA Search — \"{query}\"  (page {index + 1}/{total_pages})",
                desc=f"**{total} result(s)**\n\n{pages[index]}"
            )

        pager = Pager(pages, build)
        await interaction.response.send_message(embed=pager.current_embed(), view=pager)


# ──────────────────────────────────────────────
#  ENTRY POINT
# ──────────────────────────────────────────────
if __name__ == "__main__":
    bot.run(BOT_TOKEN)
