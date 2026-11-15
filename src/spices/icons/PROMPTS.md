# Spice icons

Icons for the Cinnamon Spices packages (`tools/spices.py`): applet/extension
`icon.png` and theme `icon.png`. Not part of the icon theme.

## `spice-icons-sheet-v1.png`

- Codex source: `~/.codex/generated_images/01a1d709-b91a-7ff2-ae07-690eb5bb1055/exec-0f73e8ed-2b3e-408f-8537-6bb889683dd6.png`
- Reference passed with `--ref`: `src/icons/apps/app-icons-sheet2-v1.png` (style only)
- Output: 1536×1024 RGBA, 3×2.
- Sliced with: `tools/slice_sheet.py src/spices/icons/spice-icons-sheet-v1.png 3 2 logo-menu app-name rounded-corners menubar-blur theme-light theme-dark --blobs --out src/spices/icons --size 256`
- Launchpad's spice icon is the dock icon, `src/icons/apps/launchpad.png`.

Prompt:

```
Use case: 6 icons for the add-ons of the same open-source Linux theme (NalaMint), shown in Linux Mint's System Settings lists and on its add-on website. The attached image is the existing icon set: match its style exactly (rounded-square "squircle" shape with continuous corners, same size, soft vertical gradients, gentle top lighting, subtle inner edge, very soft short drop shadow, clean flat-ish 3D polish, same palette family). Do not reproduce the attached icons. Original designs only: do not copy any Apple or other vendor icon, no logos, no text, letters or digits.

Canvas: 1200x800 PNG with a fully transparent background (real alpha channel, no checkerboard, no backdrop). Lay the icons out in a 3-column x 2-row grid of equal cells (400x400 px each). Fill all 6 cells in reading order. Center each icon in its cell with about 50 px of transparent padding on every side. Icons must stay inside their own cell and must not touch or overlap.

Cells, in order:
1. Logo Menu: slate-blue squircle with a white drop-down menu card (a short list of grey lines with one thin divider) hanging below a small white circle at the top left.
2. App Name: sky-blue squircle with a white bar across the top holding one thick dark rounded bar (a bold title placeholder, not text) and a small app window below it.
3. Rounded Corners: teal squircle with a white app window whose four corners are clearly rounded, with a small glowing arc highlighting the bottom right corner.
4. Menu-bar Blur: purple squircle with a soft colorful blurred landscape and a frosted translucent white strip across its top.
5. Light Theme: very light grey squircle with a light app window (white title bar with three small red, yellow and green dots) over a pastel blue-pink gradient.
6. Dark Theme: dark charcoal squircle with a dark app window (dark title bar with three small red, yellow and green dots) over a deep blue-violet gradient.

Avoid: text, letters, digits, watermarks, logos, borders around cells, grid lines, background color.
```
