/* Copyright (c) 2025-2026 Spwig. Licensed under AGPL-3.0. */

/**
 * Square Web Payments SDK Checkout Handler
 *
 * Implements embedded checkout for Square payment provider.
 *
 * @see https://developer.squareup.com/docs/web-payments/overview
 * @version 1.1.1
 * @author Spwig
 */

(function() {
    'use strict';

    window.PaymentHandlers = window.PaymentHandlers || {};

    window.PaymentHandlers.square = {
        _payments: null,
        _card: null,
        _config: null,

        async initialize(intentData, container, onSuccess, onError) {
            try {
                const config = intentData.handler_config;

                if (!config?.application_id || !config?.location_id || !config?.order_id) {
                    throw new Error('Missing required Square configuration');
                }

                this._config = config;

                console.log('[Square] Waiting for SDK...');
                await this.waitForSDK();
                console.log('[Square] SDK loaded');

                // Initialize Square Payments
                this._payments = window.Square.payments(
                    config.application_id,
                    config.location_id
                );

                // Create Card payment method
                this._card = await this._payments.card();

                // Setup container HTML with cardholder name field
                container.innerHTML = `
                    <div class="square-payment-container">
                        <div class="checkout-form-group" style="margin-bottom: 1rem;">
                            <label for="square-cardholder-name">
                                Cardholder Name <span class="required">*</span>
                            </label>
                            <input type="text"
                                   id="square-cardholder-name"
                                   class="checkout-input"
                                   placeholder="Name on card"
                                   required
                                   autocomplete="cc-name">
                        </div>
                        <div id="square-card-container" class="square-card-element"></div>
                        <div id="square-error" style="color: #df1b41; margin-top: 0.5rem; display: none;"></div>
                        <button id="square-submit" class="btn btn-primary" style="margin-top: 1rem; width: 100%;">
                            Complete Payment
                        </button>
                    </div>
                `;

                // Attach Card to DOM
                await this._card.attach('#square-card-container');
                console.log('[Square] Card element mounted');

                // Setup form submission
                const submitBtn = document.getElementById('square-submit');
                const errorDiv = document.getElementById('square-error');
                const cardholderNameInput = document.getElementById('square-cardholder-name');

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

                    try {
                        // Tokenize card to get nonce
                        const tokenResult = await this._card.tokenize();

                        if (tokenResult.status === 'OK') {
                            const nonce = tokenResult.token;
                            console.log('[Square] Card tokenized successfully');

                            // Split cardholder name into given and family names
                            const nameParts = cardholderName.split(' ');
                            const givenName = nameParts[0] || '';
                            const familyName = nameParts.slice(1).join(' ') || '';

                            // Get verification token if needed (for 3DS)
                            let verificationToken = null;
                            if (tokenResult.details?.card) {
                                try {
                                    const verifyResult = await this._payments.verifyBuyer(
                                        nonce,
                                        {
                                            amount: (config.amount / 100).toString(),
                                            currencyCode: config.currency,
                                            intent: 'CHARGE',
                                            billingContact: {
                                                givenName: givenName,
                                                familyName: familyName
                                            }
                                        }
                                    );
                                    verificationToken = verifyResult.token;
                                    console.log('[Square] Buyer verification completed with cardholder name');
                                } catch (verifyError) {
                                    console.warn('[Square] Buyer verification failed:', verifyError);
                                }
                            }

                            // Submit payment via standard confirm endpoint
                            const response = await fetch(`/api/payments/intents/${intentData.intent_id}/confirm/`, {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json',
                                    'X-CSRFToken': this._getCSRFToken()
                                },
                                body: JSON.stringify({
                                    payment_method_data: {
                                        nonce: nonce,
                                        verification_token: verificationToken
                                    }
                                })
                            });

                            const result = await response.json();

                            if (result.success && (result.status === 'succeeded' || result.status === 'authorized')) {
                                console.log('[Square] Payment successful');
                                onSuccess(intentData.order_number);
                            } else {
                                const errorMsg = result.message || result.error || 'Payment failed';
                                errorDiv.textContent = errorMsg;
                                errorDiv.style.display = 'block';
                                submitBtn.disabled = false;
                                submitBtn.textContent = 'Complete Payment';
                                cardholderNameInput.disabled = false;
                                onError(errorMsg);
                            }

                        } else {
                            // Tokenization failed
                            const errorMsg = this._formatTokenizationError(tokenResult.errors);
                            errorDiv.textContent = errorMsg;
                            errorDiv.style.display = 'block';
                            submitBtn.disabled = false;
                            submitBtn.textContent = 'Complete Payment';
                            cardholderNameInput.disabled = false;
                            onError(errorMsg);
                        }

                    } catch (err) {
                        console.error('[Square] Payment error:', err);
                        errorDiv.textContent = err.message || 'Payment failed';
                        errorDiv.style.display = 'block';
                        submitBtn.disabled = false;
                        submitBtn.textContent = 'Complete Payment';
                        cardholderNameInput.disabled = false;
                        onError(err.message);
                    }
                });

            } catch (err) {
                console.error('[Square] Init error:', err);
                onError(err.message || 'Failed to initialize payment');
            }
        },

        waitForSDK() {
            return new Promise((resolve, reject) => {
                const timeout = 10000;
                const start = Date.now();
                const check = () => {
                    if (window.Square) resolve();
                    else if (Date.now() - start > timeout) reject(new Error('SDK timeout'));
                    else setTimeout(check, 50);
                };
                check();
            });
        },

        _getCSRFToken() {
            const meta = document.querySelector('meta[name="csrf-token"]');
            if (meta && meta.content) return meta.content;
            const input = document.querySelector('[name=csrfmiddlewaretoken]');
            if (input) return input.value;
            return '';
        },

        _formatTokenizationError(errors) {
            if (!errors || errors.length === 0) return 'Card validation failed';

            const errorMessages = errors.map(error => {
                switch (error.type) {
                    case 'VALIDATION_ERROR':
                        return error.message || 'Invalid card information';
                    case 'UNSUPPORTED_CARD_BRAND':
                        return 'This card brand is not supported';
                    case 'INVALID_CARD':
                        return 'Invalid card number';
                    case 'CVV_FAILURE':
                        return 'Invalid CVV';
                    default:
                        return error.message || 'Card validation failed';
                }
            });

            return errorMessages.join('; ');
        },

        cleanup() {
            if (this._card) {
                this._card.destroy();
                this._card = null;
            }
            this._payments = null;
            this._config = null;
            console.log('[Square] Handler cleaned up');
        }
    };

    console.log('[Square] Handler registered');

})();
