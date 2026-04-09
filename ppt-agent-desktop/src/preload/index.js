const { contextBridge } = require("electron");

const apiBaseUrl = process.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

contextBridge.exposeInMainWorld("deckflow", {
  getRuntimeInfo: () => ({
    platform: process.platform,
    apiBaseUrl,
  }),
  pingBackend: async () => {
    const response = await fetch(`${apiBaseUrl}/api/health`);
    if (!response.ok) {
      throw new Error(`Health check failed with status ${response.status}`);
    }

    return response.json();
  },
});
