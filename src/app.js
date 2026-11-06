import { ApiError, createClient } from "./api.js";
import { API_URL } from "./config.js";
import { canCancel, formatDate, formatMoney, itemSummary, statusLabel } from "./format.js";

const api = createClient(API_URL);
const els = {
  filter: document.querySelector("#status-filter"),
  rows: document.querySelector("#order-rows"),
  message: document.querySelector("#message"),
  detail: document.querySelector("#detail"),
};

function cell(text) {
  const td = document.createElement("td");
  td.textContent = text;
  return td;
}

function show(text, isError = false) {
  els.message.textContent = text;
  els.message.className = isError ? "error" : "";
}

function describe(error) {
  return error instanceof ApiError ? error.message : "Could not reach the Orders API.";
}

async function loadOrders() {
  try {
    const orders = await api.listOrders(els.filter.value);
    els.rows.replaceChildren(
      ...orders.map((order) => {
        const tr = document.createElement("tr");
        tr.append(cell(order.id), cell(order.customer_name), cell(itemSummary(order)),
          cell(formatMoney(order.total_cents)), cell(statusLabel(order.status)), cell(formatDate(order.created_at)));
        tr.tabIndex = 0;
        tr.addEventListener("click", () => openOrder(order.id));
        tr.addEventListener("keydown", (e) => e.key === "Enter" && openOrder(order.id));
        return tr;
      }),
    );
    show(orders.length ? "" : "No orders match this filter.");
  } catch (error) {
    show(describe(error), true);
  }
}

async function openOrder(id) {
  try {
    const order = await api.getOrder(id);
    const lines = order.items.map((i) => `${i.quantity} × ${i.name} (${formatMoney(i.unit_price_cents)} each)`);
    els.detail.replaceChildren();
    const title = document.createElement("h2");
    title.textContent = `${order.id}: ${statusLabel(order.status)}`;
    const list = document.createElement("ul");
    list.append(...lines.map((line) => Object.assign(document.createElement("li"), { textContent: line })));
    const total = document.createElement("p");
    total.textContent = `Total ${formatMoney(order.total_cents)}`;
    els.detail.append(title, list, total);
    if (canCancel(order)) {
      const button = document.createElement("button");
      button.textContent = "Cancel order";
      button.addEventListener("click", () => cancel(order.id));
      els.detail.append(button);
    }
  } catch (error) {
    show(describe(error), true);
  }
}

async function cancel(id) {
  try {
    await api.cancelOrder(id);
    show(`${id} cancelled.`);
    await Promise.all([loadOrders(), openOrder(id)]);
  } catch (error) {
    show(describe(error), true);
  }
}

els.filter.addEventListener("change", loadOrders);
loadOrders();
