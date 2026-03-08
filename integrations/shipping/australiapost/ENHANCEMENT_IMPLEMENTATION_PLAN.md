# Australia Post Provider v2.0.0 - Enhancement Implementation Plan

**Version**: 2.0.0
**Start Date**: 2025-11-06
**Target Completion**: 20 days
**Purpose**: Implement full Australia Post lodgement validation requirements

---

## Overview

This document tracks the implementation of all features required to meet Australia Post's production lodgement validation requirements. Version 2.0.0 represents a major enhancement from v1.0.1, adding critical order management, basket management, validation services, and advanced features.

---

## Phase 1: Project Setup & Order Management (Days 1-4)

### Project Setup
- [x] Copy v1.0.1 to v2.0.0 directory structure
- [x] Create ENHANCEMENT_IMPLEMENTATION_PLAN.md
- [ ] Update manifest.json version to 2.0.0
- [ ] Create changelog entry for v2.0.0

### Order Management API Implementation

#### Create Order from Shipments
- [ ] Add `PUT /shipping/v1/orders` endpoint to API client
- [ ] Implement `create_order()` method
- [ ] Add request payload builder for order creation
- [ ] Handle order creation response parsing
- [ ] Implement error handling for order creation failures
- [ ] Add order ID tracking and storage

#### Get Order Details
- [ ] Add `GET /shipping/v1/accounts/{account}/orders/{order_id}` endpoint
- [ ] Implement `get_order()` method
- [ ] Parse order response data
- [ ] Handle order not found errors
- [ ] Cache order details appropriately

#### Get Order Summary (Manifest)
- [ ] Add `GET /shipping/v1/accounts/{account}/orders/{order_id}/summary` endpoint
- [ ] Implement `get_order_summary()` method
- [ ] Parse manifest data
- [ ] Support manifest PDF download
- [ ] Handle summary generation errors

#### Order Size Management
- [ ] Implement order size validation (max 2,000 items)
- [ ] Create `split_large_order()` function
- [ ] Add logic to split shipments across multiple orders
- [ ] Track multiple order IDs from splits
- [ ] Add configuration for order size limits

#### Order Manager Class
- [ ] Create `OrderManager` class
- [ ] Add order state tracking
- [ ] Implement order validation logic
- [ ] Add order history tracking
- [ ] Create order status enumeration

### Unit Tests - Order Management
- [ ] Test create_order() with valid data
- [ ] Test create_order() with invalid data
- [ ] Test order size validation
- [ ] Test order splitting logic (>2,000 items)
- [ ] Test get_order() retrieval
- [ ] Test get_order_summary() manifest generation
- [ ] Test error handling for all order operations
- [ ] Test multiple order creation from splits

---

## Phase 2: Basket Management (Days 5-7)

### Basket Manager Implementation

#### Basket Size Tracking
- [ ] Create `BasketManager` class
- [ ] Implement basket size counter (max 10,000 items)
- [ ] Add basket item tracking
- [ ] Create basket limit validation
- [ ] Implement basket overflow warnings
- [ ] Add basket size reporting

#### Basket State Management
- [ ] Implement basket state persistence
- [ ] Add basket clear functionality
- [ ] Track completed vs pending shipments
- [ ] Implement basket snapshot feature
- [ ] Add basket recovery logic

### Shipment Management Enhancements

#### Get Shipment(s)
- [ ] Add `GET /shipping/v1/shipments/{id}` endpoint
- [ ] Implement `get_shipment()` method
- [ ] Add `GET /shipping/v1/shipments` endpoint (list)
- [ ] Implement `get_shipments()` with filters
- [ ] Parse shipment detail responses
- [ ] Handle pagination for large shipment lists
- [ ] Add shipment search/filter capabilities

#### Update Shipment
- [ ] Add `PUT /shipping/v1/shipments/{id}` endpoint
- [ ] Implement `update_shipment()` method
- [ ] Create shipment update payload builder
- [ ] Validate updatable fields
- [ ] Handle update conflicts
- [ ] Track shipment modification history

#### Item-Level Operations
- [ ] Add `DELETE /shipping/v1/shipments/{shipment_id}/items/{item_id}` endpoint
- [ ] Implement `delete_item()` method
- [ ] Add `PUT /shipping/v1/shipments/{shipment_id}/items/{item_id}` endpoint
- [ ] Implement `update_item()` method
- [ ] Validate item-level operations
- [ ] Handle item not found errors

### Unit Tests - Basket Management
- [ ] Test BasketManager initialization
- [ ] Test basket size tracking (add/remove)
- [ ] Test basket limit validation (10,000 items)
- [ ] Test basket overflow handling
- [ ] Test get_shipment() retrieval
- [ ] Test get_shipments() with various filters
- [ ] Test update_shipment() modifications
- [ ] Test delete_item() operations
- [ ] Test update_item() operations
- [ ] Test basket state persistence
- [ ] Test basket clearing and recovery

---

## Phase 3: Validation Services (Days 8-10)

### Validation Service Implementation

#### Validate Suburb (Address Validation)
- [ ] Add `POST /shipping/v1/postcode/validate` endpoint
- [ ] Implement `validate_suburb()` method
- [ ] Create suburb validation request payload
- [ ] Parse validation response
- [ ] Handle invalid suburb errors
- [ ] Add suburb suggestion logic
- [ ] Cache valid suburbs

#### Validate Shipments
- [ ] Add `POST /shipping/v1/shipments/validate` endpoint
- [ ] Implement `validate_shipments()` method
- [ ] Create validation request builder
- [ ] Parse validation errors and warnings
- [ ] Return detailed validation results
- [ ] Integrate with shipment creation workflow

#### Lookup Serviceability
- [ ] Add `POST /shipping/v1/serviceability` endpoint
- [ ] Implement `lookup_serviceability()` method
- [ ] Create serviceability request payload
- [ ] Parse serviceability response
- [ ] Handle unserviceable addresses
- [ ] Add service availability checking

### Validation Service Class
- [ ] Create `ValidationService` class
- [ ] Implement validation result caching
- [ ] Add validation error aggregation
- [ ] Create validation report generator
- [ ] Implement pre-flight validation workflow

### Integration with Shipment Workflow
- [ ] Add optional validation to create_shipment()
- [ ] Implement automatic suburb validation
- [ ] Add serviceability checks before rating
- [ ] Create validation bypass option
- [ ] Add validation logging

### Unit Tests - Validation Services
- [ ] Test validate_suburb() with valid postcodes
- [ ] Test validate_suburb() with invalid postcodes
- [ ] Test suburb suggestion handling
- [ ] Test validate_shipments() success cases
- [ ] Test validate_shipments() error cases
- [ ] Test lookup_serviceability() for serviceable addresses
- [ ] Test lookup_serviceability() for unserviceable addresses
- [ ] Test validation caching
- [ ] Test validation workflow integration

---

## Phase 4: Feature Enhancements (Days 11-14)

### Product Feature Flags

#### Authority To Leave (ATL)
- [ ] Add `authority_to_leave` field to shipment request
- [ ] Implement ATL configuration
- [ ] Add ATL validation rules
- [ ] Support product-specific ATL availability
- [ ] Add ATL to feature matrix

#### Safe Drop
- [ ] Add `safe_drop` field to shipment request
- [ ] Implement Safe Drop configuration
- [ ] Add Safe Drop validation
- [ ] Support product-specific Safe Drop availability
- [ ] Add Safe Drop instructions field

#### Signature on Delivery
- [ ] Add `signature_on_delivery` field to shipment request
- [ ] Implement signature requirement configuration
- [ ] Add signature validation rules
- [ ] Support product-specific signature requirements
- [ ] Add signature type options

#### Allow Partial Delivery
- [ ] Add `allow_partial_delivery` field
- [ ] Implement partial delivery configuration
- [ ] Add validation for multi-item shipments
- [ ] Support product-specific partial delivery

#### Delivery Instructions
- [ ] Add `delivery_instructions` field
- [ ] Implement instruction length validation
- [ ] Add instruction formatting rules
- [ ] Support product-specific instruction fields

### Dangerous Goods Support
- [ ] Add `dangerous_goods` declaration field
- [ ] Implement DG class validation
- [ ] Add UN number support
- [ ] Create DG packaging requirements
- [ ] Add DG product restrictions
- [ ] Implement DG validation rules
- [ ] Add DG to feature matrix

### Enhanced Pricing

#### Get Shipment Price
- [ ] Add `POST /shipping/v1/prices/items` endpoint
- [ ] Implement `get_shipment_price()` method
- [ ] Create item pricing request builder
- [ ] Parse individual item pricing
- [ ] Support multiple pricing scenarios
- [ ] Add pricing comparison logic

#### Calculate ETA
- [ ] Add `POST /shipping/v1/eta` endpoint
- [ ] Implement `calculate_eta()` method
- [ ] Create ETA request payload
- [ ] Parse ETA response
- [ ] Handle multiple delivery date options
- [ ] Add ETA to quote response

### Charge Code Expiry Management
- [ ] Enhance Get Accounts API call to retrieve expiry dates
- [ ] Implement expiry date parsing
- [ ] Add expiry date caching
- [ ] Create expiry warning system
- [ ] Implement automatic expiry checking
- [ ] Add expiry notification to merchants

### Multiple Product Type Support

#### eParcel Support
- [ ] Configure eParcel account number format (10 digits, prefix 2)
- [ ] Add eParcel product codes
- [ ] Implement eParcel-specific features
- [ ] Add eParcel validation rules

#### StarTrack Support
- [ ] Configure StarTrack account number format (8 digits)
- [ ] Add StarTrack product codes (Premium, Express)
- [ ] Implement StarTrack-specific features
- [ ] Add StarTrack validation rules

#### Same Day Services Support
- [ ] Configure Same Day account number format (10 digits, prefix 3)
- [ ] Add Same Day product codes
- [ ] Implement Same Day-specific features
- [ ] Add Same Day validation rules

#### On Demand Support
- [ ] Configure On Demand account number format (10 digits, prefix 1)
- [ ] Add On Demand product codes
- [ ] Implement On Demand-specific features
- [ ] Add On Demand validation rules

### Feature Matrix
- [ ] Create product-feature compatibility matrix
- [ ] Implement feature availability checking
- [ ] Add feature validation per product
- [ ] Create feature documentation
- [ ] Add feature configuration UI hints

### Unit Tests - Feature Enhancements
- [ ] Test all feature flags individually
- [ ] Test feature flag combinations
- [ ] Test product-specific feature restrictions
- [ ] Test DG validation rules
- [ ] Test get_shipment_price() calculations
- [ ] Test calculate_eta() responses
- [ ] Test charge code expiry detection
- [ ] Test all 4 account types
- [ ] Test product feature matrix
- [ ] Test feature validation logic

---

## Phase 5: Advanced Features (Days 15-16)

### Adhoc Pickup Scheduling
- [ ] Add `POST /shipping/v1/pickups` endpoint
- [ ] Implement `create_adhoc_pickup()` method
- [ ] Create pickup request payload builder
- [ ] Add pickup time slot selection
- [ ] Implement pickup address validation
- [ ] Parse pickup confirmation response
- [ ] Add pickup cancellation support
- [ ] Track pickup requests

### SSCC Barcoding
- [ ] Add `sscc_barcode` support to shipment request
- [ ] Implement SSCC generation logic
- [ ] Add SSCC validation (18 digits)
- [ ] Support custom SSCC input
- [ ] Add SSCC to label generation
- [ ] Implement SSCC tracking

### Returns Shipment Handling
- [ ] Add `return` flag to shipment request
- [ ] Implement returns-specific validation
- [ ] Add return address handling
- [ ] Support return product codes
- [ ] Implement return label generation
- [ ] Add return tracking capabilities

### Label Format Options
- [ ] Document current PDF support
- [ ] Add label layout options (A6, A4, thermal)
- [ ] Support branded vs unbranded labels
- [ ] Implement label combination options
- [ ] Add label format configuration
- [ ] Note ZPL format for future implementation

### Enhanced Tracking
- [ ] Add tracking event details
- [ ] Implement tracking history retrieval
- [ ] Add proof of delivery support
- [ ] Support tracking notifications
- [ ] Add tracking status webhooks (future)

### Unit Tests - Advanced Features
- [ ] Test adhoc pickup creation
- [ ] Test pickup time slot validation
- [ ] Test pickup cancellation
- [ ] Test SSCC generation and validation
- [ ] Test returns shipment creation
- [ ] Test return label generation
- [ ] Test label format options
- [ ] Test enhanced tracking features

---

## Phase 6: Comprehensive Testing (Days 17-19)

### Integration Test Suite

#### Test Account Setup
- [ ] Configure eParcel testbed account (2004952470)
- [ ] Configure Same Day testbed account (3004952470)
- [ ] Configure StarTrack testbed account (04952470)
- [ ] Configure On Demand testbed account (14952470)
- [ ] Verify API key authentication for all accounts
- [ ] Test account validation for all types

#### Complete Workflow Tests

##### eParcel Workflow
- [ ] Test validate suburb → create shipment → create order → generate labels → track
- [ ] Test with Authority To Leave
- [ ] Test with Safe Drop
- [ ] Test with Signature required
- [ ] Test with Dangerous Goods
- [ ] Test domestic vs international

##### StarTrack Workflow
- [ ] Test StarTrack Premium workflow
- [ ] Test StarTrack Express workflow
- [ ] Test with transfers
- [ ] Test with book-ins
- [ ] Test with transit cover

##### Same Day Services Workflow
- [ ] Test same day delivery workflow
- [ ] Test time slot selection
- [ ] Test adhoc pickup
- [ ] Test delivery on date

##### On Demand Workflow
- [ ] Test on demand delivery workflow
- [ ] Test adhoc pickup scheduling
- [ ] Test deliver on date feature

#### Basket & Order Tests
- [ ] Test basket with <100 items
- [ ] Test basket with 100-1,000 items
- [ ] Test basket with 1,000-10,000 items
- [ ] Test basket limit exceeded (>10,000)
- [ ] Test order with <100 items
- [ ] Test order with 100-2,000 items
- [ ] Test order splitting (>2,000 items)
- [ ] Test multiple order creation
- [ ] Test update shipment in basket
- [ ] Test delete shipment from basket
- [ ] Test update item in shipment
- [ ] Test delete item from shipment

#### Error Scenario Tests
- [ ] Test invalid API key (401)
- [ ] Test invalid account number (40001)
- [ ] Test account not found (41001)
- [ ] Test expired contract (41003)
- [ ] Test missing required fields (40002)
- [ ] Test service unavailable (503)
- [ ] Test timeout recovery (55 seconds)
- [ ] Test invalid suburb validation
- [ ] Test unserviceable address
- [ ] Test rate limit exceeded (tracking)
- [ ] Test basket overflow
- [ ] Test order size exceeded
- [ ] Test invalid product codes
- [ ] Test incompatible feature flags

#### Rate Limiting Tests
- [ ] Test tracking rate limit (10 req/60s)
- [ ] Test concurrent tracking requests
- [ ] Test token bucket refill
- [ ] Test rate limit backoff
- [ ] Test bulk tracking operations

#### Product Feature Tests
- [ ] Test Authority To Leave across all products
- [ ] Test Safe Drop across supported products
- [ ] Test Signature on Delivery across all products
- [ ] Test Allow Partial Delivery
- [ ] Test Dangerous Goods (eParcel, StarTrack)
- [ ] Test Returns across all products
- [ ] Test Transfers (StarTrack only)
- [ ] Test SSCC Barcoding
- [ ] Test Book-ins (StarTrack only)
- [ ] Test Transit Cover
- [ ] Test Deliver On Date

#### Performance Tests
- [ ] Test label generation for 250+ parcels (async mode)
- [ ] Test async polling mechanism
- [ ] Test bulk shipment creation
- [ ] Test large basket operations
- [ ] Test multiple order splits
- [ ] Test concurrent API calls

### Test Infrastructure

#### Reusable Test Fixtures
- [ ] Create address fixtures (valid suburbs)
- [ ] Create invalid address fixtures
- [ ] Create shipment data fixtures
- [ ] Create order data fixtures
- [ ] Create product code fixtures
- [ ] Create error response fixtures
- [ ] Create tracking response fixtures

#### Mock Data
- [ ] Create mock API responses for all endpoints
- [ ] Create mock error responses
- [ ] Create mock validation responses
- [ ] Create mock tracking data
- [ ] Create mock order summaries

#### Test Utilities
- [ ] Create test account manager
- [ ] Create test data generator
- [ ] Create assertion helpers
- [ ] Create API mock server
- [ ] Create test reporting tools

### Test Documentation
- [ ] Document test setup instructions
- [ ] Create test account guide
- [ ] Document test scenarios
- [ ] Create test data reference
- [ ] Add troubleshooting guide

---

## Phase 7: Documentation & Packaging (Day 20)

### Documentation Updates

#### README Updates
- [ ] Update introduction and overview
- [ ] Document complete workflow (validate → basket → order → labels)
- [ ] Add order management section
- [ ] Add basket management section
- [ ] Add validation services section
- [ ] Document all product features
- [ ] Add multiple account type handling
- [ ] Document limits and constraints (10,000 basket, 2,000 order)
- [ ] Add troubleshooting section
- [ ] Update examples with new features

#### Setup Instructions
- [ ] Update setup_instructions.html
- [ ] Add order workflow configuration
- [ ] Add feature selection guide
- [ ] Add account type selection wizard
- [ ] Add validation configuration
- [ ] Add limits configuration
- [ ] Update screenshots and visuals

#### API Reference
- [ ] Document all Order Management endpoints
- [ ] Document Basket Management endpoints
- [ ] Document Validation Service endpoints
- [ ] Document Enhanced Pricing endpoints
- [ ] Document Advanced Feature endpoints
- [ ] Add request/response examples for all endpoints
- [ ] Update error code reference
- [ ] Add feature flag reference

#### Feature Documentation
- [ ] Document Authority To Leave (ATL)
- [ ] Document Safe Drop
- [ ] Document Signature on Delivery
- [ ] Document Dangerous Goods requirements
- [ ] Document Returns handling
- [ ] Document SSCC Barcoding
- [ ] Document Adhoc Pickups
- [ ] Document all product-specific features

### Manifest Updates
- [ ] Update version to 2.0.0
- [ ] Add new capabilities to manifest
- [ ] Update requirements and dependencies
- [ ] Add configuration schema for new features
- [ ] Update limits configuration
- [ ] Add feature flags to manifest
- [ ] Update compatibility information

### Changelog
- [ ] Create v2.0.0 changelog entry
- [ ] Document all new features
- [ ] Document breaking changes (if any)
- [ ] Add migration guide from v1.0.1
- [ ] List all new API endpoints
- [ ] Document new configuration options

### Packaging
- [ ] Run final integration tests
- [ ] Validate manifest.json
- [ ] Check all dependencies
- [ ] Create distribution package
- [ ] Generate package checksum
- [ ] Test package installation
- [ ] Prepare upgrade server deployment

### Upgrade Server
- [ ] Upload package to upgrade server
- [ ] Update package registry
- [ ] Test package download
- [ ] Verify installation from upgrade server
- [ ] Create release notes

---

## Deferred Features (Future Versions)

### v2.1.0 - International Enhancements
- [ ] International customs declarations
- [ ] Export classification codes
- [ ] Combined Export Tool integration
- [ ] Commercial invoice generation
- [ ] HS code validation

### v2.2.0 - Label Enhancements
- [ ] ZPL format support (thermal printers)
- [ ] Custom label templates
- [ ] Multi-language labels
- [ ] Barcode customization

### v2.3.0 - Advanced Integration
- [ ] Dangerous Goods form generation (StarTrack)
- [ ] Multi-parcel optimization
- [ ] Batch processing improvements
- [ ] Webhook notifications
- [ ] Real-time tracking webhooks

---

## Success Metrics

### Functionality
- [ ] All lodgement validation requirements met
- [ ] All 4 account types fully supported
- [ ] All product features implemented
- [ ] Complete workflow validated
- [ ] Error handling comprehensive

### Testing
- [ ] 100% unit test coverage for new code
- [ ] All integration tests passing on testbed
- [ ] All error scenarios tested
- [ ] All account types tested
- [ ] Performance benchmarks met

### Documentation
- [ ] Complete API documentation
- [ ] Merchant-friendly setup guide
- [ ] Comprehensive troubleshooting
- [ ] Feature comparison matrix
- [ ] Migration guide complete

### Quality
- [ ] Code review completed
- [ ] No critical bugs
- [ ] Performance optimized
- [ ] Security validated
- [ ] Production-ready status achieved

---

## Notes & Decisions

### Design Decisions
- Order splitting happens automatically when >2,000 items
- Basket size warnings at 8,000 items (before 10,000 limit)
- Validation is optional but recommended by default
- Feature flags are product-aware and auto-validated
- Charge code expiry checked daily via background task

### Technical Decisions
- Order Manager uses state machine pattern
- Basket Manager implements persistence layer
- Validation Service uses caching for performance
- Feature matrix is configuration-driven
- Test fixtures are version-controlled

### Known Limitations
- International customs deferred to v2.1.0
- ZPL labels deferred to v2.2.0
- Webhook support deferred to v2.3.0
- DG forms (StarTrack) deferred to v2.3.0

---

## Progress Tracking

**Current Phase**: Phase 1 - Project Setup & Order Management
**Current Status**: Setting up v2.0.0 structure
**Completion**: 2/28 major tasks completed (7%)
**On Track**: Yes
**Blockers**: None
**Next Milestone**: Complete Order Management implementation

---

*Last Updated: 2025-11-06*
*Document Version: 1.0*
