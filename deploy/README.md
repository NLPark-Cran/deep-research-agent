# 部署说明

## 已完成的部署

- **域名**：https://research.hub.tt2.li
- **Web 框架**：Gradio 6.18.0
- **反向代理**：Nginx
- **HTTPS 证书**：Let's Encrypt (Certbot)
- **进程管理**：systemd

## Nginx 配置

配置文件：`deploy/nginx-research.hub.tt2.li.conf`

已放置到：`/etc/nginx/sites-available/research.hub.tt2.li`

启用方式：
```bash
ln -sf /etc/nginx/sites-available/research.hub.tt2.li /etc/nginx/sites-enabled/
nginx -t
systemctl reload nginx
```

## systemd 服务

服务文件：`deploy/deep-research-agent.service`

已放置到：`/etc/systemd/system/deep-research-agent.service`

管理命令：
```bash
systemctl start deep-research-agent    # 启动
systemctl stop deep-research-agent     # 停止
systemctl restart deep-research-agent  # 重启
systemctl status deep-research-agent   # 查看状态
systemctl enable deep-research-agent   # 开机自启
```

## HTTPS 证书

使用 Certbot 申请：
```bash
certbot certonly --nginx -d research.hub.tt2.li
```

证书自动续期已由 Certbot 配置。

## 环境变量

服务启动时会加载 `/root/workspace/test0607/final/.env` 中的：
- `TOKENDANCE_API_KEY`
- `TOKENDANCE_BASE_URL`
- `LLM_MODEL`
- `SEARCH_BACKEND`
- `MAX_ITERATIONS`
