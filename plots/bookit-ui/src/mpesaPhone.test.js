import test from "node:test";
import assert from "node:assert/strict";
import { maskKenyanPhone, normalizeKenyanPhone } from "./mpesaPhone.js";

test("normalizes the supported Kenyan M-Pesa phone formats", () => {
  for (const phone of [
    "0712345678",
    "0112345678",
    "254712345678",
    "254112345678",
    "+254712345678",
    "+254112345678",
  ]) {
    assert.match(normalizeKenyanPhone(phone), /^254[71]\d{8}$/);
  }
});

test("rejects invalid numbers and masks a normalized number", () => {
  assert.equal(normalizeKenyanPhone("abc0712345678"), null);
  assert.equal(normalizeKenyanPhone("072345678"), null);
  assert.equal(normalizeKenyanPhone("+254812345678"), null);
  assert.equal(maskKenyanPhone("254712345678"), "*******5678");
});
