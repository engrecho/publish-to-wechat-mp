import type { WechatClient } from "./wechat-http.ts";

export interface ServerPublishConfig {
  /** 中转服务器基础 URL，如 https://tencent.bajiaolu.cn */
  url: string;
  /** 客户端访问中转服务的 Bearer token */
  token: string;
  /** 请求超时（秒），默认 60 */
  timeout?: number;
}

const WECHAT_API_BASE = "https://api.weixin.qq.com";

/**
 * 创建一个 WechatClient，将所有微信 API 请求通过中转服务器转发。
 * 客户端本地完成 markdown 渲染、图片处理等全部工作，
 * 仅把对 api.weixin.qq.com 的 HTTPS 调用改为发往中转服务器。
 */
export function createServerApiClient(config: ServerPublishConfig): WechatClient {
  const baseUrl = config.url.replace(/\/+$/, "");
  const timeoutMs = (config.timeout ?? 60) * 1000;

  return async (url: string, init = {}) => {
    // 将 https://api.weixin.qq.com/cgi-bin/... 替换为中转服务器地址
    const serverUrl = url.replace(WECHAT_API_BASE, baseUrl);

    const method = init.method ?? (init.body !== undefined ? "POST" : "GET");
    const headers: Record<string, string> = {
      ...(init.headers ?? {}),
      Authorization: `Bearer ${config.token}`,
    };

    let body: BodyInit | undefined;
    if (init.body !== undefined) {
      body = Buffer.isBuffer(init.body)
        ? new Uint8Array(init.body.buffer, init.body.byteOffset, init.body.byteLength)
        : init.body;
    }

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);

    try {
      const res = await fetch(serverUrl, { method, headers, body, signal: controller.signal });
      const buf = Buffer.from(await res.arrayBuffer());

      const responseHeaders: Record<string, string | string[] | undefined> = {};
      res.headers.forEach((value, key) => {
        const existing = responseHeaders[key];
        if (existing === undefined) {
          responseHeaders[key] = value;
        } else if (Array.isArray(existing)) {
          existing.push(value);
        } else {
          responseHeaders[key] = [existing, value];
        }
      });

      return {
        status: res.status,
        statusText: res.statusText,
        headers: responseHeaders,
        async buffer() {
          return buf;
        },
        async text() {
          return buf.toString("utf-8");
        },
        async json<T = unknown>() {
          return JSON.parse(buf.toString("utf-8")) as T;
        },
      };
    } finally {
      clearTimeout(timer);
    }
  };
}
