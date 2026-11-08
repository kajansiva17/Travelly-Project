# Approved public landing artwork — 7 November 2026

## Legacy asset provenance — superseded implementation

The crop-based implementation described below was rejected and superseded by the standalone PNG correction. Only the narrow garden-edge crops remain in use, with soft edge masks. Hero, card and logo screenshot crops are deprecated; do not restore fragment stitching or flattened logo backgrounds. Current production scenes and branding are in the sibling `landing-scenes-2026-11-07` and `branding/approved-2026-11-07` directories. The remainder of this document preserves historical provenance.

Mapping confirmed by the user: coastal reference = Home; tea-estate Driver reference = For Drivers; transport-depot reference = For Owners.

These are clean crops of the supplied artwork, not newly generated replacements. The byte-identical complete references live separately in `/references/landing-2026-11-07/`; no complete reference is displayed as a webpage. `provenance.json` records the reference and exact crop rectangle for each PNG. The extraction script is `.tools/landing-reference-2026-11-07/prepare_assets.py` at the project root.

- Card PNGs contain only the approved photo/illustration area. Actual card labels, descriptions, icons and actions are React/HTML. Text on a photographed phone, calendar or depot sign is part of that approved photograph, not a substitute for an interactive HTML card.
- Hero rectangles contain no page headings, buttons or fields. CSS positions the rectangles and blends exposed edges into sky/fog gradients. Adjacent clean rectangles preserve the source scene; obscured scenery is unavailable. Mobile uses a clean hero-photo crop with normal responsive framing.
- Garden strips come from outside the FAQ and call-to-action panels. Their center panorama is unavailable.
- Logo crops retain the flattened light background. CSS blending reduces its visibility; these are not transparent original logos.

Required for a closer match: the full text-free coastal, Driver tea-estate and Owner depot hero scenes; their complete lower scenery panoramas; transparent standard and PUBLIC DRIVER Travelly logo artwork; the verified screenshot UI font files/licence and original icon set. No unrelated stock image, AI regeneration or invented logo is used.
