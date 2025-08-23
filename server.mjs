import express from "express";
import cors from "cors";
import { testConnection } from "./src/db.js";

const app = express();
const PORT = process.env.PORT || 3000;

// Frontend origin (we’ll set this in Railway later)
const FRONTEND_ORIGIN = process.env.FRONTEND_ORIGIN || "*";

app.use(cors({ origin: FRONTEND_ORIGIN, credentials: true }));
app.use(express.json());

// Simple request logger
app.use((req, _res, next) => {
  console.log(`[${new Date().toISOString()}] ${req.method} ${req.originalUrl}`);
  next();
});

// Health check
app.get("/health", (_req, res) => res.json({ ok: true }));

// Products endpoint
app.get("/api/products", async (_req, res) => {
  try {
    const demoProducts = [
      { id: 1, name: "Demo Item A", price: 10.0 },
      { id: 2, name: "Demo Item B", price: 15.5 },
    ];
    return res.json(demoProducts);
  } catch (err) {
    console.error("Products error:", err);
    return res.status(500).json({ ok: false, message: "Failed to load products" });
  }
});

// Orders endpoint
app.post("/api/orders", async (req, res) => {
  try {
    const payload = req.body;
    console.log("ORDER PAYLOAD:", payload);

    return res.status(201).json({ ok: true, orderId: `ord_${Date.now()}` });
  } catch (err) {
    console.error("Order error:", err);
    return res.status(400).json({ ok: false, message: err.message || "Order failed" });
  }
});

// Global error handler
app.use((err, _req, res, _next) => {
  console.error("Unhandled error:", err);
  res.status(500).json({ ok: false, message: "Server error" });
});

// Start server
app.listen(PORT, async () => {
  console.log(`Server listening on :${PORT}`);
  
  // Test database connection
  await testConnection();
});
