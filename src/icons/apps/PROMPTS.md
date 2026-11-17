# App icon provenance

Generated with Codex image tools, not drawn by hand. Earlier sheets used the
Codex CLI image tool (`~/.claude/skills/codex-image-gen`); individual entries
below identify the tool and source. `tools/slice_sheet.py` cuts sheets into
512 px icons; standalone generated PNGs can retain their original size.
`build.py` scales the icon theme assets to 16–256 px and maps them to icon names (`ICONS`).

## nalamint-dictation.png

- Tool: Codex built-in image generation, transparent background.
- Source: `~/.codex/generated_images/01a1eb6c-b699-7d61-bcd7-8ee82328a402/exec-51cb98c7-26ac-4f82-9067-c858c82676e0.png`.
- Style reference: `terminal.png`. Resized from 1254×1254 to 512×512 with alpha intact.

> Generate one original NalaMint Linux desktop app icon for NalaMint Dictation. Input image is a style reference only for the squircle geometry, bevel and lighting, never repeat its terminal symbol. Isolated single centered rounded-square tile, same approximately 91% canvas footprint and even transparent padding, slight top edge highlight and restrained depth. Deep evergreen-to-dark-teal tile. Center one bold pale mint microphone capsule with a clean U-shaped cradle and short stem. Flank it with a single short pair of vertical audio marks on each side, subordinate to the microphone, crisp enough to read at 24px. Straight-on perspective, balanced, simple, NalaMint app icon family. Real transparent alpha outside tile. No lettering, border frame, scene, logo, branding, watermark, or additional icons.

## app-icons-sheet-v1.png → settings, software, update, terminal, text-editor, calculator, system-monitor, files

- Date: 2026-11-13
- Codex source: `~/.codex/generated_images/01a1d64c-efdf-73f2-9d9a-2307c0870a76/exec-cf5f6275-e491-40fa-918c-af8129c9808c.png`
- Output: 1254×1254 RGBA, transparent background
- Sliced with: `tools/slice_sheet.py src/icons/apps/app-icons-sheet-v1.png 3 3 settings software update terminal text-editor calculator system-monitor files -`

Prompt:

```
Use case: a set of 8 desktop application icons for an open-source Linux icon theme called NalaMint, styled like modern macOS (Big Sur and later) app icons. Original designs only: do not copy any Apple icon, no Apple logo, no brand logos, no text or letters.

Canvas: 1024x1024 PNG with a fully transparent background (real alpha channel, no checkerboard, no backdrop, no floor shadow). Lay the icons out in a 3x3 grid of equal cells (about 341x341 px each). Fill the first 8 cells in reading order (left to right, top to bottom); leave the 9th cell (bottom right) completely empty and transparent. Center each icon in its cell with about 40 px of transparent padding on every side. Icons must not touch or overlap.

Shared style: each icon is a rounded square ("squircle", continuous corners) seen straight on, same size in every cell, with soft vertical gradients, gentle top lighting, a subtle inner edge and a very soft short drop shadow. Clean, polished, flat-ish 3D, consistent lighting and palette across all 8.

Cells, in order:
1. System Settings: light silver-grey squircle with a large dark graphite gear in the center.
2. Software Manager: bright blue gradient squircle with a white shopping bag carrying a small downward arrow.
3. Update Manager: green gradient squircle with two white circular refresh arrows forming a loop around a small white shield.
4. Terminal: near-black squircle with a white command prompt made only of a right-pointing chevron and an underscore, in the upper left.
5. Text Editor: white paper squircle with faint grey ruled lines and a yellow pencil lying diagonally.
6. Calculator: dark graphite squircle with a 4x4 grid of round keys; the right column of keys is orange, the top row light grey, the rest dark grey; no digits.
7. System Monitor: black squircle with a glowing green line graph over a faint grid.
8. Files (file manager): light blue gradient squircle with a white folder in the center.

Avoid: text, letters, digits, watermarks, Apple logo, borders around cells, grid lines, background color.
```

## app-icons-sheet2-v1.png → document-viewer, image-viewer, media-player, archive-manager, backup, snapshots, drivers, sources, system-info, file-transfer, notes, screenshot, disks, disk-usage, calendar, web-apps, printers, passwords, scanner, renamer

- Date: 2026-11-13
- Codex source: `~/.codex/generated_images/01a1d65d-ee2b-75e3-8ae6-7928876c36bf/exec-793cda73-3c80-4e78-9ad6-dbfbda86d67c.png`
- Reference passed with `--ref`: `app-icons-sheet-v1.png` (style only)
- Output: 1402×1122 RGBA. Icons drifted across the equal-cell grid, so they
  were found by shape instead.
- Sliced with: `tools/slice_sheet.py src/icons/apps/app-icons-sheet2-v1.png 5 4 document-viewer image-viewer media-player archive-manager backup snapshots drivers sources system-info file-transfer notes screenshot disks disk-usage calendar web-apps printers passwords scanner renamer --blobs`
- Apps with their own logos (Firefox, Thunderbird, LibreOffice, Rhythmbox,
  Transmission) were left out on purpose. Snapshots (Timeshift) uses layered
  sheets rather than a clock, to stay clear of Apple's Time Machine icon.

Prompt:

```
Use case: 20 more desktop application icons for the same open-source Linux icon theme (NalaMint). The attached image is the existing icon set: match its style exactly (rounded-square "squircle" shape with continuous corners, same size, soft vertical gradients, gentle top lighting, subtle inner edge, very soft short drop shadow, clean flat-ish 3D polish, same palette family). Do not reproduce the attached icons themselves. Original designs only: do not copy any Apple or other vendor icon, no logos, no text, letters or digits.

Canvas: 1500x1200 PNG with a fully transparent background (real alpha channel, no checkerboard, no backdrop). Lay the icons out in a 5-column x 4-row grid of equal cells (300x300 px each). Fill all 20 cells in reading order (left to right, top to bottom). Center each icon in its cell with about 30 px of transparent padding on every side. Icons must not touch or overlap.

Cells, in order:
1. Document Viewer: white squircle with a page of grey text lines and a small red bookmark ribbon at the top right corner of the page.
2. Image Viewer: sky-blue squircle with a white photo frame showing a simple mountain and sun.
3. Media Player: deep purple-to-violet gradient squircle with a large white rounded play triangle.
4. Archive Manager: warm brown squircle with a light cardboard box with a zipper running down its front.
5. Backup Tool: teal squircle with a white external drive and a circular arrow wrapping around it.
6. Snapshots (Timeshift): dark slate squircle with three stacked, offset translucent rounded sheets (layers) glowing blue; no clock.
7. Driver Manager: dark green squircle with a silver computer chip with pins.
8. Software Sources: indigo squircle with a white globe behind a small stacked server.
9. System Information: light grey squircle with a white clipboard holding a checklist with green check marks.
10. File Transfer (Warpinator): bright cyan squircle with two white curved arrows passing each other in opposite directions.
11. Notes: bright yellow squircle with a slightly curled lighter-yellow sticky note.
12. Screenshot: dark charcoal squircle with white viewfinder corner brackets around a small camera lens.
13. Disks: light silver squircle with a dark grey hard drive seen at a slight angle with a small green light.
14. Disk Usage: white squircle with a colorful ring chart (blue, orange, green, purple segments).
15. Calendar: white squircle with a calendar page: red top band with two binder rings, and a grid of small grey dots for days (no numbers).
16. Web Apps: blue gradient squircle with a white browser window outline containing a small globe.
17. Printers: light grey squircle with a white printer and a sheet of paper coming out.
18. Passwords and Keys: golden-amber squircle with a silver key over a small keyhole shield.
19. Document Scanner: light blue squircle with a flatbed scanner with a glowing scan line.
20. File Renamer: soft orange squircle with two overlapping white document cards and a small pencil.

Avoid: text, letters, digits, watermarks, logos, borders around cells, grid lines, background color.
```

## settings-icons-sheet1-v1.png → System Settings pages

- Date: 2026-11-13
- Codex source: `~/.codex/generated_images/01a1d6c1-a651-7710-8fd5-b439717e9a8a/exec-85fcd63f-48da-4e7a-a738-26acecaae819.png`
- References passed with `--ref`: `app-icons-sheet-v1.png`, `app-icons-sheet2-v1.png` (style only)
- Output: 1402×1122 RGBA, transparent background
- Sliced with: `tools/slice_sheet.py src/icons/apps/settings-icons-sheet1-v1.png 5 4 cs-backgrounds cs-desktop-effects cs-fonts cs-themes cs-universal-access cs-user cs-actions cs-applets cs-date-time cs-desklets cs-desktop cs-extensions cs-general cs-gestures cs-overview input-method languages cs-nightlight cs-notifications online-accounts --blobs`

Prompt:

```
Use case: 20 System Settings panel icons for the same open-source Linux icon theme (NalaMint). The two attached images are the existing icon set: match their style exactly (rounded-square "squircle" shape with continuous corners, same size, soft vertical gradients, gentle top lighting, subtle inner edge, very soft short drop shadow, clean flat-ish 3D polish, same palette family). Do not reproduce the attached icons themselves. Original designs only: do not copy any Apple or other vendor icon (especially not macOS System Settings icons), no logos, no text, letters or digits. Each symbol should be simple and bold so it still reads at 32 px.

Canvas: 1500x1200 PNG with a fully transparent background (real alpha channel, no checkerboard, no backdrop). Lay the icons out in a 5-column x 4-row grid of equal cells (300x300 px each). Fill all 20 cells in reading order (left to right, top to bottom). Center each icon in its cell with about 30 px of transparent padding on every side. Icons must not touch or overlap.

Cells, in order:
1. Backgrounds: sky-blue squircle with two overlapping white-framed wallpaper cards showing soft abstract waves (one blue-teal, one pink-orange). No sun, no mountains.
2. Effects: violet squircle with a small white window card leaving a trail of fading translucent copies, with a few white sparkles.
3. Font Selection: cream-white squircle with a black fountain-pen nib drawing a flowing dark calligraphic swirl (decorative curl only, not a letter).
4. Themes: soft pink squircle with a light wooden painter's palette with paint dots (red, yellow, green, blue, purple) and a small brush.
5. Accessibility: deep teal squircle with a white ring containing a simple standing human figure with arms and legs spread.
6. Account details: steel-blue squircle with a white ID card showing a round person silhouette and two grey text lines.
7. Actions: orange squircle with a small white context-menu list (three rows) and a yellow lightning bolt over its corner.
8. Applets: light grey squircle with a small screen whose bottom bar holds four tiny colored widgets (blue, green, orange, purple).
9. Date & Time: white squircle with a round clock face with tick marks and two dark hands, no digits.
10. Desklets: mint-green squircle with two small white widget cards pinned on a desktop: a mini analog clock and a mini cloud-and-sun weather card.
11. Desktop: blue gradient squircle with a white-framed screen showing a calm gradient desktop with a column of three small blue folder shapes.
12. Extensions: bright green squircle with a single white jigsaw puzzle piece.
13. General: light grey squircle with two white rounded toggle switches stacked: the top one on (green), the bottom one off (grey).
14. Gestures: dark charcoal squircle with a silver trackpad and two white fingertip dots with a curved swipe arrow.
15. Hot Corners: indigo squircle with a white screen outline whose top-left corner glows bright cyan, with a small arrow pointing into that corner.
16. Input Method: light silver squircle with a large white keyboard key cap that has a small blue globe on its face.
17. Languages: royal-blue squircle with two overlapping speech bubbles (one white, one pale blue) with a small globe in the front bubble.
18. Night Light: deep navy squircle with a warm glowing amber crescent moon and three small stars.
19. Notifications: red squircle with a white bell and a small orange badge dot at its top right.
20. Online Accounts: cyan squircle with a white cloud and a small round person badge at its lower right.

Avoid: text, letters, digits, watermarks, logos, borders around cells, grid lines, background color.
```

## settings-icons-sheet2-v1.png → System Settings pages

- Date: 2026-11-13
- Codex source: `~/.codex/generated_images/01a1d6c1-a666-7082-96eb-28f5461c0ad2/exec-1bb6a70e-2158-43dc-8776-a2b0ece06cca.png`
- References passed with `--ref`: `app-icons-sheet-v1.png`, `app-icons-sheet2-v1.png` (style only)
- Output: 1402×1122 RGBA, transparent background
- Sliced with: `tools/slice_sheet.py src/icons/apps/settings-icons-sheet2-v1.png 5 4 cs-panel cs-default-applications cs-privacy cs-screensaver cs-startup-programs cs-windows cs-workspaces bluetooth cs-color cs-display cs-tablet cs-keyboard cs-mouse cs-network cs-power cs-sound cs-thunderbolt firewall login-window users --blobs`

Prompt:

```
Use case: 20 more System Settings panel icons for the same open-source Linux icon theme (NalaMint). The two attached images are the existing icon set: match their style exactly (rounded-square "squircle" shape with continuous corners, same size, soft vertical gradients, gentle top lighting, subtle inner edge, very soft short drop shadow, clean flat-ish 3D polish, same palette family). Do not reproduce the attached icons themselves. Original designs only: do not copy any Apple or other vendor icon (especially not macOS System Settings icons), no brand logos, no text, letters or digits. Each symbol should be simple and bold so it still reads at 32 px.

Canvas: 1500x1200 PNG with a fully transparent background (real alpha channel, no checkerboard, no backdrop). Lay the icons out in a 5-column x 4-row grid of equal cells (300x300 px each). Fill all 20 cells in reading order (left to right, top to bottom). Center each icon in its cell with about 30 px of transparent padding on every side. Icons must not touch or overlap.

Cells, in order:
1. Panel: dark slate squircle with a small screen showing a blue gradient desktop and a frosted translucent bar along its top edge.
2. Preferred Applications: golden-orange squircle with a 2x2 grid of small colored rounded app tiles (blue, green, red, purple) and a white star badge over them.
3. Privacy: deep purple squircle with a white eye crossed by a diagonal slash.
4. Screensaver: midnight-indigo squircle with a dark starry screen and a white padlock in front of it.
5. Startup Applications: coral squircle with a white rocket lifting off diagonally with a small orange flame.
6. Windows: magenta-purple squircle with two overlapping white app windows with plain title bars (no colored dots).
7. Workspaces: blue squircle with a 2x2 grid of white rounded screen tiles, the top-left one tinted bright cyan.
8. Bluetooth: bright blue squircle with the standard white angular Bluetooth rune symbol.
9. Color: white squircle with three overlapping translucent circles (red, green, blue) mixing toward white in the center.
10. Display: sky-blue squircle with two white monitors on stands side by side, with blue gradient screens.
11. Graphics Tablet: charcoal squircle with a black drawing tablet and a white stylus drawing a blue curved stroke on it.
12. Keyboard: light grey squircle with a white keyboard seen from slightly above, rows of blank keys.
13. Mouse and Touchpad: soft blue-grey squircle with a white computer mouse with a scroll wheel, next to a small silver touchpad.
14. Network: teal-blue squircle with a white Wi-Fi symbol (three arcs over a dot).
15. Power Management: green squircle with a white battery containing a yellow lightning bolt.
16. Sound: pink-red squircle with a white speaker with sound waves.
17. Thunderbolt: dark navy squircle with a white cable plug and a small yellow lightning bolt beside it (no logo).
18. Firewall: orange-red squircle with a red-brown brick wall and a white shield in front of it.
19. Login Window: indigo squircle with a white login card showing a round avatar and a password field of dots.
20. Users and Groups: teal squircle with three white person silhouettes, the middle one in front.

Avoid: text, letters, digits, watermarks, logos, borders around cells, grid lines, background color.
```

## Launchpad dock icon (`launchpad-source-v1.png`)

- Codex source: `~/.codex/generated_images/01a1d6d2-e7ba-7b92-a3b8-0e494e048af3/exec-b53111da-12f1-4a3d-84b6-0c6bb3505b7d.png`
- Reference passed with `--ref`: `app-icons-sheet2-v1.png` (style only)
- Output: 1254×1254 RGBA, one icon. Cut with `tools/slice_sheet.py src/icons/apps/launchpad-source-v1.png 1 1 launchpad`
- Installed as `nalamint-launchpad` (the nalamint-launchpad applet's default icon).
  White tiles on violet, kept away from Apple's multicolored Launchpad grid.

Prompt:

```
Use case: one desktop application icon for the same open-source Linux icon theme (NalaMint). It is the dock icon for "Launchpad", the full-screen launcher that shows every installed app in a grid. The attached image is the existing icon set: match its style exactly (rounded-square "squircle" shape with continuous corners, soft vertical gradient, gentle top lighting, subtle inner edge, very soft short drop shadow, clean flat-ish 3D polish, same palette family). Do not reproduce any of the attached icons.

Design: a deep indigo-to-violet gradient squircle. On it, a 3x3 grid of nine identical soft white rounded squares with small gaps, evenly spaced and centered, with a faint glow, suggesting "all apps". Original design only: no rocket, no multicolored tiles, do not copy Apple's Launchpad icon or any other vendor icon. No text, letters, digits or logos.

Canvas: 1024x1024 PNG with a fully transparent background (real alpha channel, no checkerboard, no backdrop). One icon, centered, with about 90 px of transparent padding on every side.

Avoid: text, letters, digits, watermarks, logos, borders, background color, extra objects.
```

## Sheet 3 (`app-icons-sheet3-v1.png`): remaining Mint apps + System Settings section headers

- Codex source: `~/.codex/generated_images/01a1d6e8-f4b5-7c90-9b71-f18788207410/exec-83020098-cf4c-44eb-af54-f69a5bcf7b24.png`
- References passed with `--ref`: `app-icons-sheet2-v1.png`, `settings-icons-sheet1-v1.png` (style only)
- Output: 1254×1254 RGBA, 4×4.
- Sliced with: `tools/slice_sheet.py src/icons/apps/app-icons-sheet3-v1.png 4 4 fingerprints system-admin network-config character-map power-stats onscreen-keyboard usb-writer welcome library photos tv theme-settings cat-appearance cat-prefs cat-hardware cat-admin --blobs`
- NVIDIA X Server Settings keeps its own icon (brand logo).

Prompt:

```
Use case: 16 more desktop icons for the same open-source Linux icon theme (NalaMint). The two attached images are the existing icon set: match their style exactly (rounded-square "squircle" shape with continuous corners, same size, soft vertical gradients, gentle top lighting, subtle inner edge, very soft short drop shadow, clean flat-ish 3D polish, same palette family). Do not reproduce the attached icons themselves; every new icon must look different from them. Original designs only: do not copy any Apple or other vendor icon, no logos, no text, letters or digits.

Canvas: 1200x1200 PNG with a fully transparent background (real alpha channel, no checkerboard, no backdrop). Lay the icons out in a 4-column x 4-row grid of equal cells (300x300 px each). Fill all 16 cells in reading order (left to right, top to bottom). Center each icon in its cell with about 30 px of transparent padding on every side. Icons must stay inside their own cell and must not touch or overlap.

Cells, in order:
1. Fingerprints: teal squircle with a white fingerprint made of concentric curved ridges.
2. System Administration: dark slate squircle with a white wrench crossed over a small gear.
3. Advanced Network Configuration: blue squircle with three white circular nodes joined by lines in a triangle.
4. Character Map: white squircle with a light card holding a 3x3 grid of small simple symbols (star, heart, music note, check mark, arrow, infinity sign, circle, triangle, smiley); no letters or digits.
5. Power Statistics: lime-green squircle with a white battery outline with a small rising line chart inside it.
6. On-screen Keyboard: soft lavender squircle with a white floating keyboard and a fingertip pressing one key.
7. USB Image Writer: orange squircle with a white USB flash drive and a small downward arrow writing into it.
8. Welcome Screen: warm yellow-orange squircle with a white waving hand and two small motion lines.
9. Library: brown-wood squircle with a row of four colorful book spines standing on a shelf.
10. Photos: green squircle with a fanned stack of three white-bordered photos, the top one showing a sunset.
11. TV: deep red squircle with a white flat-screen TV on a small stand, its screen a blue-to-purple gradient.
12. Theme Settings: light grey squircle with two overlapping app windows, one tinted blue, and a small paint roller.
13. Appearance (category): magenta-to-orange gradient squircle with a single white paint drop.
14. Preferences (category): blue squircle with three white horizontal slider controls at different positions.
15. Hardware (category): green squircle with a white desktop computer: monitor on a stand and a keyboard.
16. Administration (category): maroon squircle with a white shield with a small gear inside it.

Avoid: text, letters, digits, watermarks, logos, borders around cells, grid lines, background color.
```
