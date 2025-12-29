# Deploying backend to VPS (FastAPI/Web3)

This bundle contains only backend essentials for running the API. Excluded: miniapp frontend, contracts, virtual envs, git metadata, and caches.

## Included files
- `app/`
- `alembic/`, `migrations/`, `alembic.ini`
- `scripts/` (incl. `scripts/insert_vault_address.sql`)
- `init_tables.sql` (optional bootstrap)
- `requirements.txt`, `dev.requirements.txt`

## Not included / not needed
- `.git/`, `venv/`, `node_modules/`
- `miniapp/` (Svelte frontend)
- `contracts/` (Hardhat)

## Prepare environment
1) Python: ensure 3.11+ is installed.
2) Create venv and install deps:
   ```
   python3 -m venv venv
   source venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   # optionally: pip install -r dev.requirements.txt
   ```
3) Database: ensure Postgres reachable; export `DATABASE_URL` accordingly.
4) Redis (if used): export `REDIS_URL`.

## Minimal .env (create on VPS, do NOT commit)
```
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/dbname
REDIS_URL=redis://localhost:6379/0
SEPOLIA_RPC_URL=https://sepolia.infura.io/v3/<key>
VAULT_ADDRESS=<deployed_vault_address>
REGISTRY_ADDRESS=<deployed_registry_address>
TELEGRAM_BOT_TOKEN=<token>
```

## Database migrations
- Preferred: `alembic upgrade head`
- If bootstrapping manually: run `init_tables.sql`, then `scripts/insert_vault_address.sql` if needed.

## Run backend (local test)
```
source venv/bin/activate
uvicorn app.__main__:app --host 127.0.0.1 --port 8000
```

## systemd unit example (`/etc/systemd/system/backend.service`)
```
[Unit]
Description=Backend API
After=network.target

[Service]
User=www-data
WorkingDirectory=/home/www/project
EnvironmentFile=/home/www/project/.env
ExecStart=/home/www/project/venv/bin/uvicorn app.__main__:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```
Enable & start:
```
sudo systemctl daemon-reload
sudo systemctl enable --now backend.service
```

## Nginx reverse proxy (HTTP, before SSL)
`/etc/nginx/sites-available/api.conf`
```
server {
  server_name api.example.com;
  listen 80;
  listen [::]:80;

  location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
  }
}
```
Enable and test:
```
sudo ln -s /etc/nginx/sites-available/api.conf /etc/nginx/sites-enabled/api.conf
sudo nginx -t
sudo systemctl reload nginx
```

## Let’s Encrypt (HTTPS)
```
sudo apt update
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d api.example.com --redirect --agree-tos -m you@example.com
```
This will add `listen 443 ssl` and an HTTP→HTTPS redirect automatically.

## rsync command (from your local machine to VPS)
Replace `user@vps:/home/www/project` with the target path.
```
rsync -av \
  --exclude '.git' \
  --exclude 'venv' \
  --exclude 'node_modules' \
  --exclude 'miniapp' \
  --exclude 'contracts' \
  ./ user@vps:/home/www/project
```

## Health check after deploy
```
curl -I https://api.example.com/health
```
Expect `200/301` depending on your route/redirects.



