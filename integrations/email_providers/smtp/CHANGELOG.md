# Changelog

All notable changes to the External SMTP Client Provider will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.4] - 2026-03-03

### Added
- Provider DNS profiles for automatic DKIM selector and SPF include detection
- DNS validation now correctly validates DKIM and SPF for Gmail, Office 365, Outlook.com, SendGrid, Mailgun, and Amazon SES
- Wizard auto-detects the SMTP sub-provider from configured host and applies correct DNS checks

---

## [1.0.3] - 2026-03-02

### Fixed
- Fixed SendResult format to match base class contract
- Fixed EmailMessage field names in MIME builder
- Fixed attachment and inline image content field name
- Fixed validate_credentials signature to match base class
- Fixed healthcheck return format

---

## [1.0.2] - 2026-03-02

### Fixed
- Fixed credential_schema format to use flat field definitions matching platform convention

---

## [1.0.1] - 2026-03-02

### Changed
- Converted HTML files to scoped fragments for CSP compliance
- Added i18n support with Django template tags
- Replaced inline scripts with data-action attributes

---

## [1.0.0] - 2025-10-28

### Added

#### Core Functionality
- Initial release of External SMTP Client Provider
- Support for any standard SMTP server (RFC 5321/5322 compliant)
- TLS encryption support (STARTTLS on port 587)
- SSL encryption support (implicit SSL on port 465)
- SMTP authentication (AUTH LOGIN, AUTH PLAIN)
- Connection pooling and reuse for improved performance

#### Email Features
- HTML and plain text email support
- File attachments with Base64 encoding
- Inline images with Content-ID references
- Custom MIME headers support
- CC and BCC recipient support
- Reply-To header support
- Return-Path for bounce handling
- Email tags and metadata

#### Provider Presets
- Pre-configured settings for Gmail/Google Workspace
- Pre-configured settings for Outlook/Office 365
- Pre-configured settings for SendGrid
- Pre-configured settings for Mailgun
- Pre-configured settings for Amazon SES
- Custom SMTP server support for other providers

#### Security
- Fernet symmetric encryption for credential storage
- TLS/SSL certificate verification
- Secure password handling (app-specific passwords)
- No plaintext credential logging
- Redacted credentials in debug output

#### Documentation
- Comprehensive setup instructions (setup_instructions.html)
- Provider-specific configuration guides
- DNS configuration guide (dns_requirements.html)
- SPF, DKIM, and DMARC setup instructions
- Troubleshooting guide
- API reference documentation
- README with quick start guide

#### Health Checks
- Connection testing via SMTP NOOP command
- Credential validation
- Server capability detection (STARTTLS, AUTH methods)
- Connection timeout handling
- Detailed error reporting

#### Error Handling
- Comprehensive exception handling
- Authentication error detection
- Connection error recovery
- Timeout handling with configurable limits
- Detailed error messages for debugging
- Graceful degradation

### Configuration

#### Credential Schema
```json
{
  "smtp_host": "SMTP server hostname",
  "smtp_port": "SMTP server port (25/465/587)",
  "smtp_username": "Authentication username",
  "smtp_password": "Authentication password",
  "smtp_use_tls": "Enable STARTTLS (boolean)",
  "smtp_use_ssl": "Enable implicit SSL (boolean)",
  "smtp_timeout": "Connection timeout in seconds"
}
```

#### Supported Encryption Methods
- **STARTTLS (port 587)** - Recommended for most providers
- **SSL/TLS (port 465)** - Implicit SSL encryption
- **Plain (port 25)** - Unencrypted (not recommended)

#### Common Provider Settings

| Provider | Host | Port | Auth |
|----------|------|------|------|
| Gmail | smtp.gmail.com | 587/465 | App Password |
| Outlook | smtp.office365.com | 587 | Account Password |
| SendGrid | smtp.sendgrid.net | 587/465 | API Key |
| Mailgun | smtp.mailgun.org | 587/465 | SMTP Password |
| Amazon SES | email-smtp.[region].amazonaws.com | 587/465 | SMTP Credentials |

### Dependencies
- Python 3.10+
- Django 4.2+
- Standard library: smtplib, email.mime, ssl

### Known Issues
- None at this time

### Testing
- Unit tests for provider initialization
- Unit tests for credential validation
- Unit tests for email message building
- Unit tests for SMTP connection handling
- Unit tests for error scenarios
- Integration tests with mock SMTP server

### Performance
- Connection reuse reduces overhead
- Configurable timeouts prevent hanging
- Efficient MIME message construction
- Base64 encoding optimization for attachments

### Limitations
- Maximum attachment size depends on SMTP provider (typically 25MB)
- Rate limits vary by provider
- Some providers require domain verification
- Batch sending not supported (use multiple send() calls)

---

## Future Enhancements

### Planned for v1.1.0
- [ ] OAuth 2.0 support for Gmail/Outlook
- [ ] SMTP connection pooling with max connections limit
- [ ] Retry logic with exponential backoff
- [ ] Delivery status notifications (DSN) support
- [ ] Message queue integration
- [ ] Enhanced logging with structured logs

### Planned for v1.2.0
- [ ] Template support with variable substitution
- [ ] Batch sending optimization
- [ ] Rate limiting enforcement
- [ ] Webhook support for delivery events
- [ ] Advanced bounce handling
- [ ] Email tracking (opens/clicks)

### Under Consideration
- SMTP PIPELINING support for faster sending
- CHUNKING extension for large messages
- SMTPUTF8 support for internationalized email
- Automatic DNS record verification
- Provider-specific optimizations
- Enhanced error recovery strategies

---

## Support

For issues, questions, or feature requests:

1. Check the [README.md](README.md) for documentation
2. Review [setup_instructions.html](setup_instructions.html) for configuration help
3. Consult [dns_requirements.html](dns_requirements.html) for DNS setup
4. Contact your system administrator
5. Refer to your SMTP provider's documentation

---

## License

Proprietary - Copyright © 2025 Spwig. All rights reserved.

This provider is distributed with the Spwig eCommerce platform and is licensed for use with the platform only.

---

**Last Updated**: 2026-03-03
**Current Version**: 1.0.4
**Stability**: Stable
