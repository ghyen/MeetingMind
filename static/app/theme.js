// MeetingMind Dark Theme — Toss Blue, Pretendard, Fixed
// One theme object. No tweaks, no light mode.

const THEME = {
  bg: '#121417',
  bgElevated: '#191B1F',
  surface: '#1E2127',
  surfaceAlt: '#252932',
  surfaceMuted: '#181A1F',
  border: 'rgba(255, 255, 255, 0.08)',
  borderStrong: 'rgba(255, 255, 255, 0.14)',
  divider: 'rgba(255, 255, 255, 0.06)',

  text: '#F2F4F6',
  text2: '#B0B8C1',
  text3: '#8B95A1',
  text4: '#6B7684',

  accent: '#3182F6',         // 토스 블루
  accentHover: '#4A94FF',
  accentSoft: 'rgba(49, 130, 246, 0.14)',
  accentSoftStrong: 'rgba(49, 130, 246, 0.24)',

  speakerA: '#3182F6',
  speakerB: '#FF7E36',
  speakerC: '#12B886',
  speakerD: '#845EF7',

  positive: '#00C471',
  positiveSoft: 'rgba(0, 196, 113, 0.14)',
  warning: '#FFB800',
  warningSoft: 'rgba(255, 184, 0, 0.14)',
  danger: '#F04438',
  dangerSoft: 'rgba(240, 68, 56, 0.14)',

  shadow: '0 1px 2px rgba(0, 0, 0, 0.24)',
  shadowCard: '0 8px 24px rgba(0, 0, 0, 0.32)',
  shadowLifted: '0 16px 48px rgba(0, 0, 0, 0.4)',
};

const TYPE = {
  xs: 11, sm: 13, base: 14, md: 15, lg: 17, xl: 20, '2xl': 24, '3xl': 32, '4xl': 40, '5xl': 56,
};

const LIGHT_THEME = {
  bg: '#F7F8FA',
  bgElevated: '#FFFFFF',
  surface: '#FFFFFF',
  surfaceAlt: '#F2F4F6',
  surfaceMuted: '#F7F8FA',
  border: 'rgba(0, 0, 0, 0.08)',
  borderStrong: 'rgba(0, 0, 0, 0.14)',
  divider: 'rgba(0, 0, 0, 0.06)',
  text: '#191F28',
  text2: '#4E5968',
  text3: '#8B95A1',
  text4: '#B0B8C1',
  accent: '#3182F6',
  accentHover: '#1B64DA',
  accentSoft: 'rgba(49, 130, 246, 0.10)',
  accentSoftStrong: 'rgba(49, 130, 246, 0.18)',
  speakerA: '#3182F6',
  speakerB: '#FF7E36',
  speakerC: '#12B886',
  speakerD: '#845EF7',
  positive: '#00A060',
  positiveSoft: 'rgba(0, 160, 96, 0.10)',
  warning: '#E08B00',
  warningSoft: 'rgba(224, 139, 0, 0.10)',
  danger: '#E53E3E',
  dangerSoft: 'rgba(229, 62, 62, 0.10)',
  shadow: '0 1px 2px rgba(0, 0, 0, 0.08)',
  shadowCard: '0 4px 16px rgba(0, 0, 0, 0.10)',
  shadowLifted: '0 8px 32px rgba(0, 0, 0, 0.14)',
};

function buildCss(themeObj) {
  const css = {};
  for (const [k, v] of Object.entries(themeObj)) {
    const kebab = k.replace(/[A-Z]/g, (m) => '-' + m.toLowerCase());
    css[`--${kebab}`] = v;
  }
  for (const [k, v] of Object.entries(TYPE)) {
    css[`--fs-${k}`] = v + 'px';
  }
  css['--font'] = '"Pretendard Variable", Pretendard, -apple-system, BlinkMacSystemFont, sans-serif';
  return css;
}

function applyDarkTheme() { return buildCss(THEME); }
function applyLightTheme() { return buildCss(LIGHT_THEME); }

function speakerColor(s) { return `var(--speaker-${(s || 'A').toLowerCase().charAt(s ? s.length - 1 : 0)})`; }
function speakerColorResolved(s) {
  const letter = (s || 'A').toLowerCase().charAt(s ? s.length - 1 : 0);
  return THEME[`speaker${letter.toUpperCase()}`] || THEME.speakerA;
}
function speakerLetter(s) {
  // "Speaker 1" → "1"; "A" → "A"
  if (!s) return '?';
  if (s.length === 1) return s.toUpperCase();
  const m = s.match(/(\d+)/);
  if (m) return String.fromCharCode(64 + parseInt(m[1])); // 1→A
  return s[0].toUpperCase();
}

window.MM = window.MM || {};
window.MM.THEME = THEME;
window.MM.LIGHT_THEME = LIGHT_THEME;
window.MM.applyDarkTheme = applyDarkTheme;
window.MM.applyLightTheme = applyLightTheme;
window.MM.speakerColor = speakerColor;
window.MM.speakerColorResolved = speakerColorResolved;
window.MM.speakerLetter = speakerLetter;
