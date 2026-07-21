const http = require("http");
const https = require("https");
const fs = require("fs");
const path = require("path");

// ========== 加载 .env ==========
function loadEnv() {
  const envPath = path.join(__dirname, ".env");
  if (!fs.existsSync(envPath)) return;
  for (const line of fs.readFileSync(envPath, "utf-8").split("\n")) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const eqIdx = trimmed.indexOf("=");
    if (eqIdx < 0) continue;
    const key = trimmed.slice(0, eqIdx).trim();
    const val = trimmed.slice(eqIdx + 1).trim();
    if (!process.env[key]) process.env[key] = val;
  }
}
loadEnv();

const PORT = parseInt(process.env.PORT || "8080", 10);
const PUBLISH_API_TOKEN = process.env.PUBLISH_API_TOKEN;

if (!PUBLISH_API_TOKEN) {
  console.error("[FATAL] PUBLISH_API_TOKEN is required in server/.env");
  console.error("        Run: echo 'PUBLISH_API_TOKEN=<your-token>' > server/.env");
  process.exit(1);
}

// ========== 工具函数 ==========
function sendJson(res, status, data) {
  const body = JSON.stringify(data);
  res.writeHead(status, {
    "Content-Type": "application/json; charset=utf-8",
    "Content-Length": Buffer.byteLength(body),
  });
  res.end(body);
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    req.on("data", (chunk) => chunks.push(chunk));
    req.on("end", () => resolve(Buffer.concat(chunks)));
    req.on("error", reject);
  });
}

// ========== 代理转发到微信 API ==========
async function proxyToWechat(req, res, urlPath) {
  const hasBody = ["POST", "PUT", "PATCH"].includes(req.method);
  const body = hasBody ? await readBody(req) : null;

  // 构造转发 headers，去掉 hop-by-hop 和鉴权头
  const forwardHeaders = {};
  for (const [key, val] of Object.entries(req.headers)) {
    const lower = key.toLowerCase();
    if (["host", "authorization", "connection", "x-forwarded-for"].includes(lower)) continue;
    forwardHeaders[key] = val;
  }
  if (body) {
    forwardHeaders["content-length"] = String(body.length);
  } else {
    delete forwardHeaders["content-length"];
  }

  const options = {
    hostname: "api.weixin.qq.com",
    port: 443,
    path: urlPath,
    method: req.method,
    headers: forwardHeaders,
  };

  return new Promise((resolve, reject) => {
    const proxyReq = https.request(options, (proxyRes) => {
      res.writeHead(proxyRes.statusCode, proxyRes.headers);
      proxyRes.pipe(res);
      proxyRes.on("end", resolve);
      proxyRes.on("error", reject);
    });

    proxyReq.on("error", (err) => {
      console.error(`[proxy] Error: ${err.message}`);
      if (!res.headersSent) {
        sendJson(res, 502, { error: "WeChat API proxy error", detail: err.message });
      }
      reject(err);
    });

    if (body) {
      proxyReq.write(body);
    }
    proxyReq.end();
  });
}

// ========== HTTP 服务器 ==========
const server = http.createServer(async (req, res) => {
  // CORS
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Headers", "Authorization, Content-Type");
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");

  if (req.method === "OPTIONS") {
    res.writeHead(204);
    res.end();
    return;
  }

  // 健康检查
  if (req.url === "/health") {
    return sendJson(res, 200, { ok: true });
  }

  // 鉴权
  const auth = req.headers["authorization"] || "";
  const token = auth.replace(/^Bearer\s+/i, "");
  if (token !== PUBLISH_API_TOKEN) {
    console.warn(`[auth] Rejected request: ${req.method} ${req.url}`);
    return sendJson(res, 401, { error: "Unauthorized", message: "Invalid or missing token" });
  }

  // 代理转发到微信 API
  const ts = new Date().toISOString();
  console.log(`[${ts}] ${req.method} ${req.url}`);

  try {
    await proxyToWechat(req, res, req.url);
  } catch (err) {
    console.error(`[server] Unhandled error: ${err.message}`);
    if (!res.headersSent) {
      sendJson(res, 500, { error: "Internal server error", detail: err.message });
    }
  }
});

server.listen(PORT, "0.0.0.0", () => {
  console.log(`[wechat-relay] Server running on http://0.0.0.0:${PORT}`);
  console.log(`[wechat-relay] Health check: http://localhost:${PORT}/health`);
  console.log(`[wechat-relay] Proxy target: https://api.weixin.qq.com`);
});
