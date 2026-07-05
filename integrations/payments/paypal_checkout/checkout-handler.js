/* Copyright (c) 2025-2026 Spwig. Licensed under AGPL-3.0. */

/**
 * PayPal Smart Buttons Checkout Handler
 *
 * Implements embedded checkout for PayPal payment provider.
 *
 * @see https://developer.paypal.com/sdk/js/
 * @version 1.1.1
 * @author Spwig
 */

(function() {
    'use strict';

    window.PaymentHandlers = window.PaymentHandlers || {};

    window.PaymentHandlers.paypal = {
        _paypalButtons: null,
        _config: null,

        async initialize(intentData, container, onSuccess, onError) {
            try {
                const config = intentData.handler_config;

                if (!config?.order_id || !config?.client_id || !config?.currency) {
                    throw new Error('Missing required PayPal configuration');
                }

                this._config = config;

                console.log('[PayPal] Waiting for SDK...');
                await this.waitForSDK();
                console.log('[PayPal] SDK loaded');

                // Setup container HTML
                container.innerHTML = `
                    <div class="paypal-payment-container">
                        <div id="paypal-button-container" class="paypal-button-container"></div>
                        <div id="paypal-error-message" style="color: #df1b41; margin-top: 0.5rem; display: none;"></div>
                    </div>
                `;

                const errorMessage = document.getElementById('paypal-error-message');

                // Render PayPal Smart Button
                this._paypalButtons = window.paypal.Buttons({
                    style: {
                        layout: 'vertical',
                        color: 'gold',
                        shape: 'rect',
                        label: 'paypal',
                        height: 45,
                    },

                    createOrder: function() {
                        console.log('[PayPal] Using pre-created order:', config.order_id);
                        return config.order_id;
                    },

                    onApprove: async function(data) {
                        try {
                            console.log('[PayPal] Payment approved, capturing...');
                            errorMessage.style.display = 'none';

                            const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content
                                || document.querySelector('[name=csrfmiddlewaretoken]')?.value;

                            const response = await fetch(`/api/payments/intents/${intentData.intent_id}/confirm/`, {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json',
                                    'X-CSRFToken': csrfToken || '',
                                },
                                body: JSON.stringify({
                                    payment_method_data: {
                                        paypal_order_id: data.orderID,
                                    }
                                })
                            });

                            const result = await response.json();

                            if (result.success && result.status === 'succeeded') {
                                console.log('[PayPal] Payment captured successfully');
                                onSuccess(intentData.order_number);
                            } else {
                                const errorMsg = result.error?.message || 'Payment capture failed';
                                console.error('[PayPal] Capture failed:', errorMsg);
                                errorMessage.textContent = errorMsg;
                                errorMessage.style.display = 'block';
                                onError(errorMsg);
                            }

                        } catch (err) {
                            console.error('[PayPal] Capture error:', err);
                            errorMessage.textContent = 'Payment capture failed. Please try again.';
                            errorMessage.style.display = 'block';
                            onError(err.message || 'Payment capture failed');
                        }
                    },

                    onCancel: function(data) {
                        console.log('[PayPal] Payment cancelled');
                        errorMessage.textContent = 'Payment cancelled. Please try again.';
                        errorMessage.style.display = 'block';
                        onError('Payment cancelled by customer');
                    },

                    onError: function(err) {
                        console.error('[PayPal] Button error:', err);
                        errorMessage.textContent = 'PayPal encountered an error. Please try again.';
                        errorMessage.style.display = 'block';
                        onError(err.message || 'PayPal error occurred');
                    }
                });

                if (this._paypalButtons.isEligible()) {
                    await this._paypalButtons.render('#paypal-button-container');
                    console.log('[PayPal] Smart Button rendered');
                } else {
                    throw new Error('PayPal Smart Buttons not eligible');
                }

            } catch (err) {
                console.error('[PayPal] Init error:', err);
                onError(err.message || 'Failed to initialize PayPal payment');
            }
        },

        waitForSDK() {
            return new Promise((resolve, reject) => {
                const timeout = 10000;
                const start = Date.now();
                const check = () => {
                    if (window.paypal && window.paypal.Buttons) resolve();
                    else if (Date.now() - start > timeout) reject(new Error('SDK timeout'));
                    else setTimeout(check, 50);
                };
                check();
            });
        },

        cleanup() {
            if (this._paypalButtons) {
                try {
                    this._paypalButtons.close();
                } catch (e) {
                    // Ignore close errors
                }
                this._paypalButtons = null;
            }
            this._config = null;
            const buttonContainer = document.getElementById('paypal-button-container');
            if (buttonContainer) buttonContainer.innerHTML = '';
            console.log('[PayPal] Handler cleaned up');
        }
    };

    console.log('[PayPal] Handler registered');

})();
