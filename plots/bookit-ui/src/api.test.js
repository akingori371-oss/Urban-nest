import assert from "node:assert/strict";
import { test } from "node:test";
import { api } from "./Api.js";

globalThis.localStorage = {
  getItem: () => null,
  setItem: () => {},
  removeItem: () => {},
};

test("HTML API responses become readable errors without exposing the HTML", async () => {
  globalThis.fetch = async () => new Response("<!doctype html><html><body>debug traceback</body></html>", {
    status: 500,
    headers: { "Content-Type": "text/html" },
  });

  const response = await api("/houses/?page=1");
  const body = await response.json();

  assert.equal(response.ok, false);
  assert.equal(response.status, 500);
  assert.match(body.detail, /unexpected HTML response \(HTTP 500\)/);
  assert.match(body.detail, /\/api\/houses\/\?page=1/);
  assert.doesNotMatch(body.detail, /debug traceback/);
});

test("204 responses are successful and have an empty body", async () => {
  globalThis.fetch = async () => new Response(null, { status: 204 });

  const response = await api("/bookings/1/cancel/", { method: "DELETE" });

  assert.equal(response.ok, true);
  assert.equal(await response.json(), null);
});

test("network errors and malformed JSON produce structured failures", async () => {
  globalThis.fetch = async () => { throw new TypeError("offline"); };
  const network = await api("/houses/");
  assert.equal(network.ok, false);
  assert.match((await network.json()).detail, /Could not reach the server/);

  globalThis.fetch = async () => new Response("{broken", {
    status: 502,
    headers: { "Content-Type": "application/json" },
  });
  const malformed = await api("/houses/");
  assert.equal(malformed.status, 502);
  assert.match((await malformed.json()).detail, /invalid JSON \(HTTP 502\)/);
});
