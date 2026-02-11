const rawUiMode = import.meta.env.VITE_UI_MODE;

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8100';
export const UI_MODE = rawUiMode === 'debug' ? 'debug' : 'prod';
