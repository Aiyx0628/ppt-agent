export {};

declare global {
  interface Window {
    deckflow: {
      getRuntimeInfo: () => {
        platform: string;
        apiBaseUrl: string;
      };
      pingBackend: () => Promise<{
        app: string;
        environment: string;
        timestamp: string;
        storage_root: string;
        services: Record<
          string,
          {
            status: "ok" | "error" | "degraded" | "not_configured";
            detail: string;
          }
        >;
      }>;
    };
  }
}
