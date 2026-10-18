// Core Clinical Atlas values shared by the app theme, CSS and asset renderer.
export const ATLAS_TOKENS = Object.freeze({
  paper: '#f8f9f5', surface: '#ffffff', wash: '#f1f3ee',
  ink: '#202d27', green: '#245747', muted: '#65716a', line: '#dde3da',
  primaryLight: '#57816d', primaryDark: '#173c30',
  accent: '#a2b99f', accentLight: '#dce7d7', accentDark: '#647e61', accentInk: '#18382d',
  success: '#427158', successLight: '#dce8db', successDark: '#24513a',
  sans: '"Noto Sans TC", "Microsoft JhengHei", "Segoe UI", sans-serif',
  serif: '"Iowan Old Style", "Palatino Linotype", "Noto Serif TC", serif',
});

export const ATLAS_CSS_VARIABLES = Object.freeze(Object.fromEntries(
  ['paper', 'surface', 'wash', 'ink', 'green', 'muted', 'line', 'sans', 'serif', 'success']
    .map(key => [`--atlas-${key}`, ATLAS_TOKENS[key]]),
));
