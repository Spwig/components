#!/usr/bin/env python3
"""
Test imports for Canada Post provider.

This verifies all modules can be imported without errors.
"""

if __name__ == '__main__':
    try:
        # Import main provider
        from provider import CanadaPostProvider
        print('✓ CanadaPostProvider imported successfully')

        # Import exceptions
        from exceptions import (
            CanadaPostError,
            CanadaPostAuthenticationError,
            CanadaPostValidationError,
            parse_xml_error_response
        )
        print('✓ Exception classes imported successfully')

        # Import retry
        from retry import retry_with_backoff, RetryConfig
        print('✓ Retry logic imported successfully')

        # Import auth
        from auth import CanadaPostAuthClient, create_auth_client
        print('✓ Auth client imported successfully')

        # Import utils
        import utils
        print('✓ Utils module imported successfully')

        # Import XML modules
        import xml_builder
        import xml_parser
        print('✓ XML modules imported successfully')

        # Test some basic functionality
        assert hasattr(CanadaPostProvider, 'provider_key')
        assert hasattr(CanadaPostProvider, 'get_rates')
        assert hasattr(CanadaPostProvider, 'buy_label')
        assert hasattr(CanadaPostProvider, 'get_tracking')
        print('✓ Provider methods exist')

        # Test utils functions exist
        assert callable(utils.format_canadian_postal_code)
        assert callable(utils.validate_customer_number)
        assert callable(utils.map_canada_post_status)
        print('✓ Utils functions exist')

        # Test XML builders exist
        assert callable(xml_builder.build_rate_request)
        assert callable(xml_builder.build_shipment_request)
        print('✓ XML builder functions exist')

        # Test XML parsers exist
        assert callable(xml_parser.parse_rate_response)
        assert callable(xml_parser.parse_shipment_response)
        assert callable(xml_parser.parse_tracking_response)
        print('✓ XML parser functions exist')

        print('\n' + '='*60)
        print('SUCCESS: All imports and basic tests passed!')
        print('='*60)

    except Exception as e:
        print(f'\n✗ ERROR: {e}')
        import traceback
        traceback.print_exc()
        exit(1)
