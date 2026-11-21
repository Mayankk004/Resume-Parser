import { createRealtimeClient } from "@neon/realtime/client";

let cachedClient = null;
let cachedUrl = "";

export function getRealtimeClient(url) {
  const targetUrl = (url || process.env.REACT_APP_NEON_REALTIME_URL || "").trim();
  if (!targetUrl) return null;
  if (cachedClient && cachedUrl === targetUrl) {
    return cachedClient;
  }
  if (cachedClient) {
    cachedClient.close();
  }
  cachedUrl = targetUrl;
  cachedClient = createRealtimeClient({ url: targetUrl });
  return cachedClient;
}
