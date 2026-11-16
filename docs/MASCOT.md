# Mascot sprites

The BlowMyJob mascot (the suitcase blowing a heart) appears in several places. Each place has its own
sprite name, so the artist can draw a different pose for each of them.

**How to add a sprite:** put a file named `<name>.png` (also `.webp`, `.svg` or `.gif`) into
`web/app/static/mascot/`. It is picked up automatically. Until a sprite exists, `default.png` is used,
so nothing breaks. Use transparent backgrounds, square images, at least 256×256 px.

| Sprite name | Where it is used | Shown at |
|---|---|---|
| `default` | fallback for every missing sprite | n/a |
| `tab` | Profile tab in the bottom menu (grey when inactive, in colour when active) | 30 px |
| `avatar` | round avatar on the profile card | 74 px |
| `hello` | onboarding, above the CV upload | 96 px |
| `thinking` | while the CV is being analysed (bobs up and down) | 56 px |
| `blow` | pops up from the bottom on a like, together with the confetti | 120 px |
| `caught-up` | empty feed: "You're all caught up" | 112 px |
| `sad` | no saved jobs, no skills match, insights unavailable | 40–72 px |
| `peek` | peeks out from behind the top-left edge of the median-salary card on Insights | 84 px |
| `peek-close` | peeks out above the close button of the "Full description" sheet | 68 px |
| `splash` | short splash on the first page load of a browser tab session | 150 px |
| `error` | 404 page | 140 px |

The helper lives in `web/app/mascot.py` (`mascot_url(name)`) and the template macro in
`web/app/templates/_mascot.html` (`{{ mascot('sad', 72) }}`).
