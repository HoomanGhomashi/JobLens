// Demo Mode — no backend, no SQL Server. Data is read from static JSON
// under public/demo/*.json, servable as-is by any static host (Vercel included).
export const environment = {
  dataMode: 'demo' as const,
  apiBaseUrl: '',
};
