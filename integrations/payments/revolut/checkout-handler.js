/* Copyright (c) 2025-2026 Spwig. Licensed under AGPL-3.0. */

/**
 * Revolut Checkout Widget Handler
 *
 * Implements embedded checkout for Revolut payment provider
 * using the RevolutCheckout card field widget.
 *
 * @see https://developer.revolut.com/docs/accept-payments
 * @version 1.1.1
 * @author Spwig
 */

(function() {
    'use strict';

    window.PaymentHandlers = window.PaymentHandlers || {};

    window.PaymentHandlers.revolut = {
        _instance: null,
        _cardField: null,
        _config: null,

        async initialize(intentData, container, onSuccess, onError) {
            try {
                const config = intentData.handler_config;

                if (!config?.token || !config?.public_key) {
                    throw new Error('Missing required Revolut configuration');
                }

                this._config = config;

                // Wait for Revolut SDK (loaded by platform via sdk_dependencies)
                console.log('[Revolut] Waiting for SDK...');
                await this.waitForSDK();
                console.log('[Revolut] SDK loaded');

                // Initialize RevolutCheckout with order token
                this._instance = await RevolutCheckout(config.token, config.environment === 'production' ? 'prod' : 'sandbox');
                console.log('[Revolut] Checkout instance created');

                // Setup container HTML with cardholder name field
                container.innerHTML = `
                    <div class="revolut-payment-container">
                        <div class="checkout-form-group" style="margin-bottom: 1rem;">
                            <label for="revolut-cardholder-name">
                                Cardholder Name <span class="required">*</span>
                            </label>
                            <input type="text"
                                   id="revolut-cardholder-name"
                                   class="checkout-input"
                                   placeholder="Name on card"
                                   required
                                   autocomplete="cc-name">
                        </div>
                        <div id="revolut-card-element" class="revolut-card-element"></div>
                        <div id="revolut-error" style="color: #df1b41; margin-top: 0.5rem; display: none;"></div>
                        <button id="revolut-submit" class="btn btn-primary" style="margin-top: 1rem; width: 100%;">
                            Complete Payment
                        </button>
                    </div>
                `;

                const errorDiv = document.getElementById('revolut-error');
                const submitBtn = document.getElementById('revolut-submit');
                const cardholderNameInput = document.getElementById('revolut-cardholder-name');

                // Create card field with callbacks
                this._cardField = this._instance.createCardField({
                    target: document.getElementById('revolut-card-element'),

                    onSuccess() {
                        console.log('[Revolut] Payment succeeded via widget');

                        // Confirm with backend
                        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content
                            || document.querySelector('[name=csrfmiddlewaretoken]')?.value;

                        fetch(`/api/payments/intents/${intentData.intent_id}/confirm/`, {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                'X-CSRFToken': csrfToken || '',
                            },
                            body: JSON.stringify({
                                payment_method_data: {
                                    revolut_order_id: config.order_id,
                                }
                            })
                        })
                        .then(resp => resp.json())
                        .then(result => {
                            if (result.success && (result.status === 'succeeded' || result.status === 'authorized')) {
                                console.log('[Revolut] Payment confirmed by backend');
                                onSuccess(intentData.order_number);
                            } else {
                                const msg = result.error?.message || 'Payment confirmation failed';
                                console.error('[Revolut] Confirm failed:', msg);
                                errorDiv.textContent = msg;
                                errorDiv.style.display = 'block';
                                submitBtn.disabled = false;
                                submitBtn.textContent = 'Complete Payment';
                                cardholderNameInput.disabled = false;
                                onError(msg);
                            }
                        })
                        .catch(err => {
                            console.error('[Revolut] Confirm error:', err);
                            errorDiv.textContent = 'Payment confirmation failed. Please try again.';
                            errorDiv.style.display = 'block';
                            submitBtn.disabled = false;
                            submitBtn.textContent = 'Complete Payment';
                            cardholderNameInput.disabled = false;
                            onError(err.message || 'Confirmation failed');
                        });
                    },

                    onError(error) {
                        console.error('[Revolut] Card field error:', error);
                        errorDiv.textContent = error.message || 'Payment failed. Please try again.';
                        errorDiv.style.display = 'block';
                        submitBtn.disabled = false;
                        submitBtn.textContent = 'Complete Payment';
                        cardholderNameInput.disabled = false;
                        onError(error.message || 'Payment failed');
                    },

                    onCancel() {
                        console.log('[Revolut] Payment cancelled');
                        errorDiv.textContent = 'Payment cancelled. Please try again.';
                        errorDiv.style.display = 'block';
                        submitBtn.disabled = false;
                        submitBtn.textContent = 'Complete Payment';
                        cardholderNameInput.disabled = false;
                        onError('Payment cancelled by customer');
                    },

                    onValidation(errors) {
                        if (errors && errors.length > 0) {
                            errorDiv.textContent = errors.map(e => e.message).join('; ');
                            errorDiv.style.display = 'block';
                        } else {
                            errorDiv.style.display = 'none';
                        }
                    },
                });

                console.log('[Revolut] Card field mounted');

                // Handle submit button click
                submitBtn.addEventListener('click', async (e) => {
                    e.preventDefault();

                    // Validate cardholder name
                    const cardholderName = cardholderNameInput.value.trim();
                    if (!cardholderName) {
                        cardholderNameInput.focus();
                        cardholderNameInput.style.borderColor = 'var(--theme-color-error, #ef4444)';
                        errorDiv.textContent = 'Please enter the cardholder name.';
                        errorDiv.style.display = 'block';
                        return;
                    }

                    // Reset border color
                    cardholderNameInput.style.borderColor = '';

                    submitBtn.disabled = true;
                    submitBtn.textContent = 'Processing...';
                    cardholderNameInput.disabled = true;
                    errorDiv.style.display = 'none';

                    // Submit card payment with cardholder name
                    this._cardField.submit({
                        name: cardholderName,
                    });
                });

            } catch (err) {
                console.error('[Revolut] Init error:', err);
                onError(err.message || 'Failed to initialize Revolut payment');
            }
        },

        waitForSDK() {
            return new Promise((resolve, reject) => {
                const timeout = 10000;
                const start = Date.now();
                const check = () => {
                    if (window.RevolutCheckout) resolve();
                    else if (Date.now() - start > timeout) reject(new Error('Revolut SDK timeout'));
                    else setTimeout(check, 50);
                };
                check();
            });
        },

        cleanup() {
            if (this._cardField) {
                try { this._cardField.destroy(); } catch (e) { /* ignore */ }
                this._cardField = null;
            }
            if (this._instance) {
                try { this._instance.destroy(); } catch (e) { /* ignore */ }
                this._instance = null;
            }
            this._config = null;
            console.log('[Revolut] Handler cleaned up');
        }
    };

    console.log('[Revolut] Handler registered');

})();
