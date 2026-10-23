#!/usr/bin/env node
/**
 * NDJSON sidecar exposing @desert-ant-labs/redact v3.1.0 to the Python
 * ingest hook. One JSON object per stdin line:
 *   {"id": 1, "text": "..."}
 * One JSON object per stdout line:
 *   {"id": 1, "redactedText": "...", "items": [...]}
 * The model downloads from Hugging Face on first load (pinned revision,
 * SHA-256 verified) and is cached on disk.
 */
import { Redact } from "@desert-ant-labs/redact/native";
import { createInterface } from "node:readline";

const redact = await Redact.load();
const rl = createInterface({ input: process.stdin });

rl.on("line", async (line) => {
  const trimmed = line.trim();
  if (!trimmed) return;
  let req;
  try {
    req = JSON.parse(trimmed);
  } catch {
    return;
  }
  try {
    const r = await redact.redaction(String(req.text ?? ""));
    process.stdout.write(
      JSON.stringify({
        id: req.id,
        redactedText: r.redactedText,
        items: r.items,
      }) + "\n",
    );
  } catch (err) {
    process.stdout.write(
      JSON.stringify({ id: req.id, error: String(err && err.message ? err.message : err) }) + "\n",
    );
  }
});

rl.on("close", () => {
  redact.dispose();
  process.exit(0);
});
