import assert from "node:assert/strict";
import { test } from "node:test";

import { canCancel, formatDate, formatMoney, itemSummary, statusLabel } from "../src/format.js";

test("formatMoney writes cents as dollars", () => {
  assert.equal(formatMoney(0), "$0.00");
  assert.equal(formatMoney(5), "$0.05");
  assert.equal(formatMoney(3890), "$38.90");
  assert.equal(formatMoney(123456789), "$1,234,567.89");
});

test("formatMoney refuses anything that is not whole non-negative cents", () => {
  for (const bad of [-1, 1.5, "100", null, undefined, NaN]) {
    assert.throws(() => formatMoney(bad), RangeError, `accepted ${bad}`);
  }
});

test("formatDate shows the UTC date, and nothing for a missing or invalid date", () => {
  assert.equal(formatDate("2026-10-28T23:30:00+00:00"), "2026-10-28");
  assert.equal(formatDate(null), "");
  assert.equal(formatDate("not a date"), "");
});

test("statusLabel names known statuses and passes unknown ones through", () => {
  assert.equal(statusLabel("placed"), "Placed");
  assert.equal(statusLabel("delivered"), "Delivered");
  assert.equal(statusLabel("lost"), "lost");
});

test("only a placed order can be cancelled", () => {
  assert.equal(canCancel({ status: "placed" }), true);
  for (const status of ["shipped", "delivered", "cancelled"]) assert.equal(canCancel({ status }), false, status);
});

test("itemSummary counts units, not lines", () => {
  assert.equal(itemSummary({ items: [{ quantity: 1 }] }), "1 item");
  assert.equal(itemSummary({ items: [{ quantity: 2 }, { quantity: 3 }] }), "5 items");
});
