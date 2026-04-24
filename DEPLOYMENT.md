# 🚀 Deployment Guide

**Domain:** citadelsdk.com  
**Frontend:** Vercel (connected to GitHub)  
**Backend:** Fly.io (Docker)  
**Database:** Neon PostgreSQL (free tier)  
**DNS:** Cloudflare

---

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Cloudflare    │────▶│  Vercel (Edge)  │     │   Fly.io (API)  │
│  citadelsdk.com │     │   Dashboard     │     │  FastAPI + Auth │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                              │                        │
                              └────────────────────────┘
                                       │
                              ┌─────────────────┐
                              │  Neon Postgres  │
                              │   (Database)    │
                              └─────────────────┘
```

**DNS Records:**
- `www.citadelsdk.com` → Vercel (frontend)
- `api.citadelsdk.com` → Fly.io (backend)
- `citadelsdk.com` → Redirect to www

---

## Step 1: Database (Neon)

1. Go to [neon.tech](https://neon.tech)
2. Sign up with GitHub
3. Create project → "citadel-db"
4. Copy connection string:
   ```
   postgresql://username:password@host.neon.tech/citadel?sslmode=require
   ```
5. Save it — you'll need it for Fly.io secrets

---

## Step 2: Backend API (Fly.io)

### Install Fly CLI
```bash
curl -L https://fly.io/install.sh | sh
fly auth signup  # Or login if you have account
```

### Launch the app
```bash
cd /path/to/ledger-sdk

# Create the app (first time only)
fly launch --name citadel-api --region iad --no-deploy

# Set secrets
fly secrets set DATABASE_URL="postgresql://..."
fly secrets set JWT_SECRET_KEY="$(openssl rand -hex 32)"
fly secrets set STRIPE_SECRET_KEY="sk_live_..."  # If billing enabled
fly secrets set STRIPE_WEBHOOK_SECRET="whsec_..."

# Deploy
fly deploy
```

### Verify it's up
```bash
# Check health
curl https://api.citadelsdk.com/v1/health/live

# Should return: {"alive": true}

curl https://api.citadelsdk.com/v1/health/ready
# Should return: {"ready": true, "database": "connected"}
```

### Auto-deploy on push
The GitHub Actions workflow (`.github/workflows/deploy-api.yml`) deploys automatically when you push to `master`.

**Setup:**
1. Go to Fly.io dashboard → Tokens → Create token
2. Copy token
3. Go to GitHub repo → Settings → Secrets → Actions
4. Add secret: `FLY_API_TOKEN` = your token

---

## Step 3: Frontend Dashboard (Vercel)

You already connected GitHub to Vercel. Now configure it:

### In Vercel Dashboard:
1. Go to your project settings
2. **Framework Preset:** Vite
3. **Root Directory:** `apps/dashboard`
4. **Build Command:** `npm run build`
5. **Output Directory:** `dist`

### Environment Variables (Vercel)
Add these in Vercel project settings → Environment Variables:
```
VITE_API_URL=https://api.citadelsdk.com
```

### Custom Domain
1. Vercel project → Settings → Domains
2. Add `www.citadelsdk.com`
3. Vercel will give you DNS records to add in Cloudflare

---

## Step 4: Cloudflare DNS

### Add Records:
```
Type    Name              Target                    TTL    Proxy
─────────────────────────────────────────────────────────────
CNAME   www               cname.vercel-dns.com      Auto   Orange (Proxied)
CNAME   api               citadel-api.fly.dev       Auto   Gray (DNS only)
A       citadelsdk.com    192.0.2.1 (redirect)     Auto   Orange
```

### SSL/TLS Settings:
1. Cloudflare dashboard → citadelsdk.com → SSL/TLS
2. **Encryption mode:** Full (strict)
3. **Always Use HTTPS:** ON
4. **Automatic HTTPS Rewrites:** ON

### Page Rules (Optional):
```
URL: citadelsdk.com/*
Settings: Forwarding URL → 301 → https://www.citadelsdk.com/$1
```

---

## Step 5: CORS Configuration

The backend currently allows `http://localhost:3000` and `http://localhost:5173` in debug mode.

For production, add your domain to allowed origins:

### Option A: Environment Variable
```bash
fly secrets set CORS_ORIGINS="https://www.citadelsdk.com,https://citadelsdk.com"
```

### Option B: Update Code
In `apps/runtime/citadel/config.py`, update:
```python
cors_origins: Optional[str] = "https://www.citadelsdk.com"
```

Then redeploy:
```bash
fly deploy
```

---

## Step 6: Test Everything

```bash
# 1. Health checks
curl https://api.citadelsdk.com/v1/health/live
curl https://api.citadelsdk.com/v1/health/ready

# 2. Demo (local, but points to production API)
python3 demo/citadel_demo.py

# 3. Dashboard
open https://www.citadelsdk.com

# 4. API docs (debug mode only)
open https://api.citadelsdk.com/docs
```

---

## Environment Variables Reference

### Backend (Fly.io Secrets)
```
DATABASE_URL=postgresql://...
JWT_SECRET_KEY=random-64-char-hex
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
CORS_ORIGINS=https://www.citadelsdk.com
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW_SECONDS=60
LOG_LEVEL=INFO
METRICS_ENABLED=true
```

### Frontend (Vercel)
```
VITE_API_URL=https://api.citadelsdk.com
```

---

## Troubleshooting

### "Database connection failed"
- Check `DATABASE_URL` in Fly.io secrets
- Neon requires `sslmode=require` in connection string
- Verify Neon allows connections from Fly.io IPs

### "CORS error in browser"
- Check `CORS_ORIGINS` includes your exact domain
- Make sure `https://` is included
- Clear browser cache

### "Vercel build fails"
- Check Root Directory is set to `apps/dashboard`
- Make sure `package.json` exists in that directory
- Check build logs for TypeScript errors

### "Fly.io deploy fails"
- Check `Dockerfile` builds locally: `docker build .`
- Verify `fly.toml` app name matches `fly launch` output
- Check logs: `fly logs`

---

## Costs (Estimated)

| Service | Plan | Monthly |
|---------|------|---------|
| Domain (Cloudflare) | .com | ~$9/yr |
| Fly.io | 512MB VM | ~$2-5 |
| Neon | Free tier | $0 |
| Vercel | Hobby (free) | $0 |
| **Total** | | **$2-5/mo** |

---

## Next Steps

- [ ] Add Stripe webhook endpoint URL in Stripe Dashboard: `https://api.citadelsdk.com/v1/billing/webhooks/stripe`
- [ ] Set up monitoring (Sentry for errors, Fly.io metrics)
- [ ] Configure backup strategy (Neon has point-in-time recovery)
- [ ] Add GitHub Actions for frontend deploy to Vercel
- [ ] Set up staging environment: `staging-api.citadelsdk.com`
