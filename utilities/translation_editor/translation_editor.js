/* Copyright (c) 2025-2026 Spwig. Licensed under AGPL-3.0. */

/**
 * Translation Editor Utility
 * Provides interface for translating page builder element content
 */

class TranslationEditor {
    // Static properties for request caching (shared across all instances)
    static _pendingRequests = new Map();
    static _responseCache = new Map();
    static _CACHE_TTL = 5000; // Cache responses for 5 seconds

    constructor(options = {}) {
        // Get API base URL with language prefix handling
        this.apiBaseUrl = this.getApiBaseUrl();

        this.options = {
            // Translation thresholds
            charThreshold: 1000,        // Characters before suggesting batch mode
            languageThreshold: 5,        // Languages before suggesting scheduling

            // API endpoints
            translateEndpoint: `${this.apiBaseUrl}/translate-element/`,
            scheduleEndpoint: `${this.apiBaseUrl}/schedule-page-translation/`,
            statusEndpoint: `${this.apiBaseUrl}/translation-status/`,

            // UI options
            showProgress: true,
            autoDetectChanges: true,
            showFallbackWarning: true,

            // Callbacks
            onTranslate: options.onTranslate || (() => {}),
            onSchedule: options.onSchedule || (() => {}),
            onError: options.onError || ((err) => console.error(err)),

            ...options
        };

        // State
        this.isOpen = false;
        this.currentElement = null;
        this.currentField = null;
        this.translations = {};
        this.pendingTranslations = new Set();

        // UI elements
        this.editorElement = null;
        this.targetInput = null;
        this.triggerBtn = null;

        // Language detection
        this.detectedLanguage = this.detectLanguage();
        this.availableLanguages = this.getAvailableLanguages() || [];  // Ensure it's always an array
        this.primaryLanguage = document.documentElement.lang || 'en';

        // Languages are provided via template, no need for API call
    }

    getApiBaseUrl() {
        // API routes are at /api/page-builder/translation/ (outside i18n_patterns, no language prefix)
        return '/api/page-builder/translation';
    }

    detectLanguage() {
        // Detect current language from various sources
        return (
            this.getUrlParam('lang') ||
            this.getCookie('lang') ||
            document.documentElement.lang ||
            navigator.language?.substring(0, 2) ||
            'en'
        );
    }

    getUrlParam(param) {
        const urlParams = new URLSearchParams(window.location.search);
        return urlParams.get(param);
    }

    getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) {
            return parts.pop().split(';').shift();
        }
        return null;
    }

    getAvailableLanguages() {
        // Get from page data (should be set by template from translation service)
        if (window.PAGE_BUILDER_LANGUAGES && Array.isArray(window.PAGE_BUILDER_LANGUAGES)) {
            return window.PAGE_BUILDER_LANGUAGES;
        }

        // No languages available - translation service not working
        return [];
    }

    attach(element, fieldName = 'text') {
        // Attach to an input element
        this.targetInput = element;
        this.currentField = fieldName;

        // Get element ID from form
        const form = this.targetInput.closest('form');
        if (form && form.dataset.elementId) {
            this.currentElement = {
                id: form.dataset.elementId,
                type: form.dataset.elementType
            };
        }

        // Create trigger button if it doesn't exist
        if (!this.triggerBtn) {
            this.createTriggerButton();
        }

        // Load existing translations
        this.loadTranslations();
    }

    createTriggerButton() {
        // Check if button already exists
        const existingTrigger = this.targetInput.parentNode?.querySelector('.translation-editor-trigger');
        if (existingTrigger) {
            this.triggerBtn = existingTrigger;
            return;
        }

        // Create button using consistent utility button styles
        this.triggerBtn = document.createElement('button');
        this.triggerBtn.className = 'util-btn util-btn-primary translation-editor-trigger';
        this.triggerBtn.type = 'button';
        this.triggerBtn.title = 'Manage Translations';
        this.triggerBtn.innerHTML = '<i class="fas fa-language"></i>';

        // Add click handler
        this.triggerBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            this.toggle();
        });

        // Insert after input (or after textarea)
        if (this.targetInput.parentNode) {
            // Position button next to the input
            this.targetInput.parentNode.style.position = 'relative';
            this.targetInput.parentNode.style.display = 'flex';
            this.targetInput.parentNode.style.gap = '8px';
            this.targetInput.parentNode.appendChild(this.triggerBtn);
        }

        // Update count
        this.updateTranslationCount();
    }

    updateTranslationCount() {
        if (!this.triggerBtn) return;

        const count = Object.keys(this.translations).length;
        const total = this.availableLanguages.length - 1; // Exclude primary
        const countSpan = this.triggerBtn.querySelector('.utility-translation-count');

        if (countSpan) {
            countSpan.textContent = `${count}/${total}`;

            // Update color based on completion
            if (count === 0) {
                this.triggerBtn.classList.remove('has-translations', 'full-translations');
            } else if (count === total) {
                this.triggerBtn.classList.add('has-translations', 'full-translations');
            } else {
                this.triggerBtn.classList.add('has-translations');
                this.triggerBtn.classList.remove('full-translations');
            }
        }
    }

    async loadTranslations() {
        // Fetch existing translations from the API
        if (!this.currentElement || !this.currentElement.id) {
            this.translations = {};
            this.updateTranslationCount();
            return;
        }

        const elementId = this.currentElement.id;
        const elementType = this.currentElement.type;

        // Skip API call for page settings - Page model uses django-modeltranslation
        // which handles translations differently from PageElement translations
        if (elementType === 'page' || elementType === '_page' ||
            (typeof elementId === 'string' && elementId.startsWith('page-'))) {
            this.translations = {};
            this.updateTranslationCount();
            return;
        }
        const cacheKey = `element_${elementId}`;

        try {
            // Check if we have a cached response that's still valid
            const cached = TranslationEditor._responseCache.get(cacheKey);
            if (cached && (Date.now() - cached.timestamp) < TranslationEditor._CACHE_TTL) {
                this.processTranslationData(cached.data);
                return;
            }

            // Check if there's already a pending request for this element
            let requestPromise = TranslationEditor._pendingRequests.get(cacheKey);

            if (!requestPromise) {
                // No pending request, create one
                requestPromise = fetch(`${this.apiBaseUrl}/element/${elementId}/translation-status/`)
                    .then(response => {
                        if (response.ok) {
                            return response.json();
                        }
                        return null;
                    })
                    .finally(() => {
                        // Clean up pending request after completion
                        TranslationEditor._pendingRequests.delete(cacheKey);
                    });

                // Store the pending request
                TranslationEditor._pendingRequests.set(cacheKey, requestPromise);
            }

            // Wait for the request (whether we created it or reusing existing)
            const data = await requestPromise;

            // Cache the response
            if (data) {
                TranslationEditor._responseCache.set(cacheKey, {
                    data: data,
                    timestamp: Date.now()
                });
            }

            this.processTranslationData(data);
        } catch (error) {
            console.error('Error loading translations:', error);
            this.translations = {};
        }

        this.updateTranslationCount();
    }

    /**
     * Process translation data from API response
     * @param {Object|null} data - API response data
     */
    processTranslationData(data) {
        if (data && data.translations) {
            // Extract translations and convert to our internal format
            this.translations = {};
            for (const [langCode, fieldTranslations] of Object.entries(data.translations)) {
                if (fieldTranslations[this.currentField]) {
                    this.translations[langCode] = {
                        [this.currentField]: fieldTranslations[this.currentField],
                        _meta: fieldTranslations._meta || {
                            auto: true,
                            verified: false
                        }
                    };
                }
            }
        } else {
            this.translations = {};
        }
    }

    toggle() {
        if (this.isOpen) {
            this.close();
        } else {
            this.open();
        }
    }

    async open() {
        if (this.isOpen) return;

        // Check if languages are available
        if (!this.availableLanguages || this.availableLanguages.length === 0) {
            // Try to fetch languages first
            await this.fetchAndUpdateLanguages();

            // If still no languages, show error
            if (!this.availableLanguages || this.availableLanguages.length === 0) {
                this.showServiceUnavailable();
                return;
            }
        }

        // Reload translations from API to ensure we have latest data
        await this.loadTranslations();

        this.isOpen = true;

        // Create editor UI
        this.createEditor();
        this.setupEventListeners();
        this.updateLanguageList();
        this.analyzeContent();
        this.position();

        // Add outside click handler
        setTimeout(() => {
            document.addEventListener('click', this.handleOutsideClick);
        }, 100);
    }

    showServiceUnavailable() {
        // Show error message that translation service is not available
        const errorModal = document.createElement('div');
        errorModal.className = 'utility-translation-modal translation-service-error';
        errorModal.innerHTML = `
            <div class="utility-popup medium">
                <div class="utility-header error">
                    <h3 class="utility-title"><i class="fas fa-exclamation-triangle"></i> Translation Service Unavailable</h3>
                    <button type="button" class="utility-close" onclick="this.closest('.utility-translation-modal').remove()">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="utility-body">
                    <p>The translation service is currently unavailable. This could mean:</p>
                    <ul>
                        <li>The translation service is not running</li>
                        <li>No languages are configured in the system</li>
                        <li>There's a connection issue with the service</li>
                    </ul>
                    <p>Please contact your administrator to ensure the translation service is properly configured and running.</p>
                </div>
                <div class="utility-footer">
                    <button type="button" class="btn btn-apply" onclick="this.closest('.utility-translation-modal').remove()">
                        Close
                    </button>
                </div>
            </div>
        `;
        document.body.appendChild(errorModal);
    }

    close() {
        if (!this.isOpen) return;

        this.isOpen = false;

        if (this.editorElement) {
            this.editorElement.remove();
            this.editorElement = null;
        }

        document.removeEventListener('click', this.handleOutsideClick);
    }

    handleOutsideClick = (e) => {
        // Check if editor element exists and click is outside it
        if (this.editorElement && !this.editorElement.contains(e.target)) {
            // If we have a trigger button, also check it's not clicked
            if (this.triggerBtn && this.triggerBtn.contains(e.target)) {
                return;
            }
            this.close();
        }
    }

    createEditor() {
        const popup = document.createElement('div');
        popup.className = 'utility-popup large utility-translation-editor';
        popup.innerHTML = `
            <div class="utility-header">
                <h3 class="utility-title">
                    <i class="fas fa-globe"></i> Manage Translations
                </h3>
                <button class="utility-close" type="button">
                    <i class="fas fa-times"></i>
                </button>
            </div>

            <div class="utility-body">
                <!-- Content Analysis -->
                <div class="utility-translation-analysis">
                    <div class="utility-analysis-item">
                        <span class="utility-analysis-label">Content Size:</span>
                        <span class="utility-analysis-value" id="content-size">0 characters</span>
                    </div>
                    <div class="utility-analysis-item">
                        <span class="utility-analysis-label">Languages:</span>
                        <span class="utility-analysis-value" id="language-count">0 available</span>
                    </div>
                    <div class="utility-analysis-recommendation" id="recommendation"></div>
                </div>

                <!-- Language List -->
                <div class="utility-language-list" id="language-list"></div>

                <!-- Action Buttons -->
                <div class="utility-translation-actions">
                    <button class="button" id="translate-selected">
                        <i class="fas fa-language"></i> Translate Selected
                    </button>
                    <button class="button default" id="translate-all">
                        <i class="fas fa-globe"></i> Translate All
                    </button>
                </div>

                <!-- Progress Section -->
                <div class="utility-translation-progress" style="display: none;">
                    <div class="utility-progress-bar">
                        <div class="utility-progress-fill" style="width: 0%"></div>
                    </div>
                    <div class="utility-progress-text">Starting translation...</div>
                </div>
            </div>

            <div class="utility-footer">
                <button class="btn btn-clear" id="clear-translations">
                    Clear All Translations
                </button>
                <div class="footer-actions">
                    <button class="btn btn-clear" id="cancel-btn">Cancel</button>
                    <button class="btn btn-apply" id="save-btn">Save Translations</button>
                </div>
            </div>
        `;

        document.body.appendChild(popup);
        this.editorElement = popup;
    }

    setupEventListeners() {
        if (!this.editorElement) return;

        // Make the popup draggable using inline implementation
        const header = this.editorElement.querySelector('.utility-header');
        if (header) {
            this.makeDraggable(this.editorElement, header);
        }

        // Close button
        this.editorElement.querySelector('.utility-close')?.addEventListener('click', () => {
            this.close();
        });

        // Cancel button
        this.editorElement.querySelector('#cancel-btn')?.addEventListener('click', () => {
            this.close();
        });

        // Save button
        this.editorElement.querySelector('#save-btn')?.addEventListener('click', () => {
            this.saveTranslations();
        });

        // Clear translations
        this.editorElement.querySelector('#clear-translations')?.addEventListener('click', async () => {
            if (await AdminModal.confirm({message: 'Are you sure you want to clear all translations?', danger: true, confirmText: 'Clear All'})) {
                this.clearTranslations();
            }
        });

        // Translate selected
        this.editorElement.querySelector('#translate-selected')?.addEventListener('click', () => {
            this.translateSelected();
        });

        // Translate all
        this.editorElement.querySelector('#translate-all')?.addEventListener('click', () => {
            this.translateAll();
        });
    }

    analyzeContent() {
        const content = this.getSourceContent();
        const charCount = content.length;
        const langCount = this.availableLanguages.length - 1; // Exclude primary

        // Update analysis display
        const sizeElement = this.editorElement.querySelector('#content-size');
        const langElement = this.editorElement.querySelector('#language-count');
        const recElement = this.editorElement.querySelector('#recommendation');

        if (sizeElement) sizeElement.textContent = `${charCount} characters`;
        if (langElement) langElement.textContent = `${langCount} available`;

        // Make recommendation
        if (recElement) {
            if (charCount > this.options.charThreshold && langCount > this.options.languageThreshold) {
                recElement.innerHTML = `
                    <i class="fas fa-exclamation-triangle"></i>
                    Large translation job detected. Consider scheduling for off-peak hours.
                `;
                recElement.className = 'analysis-recommendation warning';
            } else if (charCount > this.options.charThreshold) {
                recElement.innerHTML = `
                    <i class="fas fa-info-circle"></i>
                    Large content detected. Translation may take a moment.
                `;
                recElement.className = 'analysis-recommendation info';
            } else {
                recElement.innerHTML = `
                    <i class="fas fa-check-circle"></i>
                    Content suitable for immediate translation.
                `;
                recElement.className = 'analysis-recommendation success';
            }
        }
    }

    updateLanguageList() {
        const listContainer = this.editorElement.querySelector('#language-list');
        if (!listContainer) return;

        const sourceContent = this.getSourceContent();

        listContainer.innerHTML = this.availableLanguages
            .filter(lang => lang.code !== this.primaryLanguage)
            .map(lang => {
                const translation = this.translations[lang.code];
                const hasTranslation = !!translation;
                const translatedText = hasTranslation ? translation[this.currentField] : '';

                // Determine translation state
                const isManual = translation?._meta?.auto === false;
                const isVerified = translation?._meta?.verified === true;
                const isPending = translation?._meta?.pending === true;

                // Build status badge
                let statusBadge = '';
                if (isPending) {
                    statusBadge = '<span class="utility-translation-badge pending"><i class="fas fa-clock"></i> Pending</span>';
                } else if (hasTranslation) {
                    if (isManual) {
                        statusBadge = '<span class="utility-translation-badge manual"><i class="fas fa-pen"></i> Manual</span>';
                    } else {
                        statusBadge = '<span class="utility-translation-badge auto"><i class="fas fa-robot"></i> AI</span>';
                    }
                    if (isVerified) {
                        statusBadge += ' <span class="utility-translation-badge verified"><i class="fas fa-check-circle"></i></span>';
                    }
                }

                return `
                    <div class="utility-language-item ${hasTranslation ? 'has-translation' : ''} ${isPending ? 'pending-translation' : ''}" data-lang="${lang.code}">
                        <div class="utility-language-header">
                            <label class="utility-language-checkbox">
                                <input type="checkbox" value="${lang.code}" ${hasTranslation || isPending ? 'checked' : ''}>
                                <span class="utility-language-name">${lang.name}</span>
                                ${statusBadge}
                            </label>
                            <div class="utility-language-actions">
                                <button class="utility-btn-icon translate-single" data-lang="${lang.code}" title="Translate">
                                    <i class="fas fa-language"></i>
                                </button>
                                ${hasTranslation ? `
                                    <button class="utility-btn-icon clear-translation" data-lang="${lang.code}" title="Clear">
                                        <i class="fas fa-times"></i>
                                    </button>
                                ` : ''}
                            </div>
                        </div>
                        <div class="utility-translation-preview">
                            <textarea class="utility-translation-text" data-lang="${lang.code}"
                                      placeholder="Enter translation for ${lang.name}..."
                                      ${isPending ? 'disabled' : ''}>${translatedText || ''}</textarea>
                            <div class="utility-translation-info">
                                <span class="char-count">${(translatedText || '').length} chars</span>
                            </div>
                        </div>
                    </div>
                `;
            }).join('');

        // Add event listeners for language actions
        this.setupLanguageItemListeners();
    }

    setupLanguageItemListeners() {
        // Translate single language buttons
        this.editorElement.querySelectorAll('.translate-single').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const lang = btn.dataset.lang;
                await this.translateSingleLanguage(lang);
            });
        });

        // Clear translation buttons
        this.editorElement.querySelectorAll('.clear-translation').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const lang = btn.dataset.lang;
                if (await AdminModal.confirm({message: `Clear ${lang} translation?`, danger: true, confirmText: 'Clear'})) {
                    delete this.translations[lang];
                    const textarea = this.editorElement.querySelector(`.utility-translation-text[data-lang="${lang}"]`);
                    if (textarea) textarea.value = '';
                    this.updateLanguageList();
                }
            });
        });

        // Manual translation edits
        this.editorElement.querySelectorAll('.utility-translation-text').forEach(textarea => {
            textarea.addEventListener('input', (e) => {
                const lang = textarea.dataset.lang;
                if (!this.translations[lang]) {
                    this.translations[lang] = {};
                }
                this.translations[lang][this.currentField] = textarea.value;
                this.translations[lang]._meta = {
                    auto: false,
                    verified: true,
                    translated_at: new Date().toISOString()
                };
            });
        });
    }

    getSourceContent() {
        // Get the current content to translate
        return this.targetInput.value || '';
    }

    getSelectedLanguages() {
        const checked = this.editorElement.querySelectorAll('.utility-language-checkbox input:checked');
        return Array.from(checked).map(cb => cb.value);
    }

    async translateSingleLanguage(lang) {
        await this.performTranslation([lang]);
    }

    async translateSelected() {
        const languages = this.getSelectedLanguages();
        if (languages.length === 0) {
            AdminModal.alert({message: 'Please select at least one language to translate.', type: 'warning'});
            return;
        }

        await this.performTranslation(languages);
    }

    async translateAll() {
        const languages = this.availableLanguages
            .filter(lang => lang.code !== this.primaryLanguage)
            .map(lang => lang.code);

        await this.performTranslation(languages);
    }

    async performTranslation(languages) {
        const content = this.getSourceContent();
        const charCount = content.length;

        // Check if should schedule
        if (charCount * languages.length > this.options.charThreshold * this.options.languageThreshold) {
            if (await AdminModal.confirm('This is a large translation job. Would you like to schedule it for off-peak hours?')) {
                await this.scheduleTranslation(languages);
                return;
            }
        }

        // Show progress
        this.showProgress();

        try {
            const response = await fetch(this.options.translateEndpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    element_id: this.currentElement?.id,
                    fields: [this.currentField],
                    content: content,
                    source_language: this.primaryLanguage,
                    languages: languages
                })
            });

            if (!response.ok) {
                throw new Error(`Translation failed: ${response.statusText}`);
            }

            const result = await response.json();

            // Update translations
            if (result.translations) {
                for (const [lang, langTranslations] of Object.entries(result.translations)) {
                    // The API returns translations[lang][field]
                    const translatedText = langTranslations[this.currentField] || langTranslations.text || '';

                    this.translations[lang] = {
                        [this.currentField]: translatedText,
                        _meta: {
                            auto: true,
                            verified: false,
                            translated_at: new Date().toISOString()
                        }
                    };
                }
            }

            // Update UI
            this.updateLanguageList();
            this.hideProgress();

            // Callback
            this.options.onTranslate(result);

        } catch (error) {
            this.hideProgress();
            this.options.onError(error);
            AdminModal.alert({message: `Translation failed: ${error.message}`, type: 'error'});
        }
    }

    async scheduleTranslation(languages) {
        try {
            const response = await fetch(this.options.scheduleEndpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    element_id: this.currentElement?.id,
                    fields: [this.currentField],
                    content: this.getSourceContent(),
                    source_language: this.primaryLanguage,
                    languages: languages,
                    schedule_time: 'off_peak' // or specific time
                })
            });

            if (!response.ok) {
                throw new Error(`Scheduling failed: ${response.statusText}`);
            }

            const result = await response.json();

            // Mark languages as pending
            languages.forEach(lang => {
                if (!this.translations[lang]) {
                    this.translations[lang] = {};
                }
                this.translations[lang]._meta = {
                    ...this.translations[lang]._meta,
                    pending: true,
                    job_id: result.job_id
                };
            });

            this.updateLanguageList();

            // Start polling for job status
            this.startJobStatusPolling(result.job_id);

            this.options.onSchedule(result);

        } catch (error) {
            this.options.onError(error);
            AdminModal.alert({message: `Scheduling failed: ${error.message}`, type: 'error'});
        }
    }

    showProgress() {
        const progressSection = this.editorElement.querySelector('.utility-translation-progress');
        if (progressSection) {
            progressSection.style.display = 'block';
        }
    }

    hideProgress() {
        const progressSection = this.editorElement.querySelector('.utility-translation-progress');
        if (progressSection) {
            progressSection.style.display = 'none';
        }
    }

    updateProgress(percent, text) {
        const progressFill = this.editorElement.querySelector('.utility-progress-fill');
        const progressText = this.editorElement.querySelector('.utility-progress-text');

        if (progressFill) progressFill.style.width = `${percent}%`;
        if (progressText) progressText.textContent = text;
    }

    clearTranslations() {
        this.translations = {};
        this.updateLanguageList();
        this.updateTranslationCount();
    }

    async saveTranslations() {
        // Don't modify the text field - translations are stored separately
        // The source text should remain in the input field unchanged

        if (!this.currentElement || !this.currentElement.id) {
            console.error('No current element to save translations to');
            this.showNotification('Cannot save: No element selected', 'error');
            return;
        }

        try {
            // Save translations via API
            const response = await fetch(`${this.apiBaseUrl}/element/${this.currentElement.id}/save-translations/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    translations: this.translations,
                    field: this.currentField
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || `Failed to save translations: ${response.statusText}`);
            }

            const result = await response.json();

            // Update button count
            this.updateTranslationCount();

            // Close editor
            this.close();

            this.showNotification('Translations saved successfully', 'success');
        } catch (error) {
            console.error('Error saving translations:', error);
            this.showNotification(`Failed to save translations: ${error.message}`, 'error');
        }
    }

    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `utility-notification ${type}`;
        notification.innerHTML = `<i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-triangle'}"></i> ${message}`;
        document.body.appendChild(notification);
        setTimeout(() => notification.remove(), 3000);
    }

    position() {
        if (!this.editorElement) {
            return;
        }

        const editorRect = this.editorElement.getBoundingClientRect();

        // If we have a trigger button, position relative to it
        if (this.triggerBtn) {
            const triggerRect = this.triggerBtn.getBoundingClientRect();

            let top = triggerRect.bottom + 8;
            let left = triggerRect.left;

            // Adjust if would go off screen
            if (top + editorRect.height > window.innerHeight) {
                top = triggerRect.top - editorRect.height - 8;
            }

            // Prevent negative top
            if (top < 8) {
                top = 8;
            }

            // Adjust horizontal position
            if (left + editorRect.width > window.innerWidth) {
                left = window.innerWidth - editorRect.width - 8;
            }

            // Prevent negative left
            if (left < 8) {
                left = 8;
            }

            this.editorElement.style.position = 'fixed';
            this.editorElement.style.top = `${top}px`;
            this.editorElement.style.left = `${left}px`;
            this.editorElement.style.zIndex = '10000';
        } else {
            // No trigger button - center the modal on screen
            const windowWidth = window.innerWidth;
            const windowHeight = window.innerHeight;
            const modalWidth = 600; // Default width from CSS
            const modalHeight = editorRect.height || 400;

            const left = Math.max(8, (windowWidth - modalWidth) / 2);
            const top = Math.max(8, (windowHeight - modalHeight) / 2);

            this.editorElement.style.position = 'fixed';
            this.editorElement.style.top = `${top}px`;
            this.editorElement.style.left = `${left}px`;
            this.editorElement.style.width = `${modalWidth}px`;
            this.editorElement.style.zIndex = '10000';
        }
    }

    makeDraggable(element, handle) {
        let isDragging = false;
        let startX = 0;
        let startY = 0;
        let initialX = 0;
        let initialY = 0;

        const startDrag = (e) => {
            // Only drag from the header, not from buttons
            if (e.target.closest('button')) return;

            isDragging = true;
            startX = e.clientX;
            startY = e.clientY;

            // Get current position
            const rect = element.getBoundingClientRect();
            initialX = rect.left;
            initialY = rect.top;

            // Add cursor style
            handle.style.cursor = 'grabbing';
            handle.classList.add('dragging');

            // Prevent text selection
            e.preventDefault();
        };

        const doDrag = (e) => {
            if (!isDragging) return;

            e.preventDefault();

            // Calculate new position
            const deltaX = e.clientX - startX;
            const deltaY = e.clientY - startY;

            let newLeft = initialX + deltaX;
            let newTop = initialY + deltaY;

            // Keep within viewport
            const maxX = window.innerWidth - element.offsetWidth;
            const maxY = window.innerHeight - element.offsetHeight;

            newLeft = Math.max(0, Math.min(maxX, newLeft));
            newTop = Math.max(0, Math.min(maxY, newTop));

            element.style.left = newLeft + 'px';
            element.style.top = newTop + 'px';
        };

        const stopDrag = () => {
            if (!isDragging) return;

            isDragging = false;
            handle.style.cursor = 'grab';
            handle.classList.remove('dragging');
        };

        // Add event listeners
        handle.addEventListener('mousedown', startDrag);
        document.addEventListener('mousemove', doDrag);
        document.addEventListener('mouseup', stopDrag);

        // Set initial cursor
        handle.style.cursor = 'grab';
    }

    startJobStatusPolling(jobId) {
        // Store the job ID and start polling
        this.currentJobId = jobId;
        this.pollJobStatus();
    }

    async pollJobStatus() {
        if (!this.currentJobId) return;

        try {
            const response = await fetch(`${this.apiBaseUrl}/translation-status/${this.currentJobId}/`, {
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });

            if (!response.ok) {
                throw new Error('Failed to fetch job status');
            }

            const status = await response.json();

            // Update progress
            this.updateJobProgress(status);

            // Check if job is complete
            if (status.status === 'completed') {
                this.handleJobComplete(status);
                this.currentJobId = null;
            } else if (status.status === 'failed') {
                this.handleJobFailed(status);
                this.currentJobId = null;
            } else {
                // Continue polling
                setTimeout(() => this.pollJobStatus(), 2000); // Poll every 2 seconds
            }
        } catch (error) {
            console.error('Error polling job status:', error);
            // Retry after a longer delay
            setTimeout(() => this.pollJobStatus(), 5000);
        }
    }

    updateJobProgress(status) {
        const progressBar = this.editorElement?.querySelector('.utility-progress-fill');
        const progressText = this.editorElement?.querySelector('.utility-progress-text');
        const progressContainer = this.editorElement?.querySelector('.utility-translation-progress');

        if (progressContainer) {
            progressContainer.style.display = 'block';
        }

        if (progressBar) {
            progressBar.style.width = `${status.progress || 0}%`;
        }

        if (progressText) {
            if (status.status === 'processing') {
                progressText.textContent = `Processing... ${status.progress || 0}%`;
                if (status.translated_characters && status.total_characters) {
                    progressText.textContent += ` (${status.translated_characters}/${status.total_characters} chars)`;
                }
            } else if (status.status === 'pending') {
                progressText.textContent = 'Waiting in queue...';
            }
        }
    }

    handleJobComplete(status) {
        // Update translations with completed data
        if (status.translated_data) {
            for (const [lang, data] of Object.entries(status.translated_data)) {
                this.translations[lang] = {
                    [this.currentField]: data.text || data,
                    _meta: {
                        auto: true,
                        verified: false,
                        translated_at: new Date().toISOString(),
                        job_id: status.job_id
                    }
                };
            }
        }

        // Update UI
        this.updateLanguageList();
        this.hideProgress();

        // Notify user
        if (this.isOpen) {
            const notification = document.createElement('div');
            notification.className = 'utility-notification success';
            notification.innerHTML = '<i class="fas fa-check-circle"></i> Translation completed successfully';
            this.editorElement?.appendChild(notification);
            setTimeout(() => notification.remove(), 3000);
        }
    }

    handleJobFailed(status) {
        // Remove pending status
        this.availableLanguages.forEach(lang => {
            if (this.translations[lang.code]?._meta?.job_id === status.job_id) {
                delete this.translations[lang.code]._meta.pending;
            }
        });

        // Update UI
        this.updateLanguageList();
        this.hideProgress();

        // Show error
        AdminModal.alert({message: `Translation job failed: ${status.error_message || 'Unknown error'}`, type: 'error'});
    }

    getCSRFToken() {
        // Get CSRF token from cookie or meta tag
        const cookie = document.cookie.split(';').find(c => c.trim().startsWith('csrftoken='));
        if (cookie) {
            return cookie.split('=')[1];
        }

        const meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.content : '';
    }
}

// Make available globally
window.TranslationEditor = TranslationEditor;
window.TranslationEditorUtility = TranslationEditor;