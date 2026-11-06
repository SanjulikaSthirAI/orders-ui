import assert from "node:assert/strict";
import { test } from "node:test";

import { ApiError, createClient } from "../src/api.js";

function fakeFetch(status, body) {
  const calls = [];
  const fn = async (url, options) => {
    calls.push({ url, options });
    return { ok: status < 400, status, json: async () => body() };
  };
  return { fn, calls };
}

test("listOrders calls /orders, adding the status filter when given", async () => {
  const { fn, calls } = fakeFetch(200, () => []);
  const api = createClient("http://api.test/", fn);
  await api.listOrders();
  await api.listOrders("placed");
  assert.deepEqual(calls.map((c) => c.url), ["http://api.test/orders", "http://api.test/orders?status=placed"]);
});

test("getOrder encodes the id", async () => {
  const { fn, calls } = fakeFetch(200, () => ({ id: "ORD-1" }));
  await createClient("http://api.test", fn).getOrder("a/b");
  assert.equal(calls[0].url, "http://api.test/orders/a%2Fb");
});

test("cancelOrder posts to the cancel path", async () => {
  const { fn, calls } = fakeFetch(200, () => ({ id: "ORD-1", status: "cancelled" }));
  const order = await createClient("http://api.test", fn).cancelOrder("ORD-1");
  assert.equal(calls[0].url, "http://api.test/orders/ORD-1/cancel");
  assert.equal(calls[0].options.method, "POST");
  assert.equal(order.status, "cancelled");
});

test("an error response becomes an ApiError carrying the API's message and status", async () => {
  const { fn } = fakeFetch(409, () => ({ detail: "Order ORD-1 is shipped; only placed orders can be cancelled" }));
  await assert.rejects(createClient("http://api.test", fn).cancelOrder("ORD-1"), (error) => {
    assert.ok(error instanceof ApiError);
    assert.equal(error.status, 409);
    assert.match(error.message, /only placed orders/);
    return true;
  });
});

test("an error response that is not JSON still reports its status", async () => {
  const fn = async () => ({ ok: false, status: 502, json: async () => Promise.reject(new SyntaxError("bad")) });
  await assert.rejects(createClient("http://api.test", fn).getOrder("ORD-1"), /Request failed \(502\)/);
});
