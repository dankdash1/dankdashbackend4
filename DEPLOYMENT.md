# DankDash Deployment Guide

## 🚀 Production Deployment Options

### Option 1: Railway (Recommended)
Railway provides automatic PostgreSQL database and easy deployment.

1. **Connect GitHub Repository**
   ```bash
   # Push your code to GitHub
   git push origin main
   ```

2. **Deploy on Railway**
   - Go to [railway.app](https://railway.app)
   - Connect your GitHub repository
   - Railway will automatically detect Flask app
   - Add PostgreSQL database service

3. **Environment Variables**
   Set these in Railway dashboard:
   ```
   DATABASE_URL=postgresql://... (automatically provided by Railway)
   SECRET_KEY=your-secret-key
   SENDGRID_API_KEY=your-sendgrid-key
   TWILIO_ACCOUNT_SID=your-twilio-sid
   TWILIO_AUTH_TOKEN=your-twilio-token
   ```

### Option 2: Heroku
1. **Install Heroku CLI**
2. **Create Heroku App**
   ```bash
   heroku create your-app-name
   heroku addons:create heroku-postgresql:hobby-dev
   ```

3. **Deploy**
   ```bash
   git push heroku main
   ```

### Option 3: DigitalOcean/AWS/GCP
1. **Create PostgreSQL Database**
2. **Deploy Flask App**
3. **Set Environment Variables**

## 🗄️ Database Setup

### PostgreSQL Production Setup
The app automatically detects PostgreSQL and creates all necessary tables.

**Required Tables:**
- `orders` - All customer orders
- `pos_transactions` - Point of sale transactions
- `inventory` - Product inventory
- `accounting_entries` - Financial records
- `customers` - Customer database
- `partners` - Partner applications

### Local Development (SQLite)
For local development, the app uses SQLite automatically.

```bash
# Local development
python3 src/main.py
```

## 🔧 Environment Configuration

### Development (.env)
```bash
DATABASE_URL=sqlite:///dankdash.db
SECRET_KEY=dev-secret-key
FLASK_ENV=development
DEBUG=True
```

### Production (.env)
```bash
DATABASE_URL=postgresql://user:pass@host:port/dbname
SECRET_KEY=secure-random-key
FLASK_ENV=production
DEBUG=False
SENDGRID_API_KEY=your-key
TWILIO_ACCOUNT_SID=your-sid
TWILIO_AUTH_TOKEN=your-token
```

## 📦 Frontend Deployment

### Option 1: Netlify (Recommended)
1. Build the frontend:
   ```bash
   cd frontend
   npm run build
   ```

2. Deploy `dist/` folder to Netlify

3. Set environment variables:
   ```
   VITE_API_URL=https://your-backend-url.railway.app
   ```

### Option 2: Vercel
1. Connect GitHub repository
2. Vercel auto-detects Vite project
3. Set build command: `npm run build`
4. Set output directory: `dist`

## 🔄 Database Migration

The app automatically creates tables on first run. For existing data:

```python
# Run this in Python console
from src.database_config import db_config
db_config.init_database()
```

## 🛡️ Security Checklist

- [ ] Set strong SECRET_KEY
- [ ] Use environment variables for sensitive data
- [ ] Enable HTTPS in production
- [ ] Set proper CORS origins
- [ ] Use PostgreSQL for production
- [ ] Regular database backups

## 📊 Monitoring

### Health Check Endpoint
```
GET /api/health
```

### Database Status
```
GET /api/status
```

## 🔧 Troubleshooting

### Common Issues

1. **Database Connection Error**
   - Check DATABASE_URL format
   - Verify PostgreSQL credentials
   - Ensure database exists

2. **CORS Errors**
   - Set proper CORS_ORIGINS
   - Check frontend API URL

3. **Environment Variables**
   - Verify all required vars are set
   - Check .env file location

### Logs
```bash
# Railway
railway logs

# Heroku
heroku logs --tail

# Local
python3 src/main.py
```

## 🚀 Quick Deploy Commands

### Railway
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and deploy
railway login
railway link
railway up
```

### Heroku
```bash
# Create and deploy
heroku create dankdash-backend
heroku addons:create heroku-postgresql:hobby-dev
git push heroku main
```

## 📈 Scaling

### Database Scaling
- Start with hobby tier PostgreSQL
- Upgrade to standard/premium as needed
- Consider read replicas for high traffic

### App Scaling
- Use gunicorn for production WSGI
- Scale horizontally with load balancer
- Consider Redis for session storage

## 🔄 CI/CD Pipeline

### GitHub Actions Example
```yaml
name: Deploy to Railway
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Deploy to Railway
        run: railway up
```

---

**Need Help?** Check the logs and ensure all environment variables are properly set.

