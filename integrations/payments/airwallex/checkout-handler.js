/* Copyright (c) 2025-2026 Spwig. Licensed under AGPL-3.0. */

/**
 * Airwallex Checkout Handler
 *
 * Dynamically loaded plugin for Airwallex embedded payment integration.
 * Implements the standard PaymentHandlers interface for Spwig platform.
 *
 * @version 1.1.6
 * @author Spwig
 */
(function() {
    'use strict';

    // Initialize global payment handlers registry
    window.PaymentHandlers = window.PaymentHandlers || {};

    /**
     * Airwallex Payment Handler
     * Registers itself in the global handlers registry
     */
    window.PaymentHandlers.airwallex = {
        /**
         * Initialize Airwallex embedded checkout
         *
         * @param {object} intentData - Payment intent response from API
         * @param {object} intentData.handler_config - Airwallex-specific configuration
         * @param {string} intentData.handler_config.intent_id - Airwallex payment intent ID
         * @param {string} intentData.handler_config.environment - 'demo' or 'production'
         * @param {string} intentData.handler_config.currency - ISO currency code (e.g., 'USD')
         * @param {string} intentData.handler_config.country_code - ISO country code (e.g., 'US')
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
                if (!config || !config.intent_id || !config.environment || !config.currency || !config.country_code) {
                    throw new Error('Missing required Airwallex configuration');
                }

                if (!intentData.client_secret) {
                    throw new Error('Missing client_secret in payment intent data');
                }

                // Wait for Airwallex SDK to be available
                console.log('[Airwallex] Waiting for SDK to load...');
                await this.waitForSDK();
                console.log('[Airwallex] SDK loaded successfully');

                // Initialize Airwallex Components SDK
                console.log('[Airwallex] Initializing SDK with environment:', config.environment);
                await window.AirwallexComponentsSDK.init({
                    env: config.environment,
                    origin: window.location.origin,
                    enabledElements: ['payments'],
                });

                // Create card payment element using createElement function
                console.log('[Airwallex] Creating card element');
                const cardElement = await window.AirwallexComponentsSDK.createElement('card', {
                    intent_id: config.intent_id,
                    client_secret: intentData.client_secret,
                    currency: config.currency,
                    country_code: config.country_code,
                });

                // Setup container HTML with cardholder name field
                container.innerHTML = `
                    <div class="airwallex-payment-container">
                        <div class="checkout-form-group" style="margin-bottom: 1rem;">
                            <label for="airwallex-cardholder-name">
                                Cardholder Name <span class="required">*</span>
                            </label>
                            <input type="text"
                                   id="airwallex-cardholder-name"
                                   class="checkout-input"
                                   placeholder="Name on card"
                                   required
                                   autocomplete="cc-name">
                        </div>
                        <div id="airwallex-card-element" class="airwallex-card-element"></div>
                        <button id="airwallex-submit-btn"
                                class="btn btn-primary airwallex-submit-btn"
                                type="button"
                                style="margin-top: 1rem; width: 100%;">
                            Complete Payment
                        </button>
                    </div>
                `;
                console.log('[Airwallex] Container HTML created with cardholder name field');

                // Verify container element exists
                const mountTarget = document.getElementById('airwallex-card-element');
                console.log('[Airwallex] Mount target element:', mountTarget);

                // Mount card element to DOM
                console.log('[Airwallex] Mounting card element...');
                cardElement.mount('airwallex-card-element');
                console.log('[Airwallex] Card element mounted successfully');

                // Handle payment submission
                const submitBtn = document.getElementById('airwallex-submit-btn');
                const cardholderNameInput = document.getElementById('airwallex-cardholder-name');

                submitBtn.addEventListener('click', async () => {
                    try {
                        // Validate cardholder name
                        const cardholderName = cardholderNameInput.value.trim();
                        if (!cardholderName) {
                            cardholderNameInput.focus();
                            cardholderNameInput.style.borderColor = 'var(--theme-color-error, #ef4444)';
                            onError('Please enter the cardholder name.');
                            return;
                        }

                        // Reset border color
                        cardholderNameInput.style.borderColor = '';

                        // Disable button during processing
                        submitBtn.disabled = true;
                        submitBtn.textContent = 'Processing...';
                        cardholderNameInput.disabled = true;

                        console.log('[Airwallex] Confirming payment intent with cardholder name');
                        var nameParts = cardholderName.split(' ');
                        var firstName = nameParts[0];
                        var lastName = nameParts.length > 1 ? nameParts.slice(1).join(' ') : firstName;

                        const result = await window.AirwallexComponentsSDK.confirmPaymentIntent({
                            element: cardElement,
                            id: config.intent_id,
                            client_secret: intentData.client_secret,
                            payment_method: {
                                billing: {
                                    first_name: firstName,
                                    last_name: lastName,
                                },
                            },
                        });

                        if (result.error) {
                            console.error('[Airwallex] Payment error:', result.error);
                            // Re-enable button on error
                            submitBtn.disabled = false;
                            submitBtn.textContent = 'Complete Payment';
                            cardholderNameInput.disabled = false;
                            onError(result.error.message || 'Payment failed. Please try again.');
                        } else {
                            console.log('[Airwallex] Payment succeeded');
                            onSuccess(intentData.order_number);
                        }
                    } catch (err) {
                        console.error('[Airwallex] Payment confirmation error:', err);
                        // Re-enable button on error
                        submitBtn.disabled = false;
                        submitBtn.textContent = 'Complete Payment';
                        cardholderNameInput.disabled = false;
                        onError(err.message || 'Payment confirmation failed. Please try again.');
                    }
                });

            } catch (err) {
                console.error('[Airwallex] Initialization error:', err);
                onError(err.message || 'Failed to initialize payment form. Please try again.');
            }
        },

        /**
         * Wait for Airwallex SDK to be loaded and available
         * @returns {Promise} - Resolves when SDK is ready
         */
        waitForSDK() {
            return new Promise((resolve, reject) => {
                const timeout = 10000;  // 10 seconds - matches other providers
                const startTime = Date.now();

                const check = () => {
                    if (window.AirwallexComponentsSDK) {
                        resolve();
                    } else if (Date.now() - startTime > timeout) {
                        reject(new Error('Airwallex SDK failed to load within 10 seconds'));
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
            console.log('[Airwallex] Cleaning up handler resources');

            // Remove card element container
            const cardElement = document.getElementById('airwallex-card-element');
            if (cardElement) {
                cardElement.innerHTML = '';
            }

            // Remove submit button event listeners by replacing it
            const submitBtn = document.getElementById('airwallex-submit-btn');
            if (submitBtn && submitBtn.parentNode) {
                const newBtn = submitBtn.cloneNode(true);
                submitBtn.parentNode.replaceChild(newBtn, submitBtn);
            }

            console.log('[Airwallex] Cleanup complete');
        }
    };

    console.log('[Airwallex] Handler registered successfully');
})();
