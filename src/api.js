// Client for the Orders API (orders-api/openapi.yaml). `fetchFn` is injectable for tests.

export class ApiError extends Error {
  constructor(status, detail) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
  }
}

export function createClient(baseUrl, fetchFn = (...args) => fetch(...args)) {
  const root = baseUrl.replace(/\/+$/, "");

  async function call(path, options) {
    const response = await fetchFn(`${root}${path}`, options);
    if (response.ok) return response.json();
    let detail = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      // not JSON: keep the generic message
    }
    throw new ApiError(response.status, detail);
  }

  return {
    listOrders(status) {
      const query = status ? `?status=${encodeURIComponent(status)}` : "";
      return call(`/orders${query}`);
    },
    getOrder(id) {
      return call(`/orders/${encodeURIComponent(id)}`);
    },
    cancelOrder(id) {
      return call(`/orders/${encodeURIComponent(id)}/cancel`, { method: "POST" });
    },
  };
}
