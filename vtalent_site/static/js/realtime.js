import { createRealtimeClient } from "@neon/realtime/client";

const apiUrl = document.body.dataset.realtimeApiUrl;
const realtimeUrl = document.body.dataset.neonRealtimeUrl;

if (apiUrl && realtimeUrl && !window.location.pathname.startsWith("/admin/")) {
  const client = createRealtimeClient({ url: realtimeUrl });

  async function subscribeToPublicUpdates() {
    const response = await fetch(new URL("/api/sealed-queries", apiUrl), {
      headers: { Accept: "application/json" },
    });
    if (!response.ok) {
      throw new Error(`Realtime query endpoint returned ${response.status}.`);
    }

    const { queries } = await response.json();
    for (const query of queries) {
      let receivedInitialSnapshot = false;
      const subscription = client.subscribe(query);
      subscription.onChange(() => {
        if (receivedInitialSnapshot) {
          window.location.reload();
          return;
        }
        receivedInitialSnapshot = true;
      });
    }
  }

  subscribeToPublicUpdates().catch((error) => {
    console.error("Could not start Neon Realtime subscriptions.", error);
  });

  window.addEventListener("beforeunload", () => client.close(), { once: true });
}
