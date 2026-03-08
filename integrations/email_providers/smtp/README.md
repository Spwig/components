# External SMTP Client Provider

Professional transactional email delivery via external SMTP servers. Supports Gmail, Outlook, SendGrid, Mailgun, Amazon SES, and any standard SMTP server.

**Version**: 1.0.0
**Author**: Spwig
**License**: Proprietary

---

## Overview

The External SMTP Client Provider enables your platform to send transactional emails through any SMTP-compliant email server. This provider supports industry-standard SMTP protocols with TLS/SSL encryption and handles authentication, attachments, inline images, and custom headers.

### Key Features

- ✅ **Universal Compatibility** - Works with any standard SMTP server
- ✅ **Popular Providers** - Pre-configured for Gmail, Outlook, SendGrid, Mailgun, Amazon SES
- ✅ **Secure Connections** - TLS/SSL encryption support
- ✅ **Attachments** - File attachments and inline images
- ✅ **Custom Headers** - Add custom MIME headers
- ✅ **Health Checks** - Built-in connection testing
- ✅ **Error Handling** - Comprehensive error messages and retry logic

### Supported SMTP Providers

This provider includes pre-configured settings for:

- **Gmail** - Personal and Google Workspace accounts
- **Outlook/Office 365** - Microsoft email services
- **SendGrid** - High-volume transactional email service
- **Mailgun** - Developer-friendly email API
- **Amazon SES** - AWS Simple Email Service
- **Custom SMTP** - Any standard SMTP server

---

## Quick Start

### 1. Installation

The SMTP provider is included with the platform. To activate it:

1. Navigate to **Admin → Email System → Email Accounts**
2. Click **Add Email Account**
3. Select **External SMTP Client** as the provider
4. Follow the setup wizard

### 2. Configuration

You'll need the following information from your SMTP provider:

| Setting | Description | Example |
|---------|-------------|---------|
| **SMTP Host** | Server hostname | `smtp.gmail.com` |
| **SMTP Port** | Server port | `587` (TLS) or `465` (SSL) |
| **Username** | Your email address | `you@example.com` |
| **Password** | SMTP password | App-specific password |
| **Use TLS** | Enable TLS encryption | ✓ (recommended) |
| **Use SSL** | Enable SSL encryption | For port 465 |

### 3. DNS Configuration

For optimal deliverability, configure these DNS records:

- **SPF** - Authorize your SMTP server to send emails
- **DKIM** - Cryptographic email signature (if supported by provider)
- **DMARC** - Email authentication policy

See the [DNS Requirements documentation](dns_requirements.html) for provider-specific instructions.

---

## Provider-Specific Setup

### Gmail / Google Workspace

**Requirements:**
- Gmail account or Google Workspace
- 2-Step Verification enabled
- App-specific password

**Configuration:**
```
Host: smtp.gmail.com
Port: 587 (TLS) or 465 (SSL)
Username: your-email@gmail.com
Password: 16-character app password
Use TLS: Yes
```

**Sending Limits:**
- Gmail: 500 emails/day
- Google Workspace: 2,000 emails/day

**Setup Guide:** [Gmail App Passwords](https://support.google.com/accounts/answer/185833)

---

### Outlook / Office 365

**Requirements:**
- Outlook.com or Office 365 account
- SMTP AUTH enabled

**Configuration:**
```
Host: smtp.office365.com (Office 365)
      smtp-mail.outlook.com (Outlook.com)
Port: 587
Username: your-email@outlook.com
Password: Your account password
Use TLS: Yes
```

**Sending Limits:**
- Office 365: 10,000 recipients/day
- Outlook.com: 300 emails/day

---

### SendGrid

**Requirements:**
- SendGrid account (free or paid)
- API key with Mail Send permission

**Configuration:**
```
Host: smtp.sendgrid.net
Port: 587 or 465
Username: apikey (literally the word "apikey")
Password: Your SendGrid API key (starts with SG.)
Use TLS: Yes
```

**Sending Limits:**
- Free: 100 emails/day
- Paid: No daily limits

**Signup:** [SendGrid Free Tier](https://signup.sendgrid.com)

---

### Mailgun

**Requirements:**
- Mailgun account
- Verified sending domain

**Configuration:**
```
Host: smtp.mailgun.org (US) or smtp.eu.mailgun.org (EU)
Port: 587 or 465
Username: Your SMTP username (from dashboard)
Password: Your SMTP password
Use TLS: Yes
```

**Sending Limits:**
- Free: 5,000 emails/month (first 3 months)
- Free forever: 1,000 emails/month

**Signup:** [Mailgun](https://signup.mailgun.com)

---

### Amazon SES

**Requirements:**
- AWS account
- Verified email/domain
- Production access (to send to any address)

**Configuration:**
```
Host: email-smtp.[region].amazonaws.com
Port: 587 or 465
Username: SMTP username (from SES console)
Password: SMTP password (from SES console)
Use TLS: Yes
```

**Regions:**
- US East: `email-smtp.us-east-1.amazonaws.com`
- US West: `email-smtp.us-west-2.amazonaws.com`
- EU: `email-smtp.eu-west-1.amazonaws.com`

**Pricing:** $0.10 per 1,000 emails

**Setup:** [AWS SES Documentation](https://docs.aws.amazon.com/ses/)

---

## Advanced Configuration

### Custom Headers

Add custom MIME headers to emails:

```python
headers = {
    'X-Campaign-ID': 'spring-sale-2025',
    'X-Priority': '1',
    'List-Unsubscribe': '<mailto:unsubscribe@example.com>'
}
```

### Attachments

The provider supports file attachments and inline images:

- **File attachments** - Any file type
- **Inline images** - Embed images in HTML emails with `<img src="cid:image-id">`
- **Size limits** - Depends on SMTP provider (typically 25MB)

### Return Path

Configure bounce handling with custom Return-Path:

```python
return_path = 'bounces@example.com'
```

---

## Troubleshooting

### Authentication Failed

**Symptoms:** "Authentication failed" or "Invalid credentials"

**Solutions:**
1. Verify username and password are correct
2. For Gmail/Outlook, use app-specific passwords
3. Check if SMTP AUTH is enabled for your account
4. Verify 2-step verification is enabled (Gmail)

### Connection Refused

**Symptoms:** "Connection refused" or "Timeout"

**Solutions:**
1. Verify SMTP host and port are correct
2. Check firewall allows outbound connections on SMTP port
3. Ensure your hosting provider doesn't block SMTP
4. Try alternative ports (587 vs 465)

### SSL/TLS Error

**Symptoms:** "SSL handshake failed" or "Certificate error"

**Solutions:**
1. Verify you're using the correct encryption method (TLS vs SSL)
2. Try the alternative port (587 for TLS, 465 for SSL)
3. Check if SSL certificate verification is enabled
4. Ensure the SMTP host supports the encryption method

### Emails Going to Spam

**Symptoms:** Emails land in recipient spam folders

**Solutions:**
1. Configure SPF, DKIM, and DMARC DNS records
2. Verify your sending domain with the provider
3. Avoid spam trigger words in subject lines
4. Include proper unsubscribe links
5. Maintain good sender reputation
6. Warm up your domain gradually

### Sender Address Rejected

**Symptoms:** "Sender address rejected" or "Not authorized"

**Solutions:**
1. Verify sending domain is verified with provider
2. Ensure From address matches authorized sender
3. Check SPF DNS record includes your SMTP provider
4. Verify DKIM is configured correctly

---

## Security

### Credential Storage

- **Encryption**: Credentials are encrypted using Fernet symmetric encryption
- **Key Security**: Encryption keys are stored securely, separate from encrypted data
- **No Plaintext**: Credentials are never logged or stored in plaintext
- **Access Control**: Only authorized admin users can view/edit credentials

### Connection Security

- **TLS/SSL Required**: All connections use encrypted transport
- **Certificate Validation**: SSL certificates are verified by default
- **No Plaintext Auth**: Credentials are never sent over unencrypted connections

### Best Practices

1. **Use app-specific passwords** - Never use main account passwords
2. **Enable 2FA** - Add two-factor authentication where supported
3. **Rotate credentials** - Change passwords periodically
4. **Limit permissions** - Use minimal required permissions
5. **Monitor activity** - Watch for unauthorized sending
6. **Separate accounts** - Use dedicated accounts for transactional email

---

## Performance

### Connection Pooling

The provider maintains SMTP connections for efficiency:

- **Reuse connections** - Multiple emails use same connection
- **Automatic reconnect** - Handles disconnections gracefully
- **Timeout handling** - Configurable connection timeouts

### Rate Limiting

Be aware of provider rate limits:

| Provider | Emails/Second | Emails/Day | Emails/Month |
|----------|---------------|------------|--------------|
| Gmail | ~15 | 500 | ~15,000 |
| Google Workspace | ~15 | 2,000 | ~60,000 |
| Outlook.com | - | 300 | ~9,000 |
| Office 365 | - | 10,000 | ~300,000 |
| SendGrid | 100+ | Unlimited* | Unlimited* |
| Mailgun | 100+ | Unlimited* | Plan-based |
| Amazon SES | Variable | Variable | Unlimited* |

*Subject to plan limits

### Optimization Tips

1. **Batch sending** - Send multiple emails in one connection
2. **Async processing** - Use Celery for background sending
3. **Error handling** - Implement retry logic for failures
4. **Monitor queues** - Watch for stuck/failed emails

---

## API Reference

### Provider Class

```python
from components.integrations.email_providers.smtp.v1.0.0.provider import SMTPProvider

# Initialize provider
provider = SMTPProvider(credentials={
    'smtp_host': 'smtp.gmail.com',
    'smtp_port': 587,
    'smtp_username': 'user@gmail.com',
    'smtp_password': 'app-password',
    'smtp_use_tls': True,
    'smtp_use_ssl': False
})

# Send email
result = provider.send({
    'message_id': 'unique-id',
    'from_email': 'sender@example.com',
    'from_name': 'Sender Name',
    'to': ['recipient@example.com'],
    'subject': 'Test Email',
    'html': '<p>Hello World</p>',
    'text': 'Hello World',
    'attachments': [],
    'inline_images': [],
    'headers': {},
    'return_path': 'bounces@example.com',
    'cc': [],
    'bcc': [],
    'tags': [],
    'metadata': {}
})

# Check health
health = provider.healthcheck()
```

### Methods

#### `send(message: EmailMessage) -> SendResult`

Sends an email message via SMTP.

**Parameters:**
- `message` (EmailMessage): Email message dictionary

**Returns:**
- `SendResult`: Send status and provider message ID

**Raises:**
- `SMTPAuthenticationError`: Invalid credentials
- `SMTPServerDisconnected`: Connection lost
- `SMTPException`: SMTP protocol error

#### `healthcheck() -> dict`

Tests SMTP connection and credentials.

**Returns:**
- Dictionary with `success`, `message`, and `details` keys

#### `validate_credentials(credentials: dict) -> None`

Validates credential format and values.

**Raises:**
- `ValueError`: Invalid or missing credentials

---

## Support

### Documentation

- [Setup Instructions](setup_instructions.html)
- [DNS Configuration](dns_requirements.html)
- [Email Provider Development Guide](/.claude_code/email/PROVIDER_DEVELOPMENT.md)

### Common Issues

- [Troubleshooting Guide](#troubleshooting)
- [Security Best Practices](#security)
- [Performance Optimization](#performance)

### Contact

- **Platform Issues**: Contact your system administrator
- **Provider Issues**: Contact your SMTP provider's support

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history and updates.

---

## License

Proprietary - Copyright © 2025 Spwig. All rights reserved.

This provider is distributed with the Spwig eCommerce platform and is licensed for use with the platform only.
