import { createTheme } from '@mui/material/styles';
import { ATLAS_TOKENS as atlas, ATLAS_CSS_VARIABLES } from './designTokens.js';

const appTheme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: atlas.green,
      light: atlas.primaryLight,
      dark: atlas.primaryDark,
      contrastText: atlas.surface,
    },
    secondary: {
      main: atlas.accent,
      light: atlas.accentLight,
      dark: atlas.accentDark,
      contrastText: atlas.accentInk,
    },
    success: {
      main: atlas.success,
      light: atlas.successLight,
      dark: atlas.successDark,
    },
    background: {
      default: atlas.paper,
      paper: atlas.surface,
    },
    text: {
      primary: atlas.ink,
      secondary: atlas.muted,
    },
    divider: atlas.line,
  },
  typography: {
    fontFamily: atlas.sans,
    h1: { letterSpacing: 0, fontWeight: 650 },
    h2: { letterSpacing: 0, fontWeight: 650 },
    h3: { letterSpacing: 0, fontWeight: 600 },
    h4: { letterSpacing: 0, fontWeight: 600 },
    h5: { letterSpacing: 0, fontWeight: 600 },
    h6: { letterSpacing: 0, fontWeight: 600 },
    button: { letterSpacing: 0, fontWeight: 600, textTransform: 'none' },
  },
  shape: {
    borderRadius: 4,
  },
  components: {
    MuiCssBaseline: { styleOverrides: { ':root': ATLAS_CSS_VARIABLES } },
    MuiButton: {
      styleOverrides: {
        root: { minHeight: 44, borderRadius: 4 },
      },
    },
    MuiToggleButton: {
      styleOverrides: { root: { minHeight: 44 } },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          border: `1px solid ${atlas.line}`,
          boxShadow: 'none',
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
        },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        head: {
          color: atlas.muted,
          fontWeight: 600,
          background: atlas.wash,
        },
      },
    },
  },
});

export default appTheme;
