# orders-ui

A browser UI for the orders demo API: list orders, filter by status, open one, cancel it while it is still `placed`.

```sh
npm run lint
npm test
npm start          # http://localhost:8080, expects orders-api on http://localhost:8000
```

The API address is in `src/config.js`. The API allows this UI's origin through CORS
(`ORDERS_UI_ORIGINS` in orders-api).
