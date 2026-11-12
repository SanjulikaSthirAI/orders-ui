# Orders UI: guide for coding agents

A small browser UI for the Orders API (`orders-api`, contract in its `openapi.yaml`). Plain HTML and ES modules.
There is no build step and there are no runtime dependencies.

## Layout

- `index.html`, `styles.css`: the page.
- `src/api.js`: the only code that calls the API. Takes the base URL and a `fetch` function.
- `src/format.js`: pure display helpers. Put new formatting and display rules here so they can be tested.
- `src/app.js`: DOM wiring only. No business rules here.
- `src/config.js`: the API address.
- `tests/`: `node --test`. Test `api.js` with an injected fake `fetch`, and `format.js` directly.

## Commands

- Lint: `npm run lint`
- Test: `npm test`
- Run locally: start the API on port 8000, then `npm start` and open http://localhost:8080

## Rules

- Call the API only through `src/api.js`, and only with operations that exist in the API's `openapi.yaml`.
  If the UI needs an operation the API lacks, that is an API change first.
- Money arrives as integer cents (`*_cents`). Display it with `formatMoney`; never convert to floats.
- Show the API's own error `detail` to the user. Do not invent messages for status codes.
- Build DOM with `textContent` and `createElement`, never `innerHTML` with API data.
- Every new helper or client call needs a test, including its failure case.
- `.github/` and `AGENTS.md` are code-owned; do not edit them outside an approved change.

<!-- protected-contracts:start INT-2 -->
## Protected contracts (INT-2)

Stories must not change these unless plan.json marks the story as a contract change.

- File: `api/**`
- File: `app/**`
- File: `config/**`
- File: `format/**`
<!-- protected-contracts:end INT-2 -->
