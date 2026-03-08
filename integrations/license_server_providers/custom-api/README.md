# Custom API License Provider

**Version:** 1.0.0
**Author:** Spwig
**Type:** License Server Provider Component

## Overview

Connect your own license server to Spwig via REST API. Perfect for merchants with existing license management systems who want to maintain full control over their data and infrastructure.

## Features

- ✅ **Custom Integration** - Use your existing license server
- ✅ **Flexible Authentication** - Bearer, API Key, Basic Auth, or Custom headers
- ✅ **Endpoint Mapping** - Map operations to your custom endpoints
- ✅ **Full Control** - All data stays on your servers
- ✅ **No Third-Party** - No external dependencies

## Setup

1. Ensure your license server implements the required API endpoints
2. Configure HTTPS for secure communication
3. Prepare your API base URL and authentication credentials
4. Optional: Configure custom endpoint mappingif your endpoints differ from defaults
5. Connect via Spwig wizard

## Required API Endpoints

Your license server must implement these endpoints:

### Create License
```
POST /licenses
Body: {
  "license_key": "XXXXX-XXXXX-XXXXX",
  "product_id": "123",
  "max_activations": 5,
  ...
}
```

### Validate License
```
GET /licenses/{key}/validate
Response: {
  "valid": true,
  "license_key": "XXXXX-XXXXX-XXXXX"
}
```

### Activate Device
```
POST /licenses/{key}/activate
Body: {
  "device_fingerprint": "abc123",
  "device_name": "MacBook Pro"
}
```

### Deactivate Device
```
POST /licenses/{key}/deactivate
Body: {
  "device_fingerprint": "abc123"
}
```

## API Specification

Full API specification: [spwig.com/docs/custom-license-api/spec](https://spwig.com/docs/custom-license-api/spec)

## Support

- **Docs:** [spwig.com/docs/custom-license-api](https://spwig.com/docs/custom-license-api)
- **Support:** [spwig.com/support](https://spwig.com/support)

## Changelog

See [CHANGELOG.md](CHANGELOG.md)
