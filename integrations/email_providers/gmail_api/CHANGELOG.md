# Changelog

All notable changes to the Gmail API email provider will be documented in this file.

## [1.0.4] - 2026-03-03

### Fixed
- Fixed DMARC recommendation to use relaxed alignment (adkim=r; aspf=r) instead of strict
- Strict alignment breaks multi-provider email setups; relaxed alignment is correct for compatibility
- Normalized spf_include value format in manifest (removed include: prefix)

## [1.0.3] - 2026-03-02

### Changed
- Converted HTML files to scoped fragments for CSP compliance
- Added i18n support with Django template tags
- Replaced inline scripts with data-action attributes

## [1.0.2] - 2025-10-29

### Fixed
- Updated HTML templates to use CSS variables for admin theme support
- Fixed CSS class name conflicts

## [1.0.1] - 2025-10-28

### Fixed
- Fixed SVG logo display issue on provider browse page
- Added explicit width and height attributes to logo.svg (88x66px)
- Logo now displays correctly at proper dimensions instead of 0x0

### Technical Details
- Updated logo.svg with `width="88" height="66"` attributes
- Ensures proper rendering in browsers when SVG is used as `<img>` tag
- No functional changes to provider code

## [1.0.0] - 2025-10-25

### Added
- Initial release of Gmail API email provider
- OAuth 2.0 authentication with automatic token refresh
- Send transactional emails via Gmail API
- HTML and plain text email support
- File attachment support (up to 25MB per email)
- Inline image support with Content-ID references
- CC and BCC recipient support
- Custom email headers support
- Reply-To header support
- Encrypted credential storage using Fernet encryption
- Comprehensive error handling:
  - 401 Unauthorized (invalid/expired token)
  - 403 Forbidden (insufficient permissions)
  - 429 Rate Limit Exceeded
  - Network timeout handling
- Health check endpoint via Gmail API profile
- Rate limit information (15/sec, 2000/day for Workspace)
- Credential validation before storage
- Credential redaction for logging security
- Full docstrings and type hints
- Unit test coverage for core functionality
- Integration test examples

### Security
- OAuth tokens encrypted at rest using Fernet symmetric encryption
- Minimal OAuth scope (gmail.send only)
- Sensitive credentials redacted in logs
- HTTPS-only API communication
- Automatic token refresh without exposing credentials

### Documentation
- Comprehensive README with setup instructions
- OAuth 2.0 configuration guide
- Sending limits documentation
- Best practices for production use
- Troubleshooting guide
- Security considerations
- API reference links

### Technical Details
- Provider Key: `gmail_api`
- Class Name: `GmailProvider`
- OAuth Scope: `https://www.googleapis.com/auth/gmail.send`
- API Version: Gmail API v1
- Python Dependencies:
  - google-auth >= 2.41.0
  - google-auth-oauthlib >= 1.2.0
  - google-auth-httplib2 >= 0.2.0
  - google-api-python-client >= 2.185.0

### Limitations
- No webhook support (Gmail API doesn't provide webhooks)
- No email tracking (open/click tracking)
- No batch send support
- Subject to Gmail sending limits (500-2000 emails/day)

## Future Enhancements (Planned)

### v1.1.0
- Batch sending support (send multiple emails in one API call)
- Scheduled sending
- Save sent emails to Gmail "Sent" folder option
- Draft management

### v1.2.0
- Gmail Pub/Sub for bounce notifications
- Enhanced delivery tracking
- Email templates stored in Gmail

### v2.0.0
- Google Workspace admin features
- Domain-wide delegation support
- Advanced routing rules
- Compliance and archiving features
