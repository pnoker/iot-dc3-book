# 安全头部配置指引

`book.dc3.site` 托管于 GitHub Pages，不支持自定义 HTTP 响应头。以下为生产部署推荐配置。

## GitHub Pages 已默认提供

- ✅ HTTPS 强制（无法通过 `.dev` 域名访问 HTTP）
- ✅ HSTS preload（`github.io` 及自定义域在 Chromium HSTS preload list 中）
- ✅ HTTP/2

## 自定义域名部署建议

若迁移至自有服务器或 Cloudflare Pages / Vercel，推荐添加以下响应头：

### 生产 Nginx 配置

```nginx
# 安全头部
add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-Frame-Options "SAMEORIGIN" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;

# CSP — 允许 GA4 + 百度统计 + 自有资源
add_header Content-Security-Policy
  "default-src 'self';
   script-src 'self' 'unsafe-inline' https://www.googletagmanager.com https://hm.baidu.com;
   img-src 'self' data: https:;
   style-src 'self' 'unsafe-inline';
   connect-src 'self' https://www.google-analytics.com https://hm.baidu.com;
   font-src 'self';
   frame-ancestors 'none';" always;

# 静态资源缓存
location /assets/ {
  expires 1y;
  add_header Cache-Control "public, immutable";
}
location ~ \.(webp|png|svg)$ {
  expires 30d;
  add_header Cache-Control "public";
}
location /feed.xml {
  add_header Content-Type "application/atom+xml; charset=utf-8";
}
```

### Cloudflare Pages

在项目根目录添加 `_headers` 文件：

```
/*
  Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
  X-Content-Type-Options: nosniff
  X-Frame-Options: SAMEORIGIN
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: camera=(), microphone=(), geolocation=()

/assets/*
  Cache-Control: public, max-age=31536000, immutable
```

### 验证

部署后使用以下工具验证：

- [Security Headers](https://securityheaders.com/)
- [HSTS Preload](https://hstspreload.org/)
- [CSP Evaluator](https://csp-evaluator.withgoogle.com/)

## 已知限制（GitHub Pages）

| 头部 | 状态 | 说明 |
|------|------|------|
| `Strict-Transport-Security` | ⚠️ 不可配 | GitHub Pages 已内建，但不可自定义 max-age |
| `Content-Security-Policy` | ❌ 不可配 | GitHub Pages 不支持自定义 HTTP 头 |
| `X-Content-Type-Options` | ❌ 不可配 | 同上 |
| 自定义 Cache-Control | ❌ 不可配 | 同上（GitHub 控制缓存策略） |

> **结论**: GitHub Pages 的基础安全足够（HTTPS + HTTP/2），但缺少 CSP 等精细化控制。如需满分安全配置，建议迁移至 Cloudflare Pages（免费）或 Vercel。
