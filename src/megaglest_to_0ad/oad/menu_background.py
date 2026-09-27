"""Main-menu background emission (MegaGlest loading screen -> 0 A.D. GUI).

0 A.D. has no per-civ loading screen: the pregame page is generic, and its
background layer set is picked at random by ``pickRandom`` in
``gui/pregame/MainMenuPage.js``. The pack's loading screen is the only large
per-civ illustration it ships, so it is emitted as a main-menu background.

Registration is additive. Since 0.28 the pregame page loads
``gui/pregame/mainmenu.js`` as an ES module instead of scanning the whole
``gui/pregame/`` directory, so a plain sibling script is never evaluated. The
supported extension point is a ``~<mod>.append.js`` file, which the GUI loader
appends into the ``mainmenu`` module. ``backgrounds`` is already imported
there, so the layer set registers without shadowing any stock file.
"""

from __future__ import annotations

from pathlib import Path

from lxml import etree

from ..converters.texture_converter import TextureConverter
from ..core.errors import ConversionError
from ..megaglest.civ_loader import Faction
from .common import write_xml

TEXTURE_DIR = "art/textures/ui/pregame/backgrounds"
GUI_DIR = "gui/pregame/backgrounds"

_APPEND_JS = """\
// Registers this mod's main-menu background with the pregame page.
//
// 0.28 loads gui/pregame/mainmenu.js as an ES module rather than scanning
// gui/pregame/, so a plain sibling script is never evaluated. A
// ~<mod>.append.js file is appended into that module instead, which leaves
// the stock background.js untouched. `backgrounds` is mainmenu.js's own
// import, so the layer set registers without shadowing anything.
//
// Selection is random across every registered set (pickRandom in
// MainMenuPage.js), so this shares the menu with the stock backgrounds.
backgrounds["{civ}"] = [
  {{
    "offset": (time, width) => 0.02 * width * Math.cos(0.05 * time),
    "sprite": "background-{civ}1-1",
    "tiling": false,
  }},
];
"""


def write_menu_background(
    faction: Faction,
    mod_dir: Path,
    civ: str,
    converter: TextureConverter,
    warnings: list[str],
) -> Path | None:
    """Convert the faction's loading screen into a main-menu background.

    Returns the written PNG, or ``None`` when the pack ships no loading screen
    or the image cannot be read. A missing screen is a warning, not a failure:
    most packs have none and the menu simply keeps the stock backgrounds.

    The image goes through the shared ``TextureConverter``, so it lands as an
    RGBA, power-of-two PNG like every other converted texture rather than a
    copy 0 A.D.'s archive builder would warn about and rescale.
    """
    source = faction.loading_screen
    if source is None or not source.is_file():
        warnings.append(f"{civ}: no loading screen found; menu background skipped")
        return None

    texture = mod_dir / TEXTURE_DIR / f"{civ}1_1.png"
    try:
        converter.convert_to_png(source, texture)
    except ConversionError as exc:
        warnings.append(f"{civ}: menu background: {exc}")
        return None

    _write_sprite(mod_dir, civ)
    _write_textures_xml(texture.parent)
    _write_append_js(mod_dir, civ)
    return texture


def _write_sprite(mod_dir: Path, civ: str) -> None:
    """Declare the background sprite for ``gui/pregame/backgrounds/``.

    ``page_pregame.xml`` includes that directory wholesale, so a new file here
    is picked up without editing any stock XML. The texture ref resolves
    against ``art/textures/ui/``, matching the stock background sets.
    """
    root = etree.Element("sprites")
    sprite = etree.SubElement(root, "sprite", name=f"background-{civ}1-1")
    etree.SubElement(
        sprite,
        "image",
        texture=f"pregame/backgrounds/{civ}1_1.png",
        round_coordinates="false",
        wrap_mode="clamp_to_edge",
    )
    path = mod_dir / GUI_DIR / f"{civ}.xml"
    path.parent.mkdir(parents=True, exist_ok=True)
    write_xml(path, root)


def _write_textures_xml(directory: Path) -> None:
    """Mirror the stock mipmap/alpha declaration for the background texture.

    Without it the full-screen background is minified unfiltered, which
    aliases badly at low resolutions.
    """
    root = etree.Element("Textures")
    etree.SubElement(root, "File", pattern="*", mipmap="true", alpha="transparency")
    write_xml(directory / "textures.xml", root)


def _write_append_js(mod_dir: Path, civ: str) -> None:
    """Emit ``gui/pregame/mainmenu~<mod>.append.js`` registering the layer set."""
    path = mod_dir / "gui/pregame" / f"mainmenu~{mod_dir.name}.append.js"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_APPEND_JS.format(civ=civ), encoding="utf-8")
