# DNS Configuration Guide for mongado.com

This guide explains how to configure DNS for mongado.com on Hover.com while preserving your existing Fastmail email service.

## Important: Preserving Email Service

**⚠️ CRITICAL**: You already use Fastmail for email at mongado.com. When adding DNS records for your website, **DO NOT remove or modify any existing MX or email-related records**. Doing so will break your email service.

## Current DNS Setup (Fastmail Email)

Your existing Fastmail configuration should include these records (DO NOT TOUCH):

### MX Records (Email Routing)
```
Type: MX
Name: @
Value: in1-smtp.messagingengine.com
Priority: 10
TTL: 3600

Type: MX
Name: @
Value: in2-smtp.messagingengine.com
Priority: 20
TTL: 3600
```

### SPF Record (Email Authentication)
```
Type: TXT
Name: @
Value: v=spf1 include:spf.messagingengine.com ?all
TTL: 3600
```

### DKIM Records (Email Signing)
```
Type: CNAME
Name: fm1._domainkey
Value: fm1.mongado.com.dkim.fmhosted.com
TTL: 3600

Type: CNAME
Name: fm2._domainkey
Value: fm2.mongado.com.dkim.fmhosted.com
TTL: 3600

Type: CNAME
Name: fm3._domainkey
Value: fm3.mongado.com.dkim.fmhosted.com
TTL: 3600
```

### Email Subdomains (Webmail, IMAP, SMTP)
```
Type: CNAME
Name: mail
Value: mail.messagingengine.com
TTL: 3600

Type: CNAME
Name: imap
Value: imap.fastmail.com
TTL: 3600

Type: CNAME
Name: smtp
Value: smtp.fastmail.com
TTL: 3600
```

## New DNS Records to Add (Website)

After setting up your DigitalOcean droplet, add these A records for your website:

### Get Your Droplet IP Address

1. Log into DigitalOcean
2. Go to Droplets
3. Find your `mongado-prod` droplet
4. Copy the IPv4 address (e.g., `164.90.123.456`)

### Add A Records on Hover.com

Log into Hover.com and add these records:

#### Root Domain (mongado.com)
```
Type: A
Name: @
Value: YOUR_DROPLET_IP_ADDRESS
TTL: 3600 (1 hour)
```

#### WWW Subdomain
```
Type: A
Name: www
Value: YOUR_DROPLET_IP_ADDRESS
TTL: 3600
```

#### API Subdomain
```
Type: A
Name: api
Value: YOUR_DROPLET_IP_ADDRESS
TTL: 3600
```

### Example Configuration

If your droplet IP is `164.90.123.456`, your A records should look like:

```
Type: A    Name: @     Value: 164.90.123.456    TTL: 3600
Type: A    Name: www   Value: 164.90.123.456    TTL: 3600
Type: A    Name: api   Value: 164.90.123.456    TTL: 3600
```

## Complete DNS Table (Email + Website)

After adding the new records, your complete DNS configuration on Hover.com should look like this:

| Type | Name | Value | Priority | TTL |
|------|------|-------|----------|-----|
| **Website Records** |
| A | @ | YOUR_DROPLET_IP | - | 3600 |
| A | www | YOUR_DROPLET_IP | - | 3600 |
| A | api | YOUR_DROPLET_IP | - | 3600 |
| **Email (Fastmail) Records** |
| MX | @ | in1-smtp.messagingengine.com | 10 | 3600 |
| MX | @ | in2-smtp.messagingengine.com | 20 | 3600 |
| TXT | @ | v=spf1 include:spf.messagingengine.com ?all | - | 3600 |
| CNAME | mail | mail.messagingengine.com | - | 3600 |
| CNAME | imap | imap.fastmail.com | - | 3600 |
| CNAME | smtp | smtp.fastmail.com | - | 3600 |
| CNAME | fm1._domainkey | fm1.mongado.com.dkim.fmhosted.com | - | 3600 |
| CNAME | fm2._domainkey | fm2.mongado.com.dkim.fmhosted.com | - | 3600 |
| CNAME | fm3._domainkey | fm3.mongado.com.dkim.fmhosted.com | - | 3600 |

## Step-by-Step Instructions for Hover.com

### 1. Log into Hover.com

1. Go to [hover.com](https://www.hover.com)
2. Click "Sign In"
3. Log in with your credentials

### 2. Navigate to DNS Settings

1. Click on "Domains" in the navigation
2. Find and click on `mongado.com`
3. Click on the "DNS" tab

### 3. Add the A Records

For each A record (root, www, api):

1. Click "Add A Record" (or "Add Record" → select "A")
2. Fill in the fields:
   - **Hostname**: `@` (for root), `www`, or `api`
   - **IP Address**: Your DigitalOcean droplet IP
   - **TTL**: 3600 (or use default)
3. Click "Save" or "Add Record"

### 4. Verify Existing Records

1. Scroll through your DNS records
2. **Confirm** that all MX, TXT, and CNAME records for Fastmail are still present
3. **Do not delete or modify** any email-related records

### 5. Wait for DNS Propagation

- DNS changes typically propagate within 30 minutes to 1 hour
- Maximum propagation time is 48 hours (rare)
- Lower TTL values (like 3600 seconds) propagate faster

## Verifying DNS Configuration

### Check DNS Propagation

From your terminal, run these commands to verify DNS is working:

```bash
# Check root domain
dig mongado.com +short
# Should return: YOUR_DROPLET_IP

# Check www subdomain
dig www.mongado.com +short
# Should return: YOUR_DROPLET_IP

# Check API subdomain
dig api.mongado.com +short
# Should return: YOUR_DROPLET_IP

# Check MX records (email should still work)
dig mongado.com MX +short
# Should return:
# 10 in1-smtp.messagingengine.com.
# 20 in2-smtp.messagingengine.com.

# Check from multiple DNS servers
dig @8.8.8.8 mongado.com +short     # Google DNS
dig @1.1.1.1 mongado.com +short     # Cloudflare DNS
dig @208.67.222.222 mongado.com +short  # OpenDNS
```

### Use Online DNS Tools

Check propagation status globally:
- [whatsmydns.net](https://www.whatsmydns.net/)
- [dnschecker.org](https://dnschecker.org/)

Enter your domain (`mongado.com`) and select "A" record type.

### Verify Email Still Works

After adding website DNS records:

1. **Send a test email** to yourself at `your-email@mongado.com`
2. **Check webmail**: Go to [fastmail.com](https://www.fastmail.com) and log in
3. **Verify SPF/DKIM**: Use [mail-tester.com](https://www.mail-tester.com/)

## What Each Domain Will Point To

After configuration:

| Domain | Points To | Purpose |
|--------|-----------|---------|
| `mongado.com` | Your DigitalOcean droplet | Frontend website |
| `www.mongado.com` | Your DigitalOcean droplet | Frontend website (www redirect) |
| `api.mongado.com` | Your DigitalOcean droplet | Backend API |
| `mail.mongado.com` | Fastmail servers | Email webmail interface |
| `imap.mongado.com` | Fastmail servers | Email IMAP access |
| `smtp.mongado.com` | Fastmail servers | Email SMTP access |
| MX records | Fastmail servers | Email delivery |

## Troubleshooting

### DNS Not Resolving

**Problem**: `dig mongado.com +short` returns nothing or wrong IP

**Solutions**:
1. Wait longer (DNS can take up to 48 hours, though usually 30 min)
2. Check you entered the correct droplet IP in Hover.com
3. Clear your local DNS cache:
   ```bash
   # macOS
   sudo dscacheutil -flushcache; sudo killall -HUP mDNSResponder

   # Linux
   sudo systemd-resolve --flush-caches

   # Windows
   ipconfig /flushdns
   ```
4. Try a different DNS server (8.8.8.8, 1.1.1.1)

### Email Stopped Working

**Problem**: Can't send/receive email after DNS changes

**Solutions**:
1. Log into Hover.com and verify **all Fastmail records are still present**
2. Check MX records: `dig mongado.com MX +short`
3. Check SPF record: `dig mongado.com TXT +short`
4. If records are missing, **immediately re-add them** using the values from "Current DNS Setup" section above
5. Contact Fastmail support if email still not working after 1 hour

### Website Not Loading After DNS Propagation

**Problem**: DNS resolves correctly but site doesn't load

**Solutions**:
1. Verify droplet is running: Log into DigitalOcean and check droplet status
2. Check Nginx is running: SSH into droplet and run `systemctl status nginx`
3. Check Docker containers: `docker ps` should show frontend and backend running
4. Check SSL certificates: `certbot certificates`
5. See full troubleshooting in [DEPLOYMENT.md](DEPLOYMENT.md)

## TTL (Time To Live) Explained

TTL determines how long DNS records are cached:

- **3600 seconds (1 hour)**: Good balance for production
- **300 seconds (5 minutes)**: Use when actively testing/migrating
- **86400 seconds (24 hours)**: Use for stable, rarely-changing records

**Before making DNS changes**: Lower TTL to 300, wait for old TTL to expire, make changes, then raise back to 3600.

## Advanced: Adding a Staging Subdomain

If you want a staging environment (`staging.mongado.com`):

```
Type: A
Name: staging
Value: YOUR_STAGING_DROPLET_IP
TTL: 3600

Type: A
Name: staging-api
Value: YOUR_STAGING_DROPLET_IP
TTL: 3600
```

Then set up SSL certificates on the staging droplet:
```bash
certbot --nginx -d staging.mongado.com -d staging-api.mongado.com
```

## Security Considerations

### CAA Records (Optional but Recommended)

CAA (Certification Authority Authorization) records restrict which CAs can issue SSL certificates for your domain:

```
Type: CAA
Name: @
Value: 0 issue "letsencrypt.org"
TTL: 3600

Type: CAA
Name: @
Value: 0 issuewild "letsencrypt.org"
TTL: 3600
```

This prevents unauthorized SSL certificates from being issued for your domain.

### DNSSEC (Optional)

Some registrars support DNSSEC for additional DNS security. Check if Hover.com offers this feature.

## Related Documentation

- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Complete deployment guide
- **[SETUP.md](SETUP.md)** - Local development setup
- **[ROADMAP.md](ROADMAP.md)** - Future enhancements

## Quick Reference: DNS Changes Checklist

- [ ] Log into Hover.com
- [ ] Get DigitalOcean droplet IP address
- [ ] Add A record: `@` → droplet IP
- [ ] Add A record: `www` → droplet IP
- [ ] Add A record: `api` → droplet IP
- [ ] Verify all Fastmail MX records are still present
- [ ] Verify all Fastmail CNAME records are still present
- [ ] Verify SPF TXT record is still present
- [ ] Wait 30-60 minutes for DNS propagation
- [ ] Verify with `dig mongado.com +short`
- [ ] Verify with `dig mongado.com MX +short`
- [ ] Test email sending/receiving
- [ ] Set up SSL certificates on droplet (after DNS propagates)
- [ ] Visit `https://mongado.com` to confirm site is live

---

**Questions?** Review the Troubleshooting section above or check [DEPLOYMENT.md](DEPLOYMENT.md) for full deployment instructions.
