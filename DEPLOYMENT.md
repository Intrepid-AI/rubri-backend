# Rubri Deployment Guide - Coolify + Hetzner

This guide will walk you through deploying the Rubri application on Hetzner Cloud using Coolify.

## Prerequisites

- A domain name (e.g., rubri.ai)
- Credit card for Hetzner account
- Basic knowledge of SSH and command line

## Step 1: Set Up Hetzner Cloud Account

1. **Create Account**
   - Go to [Hetzner Cloud](https://www.hetzner.com/cloud)
   - Sign up for an account
   - **Important**: Use a professional email (not Gmail/free email)
   - Don't use VPN during registration
   - Start with the smallest server for verification

2. **Create Your Server**
   - Click "New Server"
   - Choose **Ubuntu 22.04** as the OS
   - Select **CX22** (€3.79/month) - 2 vCPU, 4GB RAM, 40GB SSD
   - Choose a location (EU recommended for GDPR)
   - Add your SSH key or use password
   - Click "Create & Buy now"

3. **Note Your Server IP**
   - You'll receive an IP address like `123.456.789.10`
   - Save this for DNS configuration

## Step 2: Configure DNS

1. **Go to Your Domain Provider** (GoDaddy, Namecheap, etc.)

2. **Add DNS Records**:
   ```
   Type  | Name | Value              | TTL
   ------|------|-------------------|-----
   A     | @    | YOUR_SERVER_IP    | 3600
   A     | www  | YOUR_SERVER_IP    | 3600
   A     | api  | YOUR_SERVER_IP    | 3600
   ```

3. **Wait for DNS Propagation** (5-30 minutes usually)

## Step 3: Install Coolify

1. **SSH into Your Server**
   ```bash
   ssh root@YOUR_SERVER_IP
   ```

2. **Run Coolify Installation**
   ```bash
   curl -fsSL https://cdn.coollabs.io/coolify/install.sh | bash
   ```

3. **Access Coolify**
   - Open browser: `http://YOUR_SERVER_IP:8000`
   - Create your admin account
   - Save credentials securely

## Step 4: Prepare Your Code

1. **Clone This Repository** (on your local machine)
   ```bash
   git clone YOUR_REPO_URL
   cd rubri-backend
   ```

2. **Create Environment File**
   ```bash
   cp .env.example .env
   ```

3. **Fill in Required Values** in `.env`:
   - At least one LLM API key (OpenAI, Gemini, etc.)
   - Google OAuth credentials
   - Generate JWT secret: `openssl rand -hex 32`
   - Update domain URLs to match yours

## Step 5: Deploy with Coolify

1. **In Coolify Dashboard**:
   - Click "New Application"
   - Choose "Docker Compose"
   - Connect your GitHub repository

2. **Configure Application**:
   - Set branch to `main` (or your branch)
   - Root directory: `/` (leave empty)
   - Docker Compose file: `docker-compose.yml`

3. **Add Environment Variables**:
   - Go to "Environment Variables" tab
   - Add all variables from your `.env` file
   - Click "Save"

4. **Configure Domains**:
   - Go to "Domains" tab
   - Backend: `https://api.yourdomain.com`
   - Frontend: `https://yourdomain.com,https://www.yourdomain.com`
   - Enable "Generate SSL Certificate"

5. **Deploy**:
   - Click "Deploy"
   - Watch logs for any errors
   - First deployment may take 5-10 minutes

## Step 6: Verify Deployment

1. **Check Services**:
   - Frontend: `https://yourdomain.com`
   - Backend API: `https://api.yourdomain.com/docs`
   - Both should have valid SSL certificates

2. **Test OAuth Login**:
   - Click login button
   - Should redirect to Google
   - After login, should return to your app

## Step 7: Post-Deployment

1. **Monitor Logs** in Coolify:
   - Check for any errors
   - Verify Redis connection
   - Ensure Celery workers are running

2. **Set Up Backups**:
   - SQLite database is in `/app/data/rubri.db`
   - Configure regular backups in Coolify
   - Or set up external backup solution

3. **Configure Google OAuth**:
   - Go to [Google Cloud Console](https://console.cloud.google.com)
   - Create new project or select existing
   - Enable Google+ API
   - Create OAuth 2.0 credentials
   - Add authorized redirect URI: `https://api.yourdomain.com/api/v1/auth/google/callback`

## Troubleshooting

### DNS Issues
- Use `nslookup yourdomain.com` to verify DNS
- Wait up to 48 hours for full propagation
- Check DNS records are correct

### SSL Certificate Issues
- Ensure DNS is properly configured first
- Check Coolify logs for Let's Encrypt errors
- Disable Cloudflare proxy initially if using

### Application Errors
- Check Coolify logs for each service
- Verify environment variables are set
- Ensure Redis is running
- Check SQLite database permissions

### OAuth Issues
- Verify redirect URI matches exactly
- Check Google OAuth credentials
- Ensure JWT_SECRET_KEY is set

## Maintenance

### Updating Code
1. Push changes to GitHub
2. In Coolify, click "Redeploy"
3. Zero-downtime deployment

### Monitoring
- Coolify provides basic monitoring
- Check service health regularly
- Monitor disk space (SQLite grows over time)

### Scaling
- Upgrade Hetzner server if needed
- CX32 (€6.80/month) for more resources
- Consider PostgreSQL for larger scale

## Security Recommendations

1. **Enable Firewall** on Hetzner
   - Allow only necessary ports
   - 80, 443 for web traffic
   - 22 for SSH (restrict to your IP)

2. **Regular Updates**
   ```bash
   apt update && apt upgrade -y
   ```

3. **Secure SSH**
   - Disable password authentication
   - Use SSH keys only
   - Change default SSH port

4. **Monitor Access**
   - Check Coolify logs regularly
   - Set up alerts for failures

## Support

- Coolify Documentation: https://coolify.io/docs
- Hetzner Support: https://docs.hetzner.com
- Project Issues: [Your GitHub Issues URL]

## Cost Summary

- Hetzner CX22: €3.79/month
- Domain: Your existing cost
- SSL Certificates: Free (Let's Encrypt)
- **Total: €3.79/month** (~$4.10)

That's it! Your Rubri application should now be live and accessible via your domain.