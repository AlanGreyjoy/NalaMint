# Folder and trash icon provenance

Generated with the Codex CLI image tool (`~/.claude/skills/codex-image-gen`),
not drawn by hand. Replaced the earlier hand-made SVG folders and trash.

## places-sheet-v1.png → folder, documents, download, music, pictures, videos, templates, public, desktop, home, network, search, trash, trash-full

- Date: 2026-11-13
- Codex source: `~/.codex/generated_images/01a1d650-3e93-7b50-bd0b-2b88ee788133/exec-3c7df6c3-1aba-44de-86c8-5555922493ae.png`
- Reference passed with `--ref`: `src/icons/apps/app-icons-sheet-v1.png` (style only)
- Output: 1254×1254 RGBA. The transparent area holds alpha-1 specks (invisible;
  `slice_sheet.py --alpha-floor` clears them).
- Sliced with: `tools/slice_sheet.py src/icons/places/places-sheet-v1.png 4 4 folder documents download music pictures videos templates public desktop home network search trash trash-full - - --out src/icons/places --uniform`

Prompt:

```
Use case: folder and trash icons for an open-source Linux icon theme called NalaMint, styled like modern macOS (Big Sur and later) Finder folders. Original designs only: do not copy any Apple icon, no Apple logo, no brand logos, no text, letters or digits. The attached image is a style reference only (lighting, gradients, polish, soft shadow) from the same icon theme; do not reproduce its contents.

Canvas: 1536x1536 PNG with a fully transparent background (real alpha channel, no checkerboard, no backdrop, no floor shadow). Lay the icons out in a 4x4 grid of equal cells (384x384 px each). Fill the first 14 cells in reading order (left to right, top to bottom); leave the last 2 cells (row 4, columns 3 and 4) completely empty and transparent. Center each icon in its cell with about 40 px of transparent padding on every side. Icons must not touch or overlap.

Folders (cells 1-12): every folder is the same shape and size, seen straight on: a light sky-blue folder with a slightly darker back panel and tab at the top left, a white paper sheet peeking out between back and front, and a front panel with a soft vertical gradient and a subtle light top edge. Cells 2-12 have a simple symbol debossed into the center of the front panel in a slightly darker blue, like it is pressed into the material; the symbol is small (about 40% of the folder width) and clean. Cell 1 has no symbol.
1. plain folder, no symbol
2. Documents: a single page with a folded corner
3. Downloads: an arrow pointing down inside a circle
4. Music: a double eighth note
5. Pictures: a landscape photo frame with a mountain and sun
6. Videos: a play triangle inside a rounded rectangle
7. Templates: a page with a ruler
8. Public: a person silhouette (head and shoulders)
9. Desktop: a computer monitor on a stand
10. Home: a house
11. Network: a globe with meridians
12. Saved search: a magnifying glass

Trash (cells 13-14): a light grey, slightly translucent cylindrical waste bin with fine vertical ribs and a rounded rim, seen straight on, same height as the folders.
13. Trash empty
14. Trash full: the same bin with crumpled white paper sticking out of the top

Avoid: text, letters, digits, watermarks, Apple logo, borders around cells, grid lines, background color, perspective or tilt.
```
