// Local Mode (default) — talks to the real ASP.NET Core API + SQL Server.
// No secrets here: this is only a base URL for a local dev server.
export const environment = {
  dataMode: 'local' as const,
  apiBaseUrl: 'http://localhost:5020/api/research',
};
