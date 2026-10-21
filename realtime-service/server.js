import { createServer } from "node:http";
import { createRealtime, rawSql } from "@neon/realtime/server";

function requiredEnv(name) {
  const value = process.env[name];
  if (!value) {
    throw new Error(`${name} must be configured.`);
  }
  return value;
}

const databaseUrl = new URL(requiredEnv("DATABASE_URL"));
const databaseName = decodeURIComponent(databaseUrl.pathname.slice(1));
if (!databaseName) {
  throw new Error("DATABASE_URL must include a database name.");
}

const allowedOrigin = new URL(requiredEnv("APP_ORIGIN")).origin;
const realtime = createRealtime({
  secret: requiredEnv("NEON_REALTIME_SECRET"),
  db: databaseName,
});

const queries = [
  rawSql(
    `SELECT id, title, category, description, duration, syllabus, display_order, is_published, updated_at
     FROM myapp_course
     WHERE is_published = TRUE
     ORDER BY display_order, title`,
  ),
  rawSql(
    `SELECT id, course_id, name, month, year, duration, google_form_url, registrations_open, is_visible, updated_at
     FROM myapp_batch
     WHERE is_visible = TRUE
     ORDER BY year, month, name`,
  ),
  rawSql(
    `SELECT id, message, is_active, created_at
     FROM myapp_announcement
     WHERE is_active = TRUE
     ORDER BY created_at DESC`,
  ),
];

const server = createServer(async (request, response) => {
  const origin = request.headers.origin;
  if (origin && origin !== allowedOrigin) {
    response.writeHead(403);
    response.end("Forbidden");
    return;
  }

  if (origin) {
    response.setHeader("Access-Control-Allow-Origin", allowedOrigin);
    response.setHeader("Vary", "Origin");
  }

  if (request.method === "GET" && request.url === "/healthz") {
    response.writeHead(200, { "Content-Type": "text/plain" });
    response.end("ok");
    return;
  }

  if (request.method !== "GET" || request.url !== "/api/sealed-queries") {
    response.writeHead(404);
    response.end("Not found");
    return;
  }

  try {
    const sealedQueries = await Promise.all(
      queries.map((query) => realtime.seal({ query })),
    );
    response.writeHead(200, {
      "Cache-Control": "no-store",
      "Content-Type": "application/json",
    });
    response.end(JSON.stringify({ queries: sealedQueries }));
  } catch (error) {
    console.error("Failed to seal public Realtime queries.", error);
    response.writeHead(500, { "Content-Type": "text/plain" });
    response.end("Unable to prepare Realtime subscriptions.");
  }
});

const port = Number(process.env.PORT || 3000);
server.listen(port, "0.0.0.0", () => {
  console.log(`Realtime API listening on port ${port}.`);
});
