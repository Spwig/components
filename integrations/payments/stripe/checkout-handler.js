/* © 2025 Spwig. All rights reserved. */

/**
 * Stripe Checkout Handler
 *
 * Dynamically loaded plugin for Stripe embedded payment integration.
 * Implements the standard PaymentHandlers interface for Spwig platform.
 *
 * Uses Stripe Elements v2 Payment Element for unified payment experience.
 * Supports cards, digital wallets, BNPL automatically based on customer location.
 *
 * @version 1.1.1
 * @author Spwig
 */
(function() {
    'use strict';

    // Initialize global payment handlers registry
    window.PaymentHandlers = window.PaymentHandlers || {};

    /**
     * Stripe Payment Handler
     * Registers itself in the global handlers registry
     */
    window.PaymentHandlers.stripe = {
        // Store Stripe instances for cleanup
        _stripe: null,
        _elements: null,
        _paymentElement: null,

        /**
         * Initialize Stripe embedded checkout
         *
         * @param {object} intentData - Payment intent response from API
         * @param {object} intentData.handler_config - Stripe-specific configuration
         * @param {string} intentData.handler_config.intent_id - Stripe PaymentIntent ID
         * @param {string} intentData.handler_config.publishable_key - Stripe publishable key
         * @param {string} intentData.handler_config.currency - ISO currency code (e.g., 'USD')
         * @param {string} intentData.handler_config.country_code - ISO country code (e.g., 'US')
         * @param {string} intentData.handler_config.environment - 'test' or 'live'
         * @param {string} intentData.client_secret - Client secret for intent confirmation
         * @param {string} intentData.order_number - Order number for confirmation redirect
         * @param {HTMLElement} container - Container element for payment form
         * @param {function} onSuccess - Callback when payment succeeds (orderNumber)
         * @param {function} onError - Callback when payment fails (errorMessage)
         * @returns {Promise<void>}
         */
        async initialize(intentData, container, onSuccess, onError) {
            try {
                const config = intentData.handler_config;

                // Validate required configuration
                if (!config || !config.intent_id || !config.publishable_key || !config.currency) {
                    throw new Error('Missing required Stripe configuration');
                }

                if (!intentData.client_secret) {
                    throw new Error('Missing client_secret in payment intent data');
                }

                // Wait for Stripe.js to be available
                console.log('[Stripe] Waiting for SDK to load...');
                await this.waitForSDK();
                console.log('[Stripe] SDK loaded successfully');

                // Initialize Stripe instance
                console.log('[Stripe] Initializing with publishable key');
                this._stripe = window.Stripe(config.publishable_key);

                // Create Elements instance
                console.log('[Stripe] Creating Elements instance');
                const appearance = {
                    theme: 'stripe',
                    variables: {
                        colorPrimary: '#0570de',
                        colorBackground: '#ffffff',
                        colorText: '#30313d',
                        colorDanger: '#df1b41',
                        fontFamily: 'system-ui, sans-serif',
                        spacingUnit: '4px',
                        borderRadius: '4px',
                    },
                };

                this._elements = this._stripe.elements({
                    clientSecret: intentData.client_secret,
                    appearance: appearance,
                });

                // Create Payment Element
                console.log('[Stripe] Creating Payment Element');
                this._paymentElement = this._elements.create('payment', {
                    layout: {
                        type: 'tabs',
                        defaultCollapsed: false,
                    },
                    business: {
                        name: window.location.hostname,
                    },
                    paymentMethodOrder: ['card', 'apple_pay', 'google_pay'],
                });

                // Setup container HTML
                container.innerHTML = `
                    <div class="stripe-payment-container">
                        <div id="stripe-payment-element" class="stripe-payment-element"></div>
                        <div id="stripe-error-message" class="stripe-error-message" style="color: #df1b41; margin-top: 0.5rem; display: none;"></div>
                        <button id="stripe-submit-btn"
                                class="btn btn-primary stripe-submit-btn"
                                type="button"
                                style="margin-top: 1rem; width: 100%;">
                            Complete Payment
                        </button>
                    </div>
                `;
                console.log('[Stripe] Container HTML created');

                // Mount Payment Element to DOM
                console.log('[Stripe] Mounting Payment Element...');
                this._paymentElement.mount('#stripe-payment-element');
                console.log('[Stripe] Payment Element mounted successfully');

                // Handle form submission
                const submitBtn = document.getElementById('stripe-submit-btn');
                const errorMessage = document.getElementById('stripe-error-message');

                submitBtn.addEventListener('click', async (e) => {
                    e.preventDefault();

                    try {
                        // Disable button during processing
                        submitBtn.disabled = true;
                        submitBtn.textContent = 'Processing...';
                        errorMessage.style.display = 'none';

                        console.log('[Stripe] Confirming payment');

                        // Get current language for return URL
                        const lang = document.documentElement.lang || 'en';
                        const returnUrl = `${window.location.origin}/${lang}/checkout/confirmation/${intentData.order_number}/`;

                        const { error } = await this._stripe.confirmPayment({
                            elements: this._elements,
                            confirmParams: {
                                return_url: returnUrl,
                            },
                            redirect: 'if_required',
                        });

                        if (error) {
                            // Payment failed
                            console.error('[Stripe] Payment error:', error);
                            errorMessage.textContent = error.message;
                            errorMessage.style.display = 'block';
                            submitBtn.disabled = false;
                            submitBtn.textContent = 'Complete Payment';
                            onError(error.message || 'Payment failed. Please try again.');
                        } else {
                            // Payment succeeded
                            console.log('[Stripe] Payment succeeded');
                            onSuccess(intentData.order_number);
                        }
                    } catch (err) {
                        console.error('[Stripe] Payment confirmation error:', err);
                        errorMessage.textContent = 'Payment failed. Please try again.';
                        errorMessage.style.display = 'block';
                        submitBtn.disabled = false;
                        submitBtn.textContent = 'Complete Payment';
                        onError(err.message || 'Payment confirmation failed. Please try again.');
                    }
                });

                // Handle element ready event
                this._paymentElement.on('ready', () => {
                    console.log('[Stripe] Payment Element ready');
                });

                // Handle element change event for validation
                this._paymentElement.on('change', (event) => {
                    if (event.complete) {
                        errorMessage.style.display = 'none';
                    }
                });

            } catch (err) {
                console.error('[Stripe] Initialization error:', err);
                onError(err.message || 'Failed to initialize payment form. Please try again.');
            }
        },

        /**
         * Wait for Stripe.js SDK to be loaded and available
         * @returns {Promise} - Resolves when SDK is ready
         */
        waitForSDK() {
            return new Promise((resolve, reject) => {
                const timeout = 10000; // 10 seconds
                const startTime = Date.now();

                const check = () => {
                    if (window.Stripe) {
                        resolve();
                    } else if (Date.now() - startTime > timeout) {
                        reject(new Error('Stripe SDK failed to load within 10 seconds'));
                    } else {
                        setTimeout(check, 50);
                    }
                };

                check();
            });
        },

        /**
         * Cleanup handler resources
         * Called when navigating away or switching payment methods
         */
        cleanup() {
            console.log('[Stripe] Cleaning up handler resources');

            // Unmount and destroy payment element
            if (this._paymentElement) {
                this._paymentElement.unmount();
                this._paymentElement = null;
            }

            // Clear elements instance
            if (this._elements) {
                this._elements = null;
            }

            // Clear stripe instance
            this._stripe = null;

            // Remove payment element container
            const paymentElement = document.getElementById('stripe-payment-element');
            if (paymentElement) {
                paymentElement.innerHTML = '';
            }

            // Remove submit button event listeners by replacing it
            const submitBtn = document.getElementById('stripe-submit-btn');
            if (submitBtn && submitBtn.parentNode) {
                const newBtn = submitBtn.cloneNode(true);
                submitBtn.parentNode.replaceChild(newBtn, submitBtn);
            }

            console.log('[Stripe] Cleanup complete');
        }
    };

    console.log('[Stripe] Handler registered successfully');
})();
