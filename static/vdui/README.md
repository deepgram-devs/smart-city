# Deepgram brand UI kit assets

Copied from [`deepgram-devs/dg-brand-ui`](https://github.com/deepgram-devs/dg-brand-ui) **v0.6.0** (`assets/`). This app has no build step, so the files are committed here and served by Flask from `/static/vdui/`.

| File | What it is |
| --- | --- |
| `brand.css` | The kit's theme as plain CSS: tokens, fonts, and the `label`, `glass`, and `stage-glow` utilities |
| `textures/stage.webp` | The violet texture behind `stage-glow` (loaded by `brand.css`) |
| `ring-element/deepgram-voice-ring.js` | The voice ring as a `<deepgram-voice-ring>` Web Component |
| `logos/deepgram.svg`, `logos/deepgram-favicon.svg` | The Deepgram logo and favicon |

Don't edit these files. To upgrade, copy the same files from the kit's `assets/` folder at the new tag, then update the version above.
