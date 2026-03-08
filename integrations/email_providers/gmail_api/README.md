# Gmail API Email Provider

Send transactional emails via Gmail API with OAuth 2.0 authentication.

## Overview

This provider allows you to send transactional emails using your Gmail or Google Workspace account through the Gmail API. It uses OAuth 2.0 for secure authentication and supports all standard email features including attachments, inline images, CC/BCC, and custom headers.

## Features

- **OAuth 2.0 Authentication** - Secure authentication with automatic token refresh
- **HTML & Plain Text** - Send both HTML and plain text email versions
- **Attachments** - Support for file attachments up to 25MB
- **Inline Images** - Embed images in HTML emails using Content-ID
- **CC & BCC** - Send to multiple recipients
- **Custom Headers** - Add custom email headers
- **Rate Limiting** - Built-in rate limit handling
- **Error Handling** - Comprehensive error handling and retry logic

## Sending Limits

### Standard Gmail Account
- **500 emails per day**
- 15 emails per second (burst)

### Google Workspace Account
- **2,000 emails per day**
- 15 emails per second (burst)

## Requirements

- Google Cloud Console project
- Gmail API enabled
- OAuth 2.0 client credentials
- OAuth consent screen configured

## Setup Instructions

See the detailed setup instructions in the admin interface when configuring this provider.

### Quick Setup Steps

1. **Create Google Cloud Project**
   - Go to [Google Cloud Console](https://console.cloud.google.com)
   - Create a new project or select existing one

2. **Enable Gmail API**
   - In your project, go to "APIs & Services" > "Library"
   - Search for "Gmail API" and enable it

3. **Create OAuth Credentials**
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Application type: "Web application"
   - Add authorized redirect URI: `https://yourdomain.com/admin/email_system/oauth/callback/gmail_api/`

4. **Configure OAuth Consent Screen**
   - Go to "APIs & Services" > "OAuth consent screen"
   - Add required information
   - Add scope: `https://www.googleapis.com/auth/gmail.send`

5. **Connect in Platform**
   - Go to Email Providers in admin
   - Add Gmail API provider
   - Complete OAuth flow to authorize access

## OAuth Scopes

This provider requires the following OAuth scope:

- `https://www.googleapis.com/auth/gmail.send` - Send email on your behalf

This is the most restrictive Gmail scope that only allows sending emails. It does not grant read access to your inbox.

## Best Practices

### For Transactional Emails

1. **Use Google Workspace** - Higher sending limits (2,000/day vs 500/day)
2. **Monitor Sending Limits** - Track your daily usage
3. **Implement Retry Logic** - Handle rate limits gracefully
4. **Use Plain Text Alternative** - Always provide plain text version
5. **Test Thoroughly** - Test with various email clients

### For Production Use

1. **Dedicated Email Account** - Use separate account for transactional emails
2. **Configure SPF/DKIM** - Ensure proper email authentication
3. **Monitor Bounces** - Track delivery failures
4. **Rate Limit Handling** - Implement queue with rate limiting
5. **Token Refresh** - OAuth tokens are automatically refreshed

## Security Considerations

- **OAuth Tokens** - Securely encrypted in database using Fernet encryption
- **Least Privilege** - Uses minimal OAuth scope (send only)
- **Token Expiry** - Automatic token refresh
- **Secure Storage** - Credentials never logged in plain text
- **HTTPS Only** - All API calls over HTTPS

## Troubleshooting

### Authentication Errors (401)
- Token may have expired - provider will automatically refresh
- Check OAuth consent screen configuration
- Verify OAuth scopes are correct

### Permission Errors (403)
- Insufficient OAuth scopes
- Gmail API not enabled in Google Cloud Console
- Account may be suspended or restricted

### Rate Limit Errors (429)
- Exceeded daily sending limit (500 or 2,000 emails)
- Exceeded burst limit (15 emails/second)
- Implement exponential backoff retry

### Invalid Recipients
- Verify email addresses are valid
- Check for typos in email addresses
- Ensure recipients haven't blocked your domain

## API Reference

### Gmail API Documentation
- [Gmail API Overview](https://developers.google.com/gmail/api/guides)
- [Sending Email](https://developers.google.com/gmail/api/guides/sending)
- [API Reference](https://developers.google.com/gmail/api/reference/rest)

### Rate Limits
- [Gmail API Quotas](https://developers.google.com/gmail/api/reference/quota)

## Support

For issues or questions:
- Platform Support: support@spwig.com
- Gmail API Issues: [Google Workspace Support](https://support.google.com/a)

## Version

**v1.0.0** - Initial release

See [CHANGELOG.md](CHANGELOG.md) for version history.
