export const TOKENS = {
  color: {
    paper:      '#F3EFE6',  // app ground: warm cream, NOT white
    surface:    '#FDFCF8',  // cards
    raised:     '#ECE7DB',  // hover / active tab / table header
    line:       '#E1DAC9',  // 1px hairline
    lineStrong: '#C8C0AC',  // emphasized border
    ink:        '#191712',  // primary text (warm near-black)
    ink2:       '#57534A',  // secondary text
    ink3:       '#6F6A5C',  // micro-labels (must pass 4.5:1 on paper)
    ochre:      '#C25E00',  // PRIMARY accent: burnt saffron (brand, links, focus, p50)
    ochreDeep:  '#8A4B00',  // ochre for small text
    ochreWash:  'rgba(194, 94, 0, 0.10)',
    clear:      '#1B6B3A',  // aspect green: on-time <5m
    caution:    '#B87400',  // aspect amber: 5-20m delay
    restrict:   '#B3362B',  // aspect brick: >20m / conflict
    graphite:   '#4A453D',  // uncertainty bands (use 12% alpha fills)
    // kiosk world (only /kiosk):
    kioskBg:    '#000000',
    kioskGold:  '#FFD700',
    kioskText:  '#FFFFFF',
    // landing world (only /: ported dark palette):
    nightBg0:   '#0A0B0D',
    nightBg1:   '#101216',
    nightLine:  '#23272F',
    nightAmber: '#F5A524',
    nightGreen: '#3DDC97',
    nightRed:   '#F4506A',
  },
  font: {
    display: '"Fraunces", Georgia, serif',
    sans: '"Instrument Sans", system-ui, sans-serif',
    mono: '"IBM Plex Mono", monospace',
    hindi: '"Noto Sans Devanagari", sans-serif',
  },
  // STRICT 6-step scale, nothing between:
  scale: { micro: '11px', caption: '13px', body: '15px', subhead: '20px', headline: '32px', hero: '60px' },
  radius: { sm: '2px', md: '4px' },   // flat, print-like. NO large radii.
  space: 4,                           // 4px grid
} as const;

export type Tokens = typeof TOKENS;
