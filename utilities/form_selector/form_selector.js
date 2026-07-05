/* Copyright (c) 2025-2026 Spwig. Licensed under AGPL-3.0. */

/**
 * Form Selector Utility for Page Builder
 *
 * Provides a form selection dropdown that integrates with the Form Builder.
 * Features:
 * - Dropdown of available forms from Form Builder
 * - "Create New Form" option that opens Form Builder in new window
 * - BroadcastChannel listener for detecting newly created forms
 * - Form preview info display
 */

class FormSelectorUtility {
    constructor(options = {}) {
        this.options = {
            onChange: options.onChange || (() => {}),
            onApply: options.onApply || (() => {}),
            apiEndpoint: options.apiEndpoint || '/api/form-builder/forms/list/',
            createUrl: options.createUrl || '/admin/form_builder/forms/create/',
            translations: options.translations || {
                selectForm: 'Select a form...',
                createNew: 'Create New Form',
                noForms: 'No forms available',
                loading: 'Loading forms...',
                formInfo: 'Form Info',
                fields: 'fields',
                steps: 'steps',
                multiStep: 'Multi-step',
                singleStep: 'Single step',
                openBuilder: 'Edit Form',
                refresh: 'Refresh List',
            }
        };

        this.forms = [];
        this.selectedSlug = null;
        this.targetInput = null;
        this.wrapper = null;
        this.broadcastChannel = null;

        // Setup BroadcastChannel for cross-window communication
        this.setupBroadcastChannel();
    }

    /**
     * Setup BroadcastChannel to listen for new form creation
     */
    setupBroadcastChannel() {
        if ('BroadcastChannel' in window) {
            this.broadcastChannel = new BroadcastChannel('form_builder_channel');
            this.broadcastChannel.onmessage = (event) => {
                if (event.data.type === 'form_created' || event.data.type === 'form_updated') {
                    this.refreshForms();

                    // Auto-select newly created form
                    if (event.data.type === 'form_created' && event.data.slug) {
                        setTimeout(() => {
                            this.selectForm(event.data.slug);
                        }, 500);
                    }
                }
            };
        }
    }

    /**
     * Attach utility to an input element
     */
    attach(input, currentValue = '') {
        this.targetInput = input;
        this.selectedSlug = currentValue;

        // Hide the original input
        input.style.display = 'none';

        // Create wrapper element
        this.wrapper = document.createElement('div');
        this.wrapper.className = 'form-selector-wrapper';

        // Insert wrapper after the input
        input.parentNode.insertBefore(this.wrapper, input.nextSibling);

        // Render the selector UI
        this.render();

        // Fetch forms
        this.fetchForms();
    }

    /**
     * Render the selector UI
     */
    render() {
        this.wrapper.innerHTML = `
            <div class="form-selector">
                <div class="form-selector__select-wrapper">
                    <select class="form-selector__select property-select" disabled>
                        <option value="">${this.options.translations.loading}</option>
                    </select>
                    <button type="button" class="form-selector__refresh btn btn--icon btn--sm" title="${this.options.translations.refresh}">
                        <i class="fas fa-sync-alt"></i>
                    </button>
                </div>
                <div class="form-selector__actions">
                    <button type="button" class="form-selector__create btn btn--outline btn--sm">
                        <i class="fas fa-plus"></i> ${this.options.translations.createNew}
                    </button>
                </div>
                <div class="form-selector__info" style="display: none;"></div>
            </div>
        `;

        // Bind events
        this.bindEvents();
    }

    /**
     * Bind event listeners
     */
    bindEvents() {
        const select = this.wrapper.querySelector('.form-selector__select');
        const createBtn = this.wrapper.querySelector('.form-selector__create');
        const refreshBtn = this.wrapper.querySelector('.form-selector__refresh');

        // Selection change
        select.addEventListener('change', (e) => {
            this.selectForm(e.target.value);
        });

        // Create new form
        createBtn.addEventListener('click', () => {
            this.openFormBuilder();
        });

        // Refresh list
        refreshBtn.addEventListener('click', () => {
            this.refreshForms();
        });
    }

    /**
     * Fetch forms from API
     */
    async fetchForms() {
        const select = this.wrapper.querySelector('.form-selector__select');

        try {
            const response = await fetch(this.options.apiEndpoint, {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                }
            });

            if (!response.ok) {
                throw new Error('Failed to fetch forms');
            }

            const data = await response.json();
            this.forms = data.forms || [];

            // Update create URL if provided
            if (data.create_url) {
                this.options.createUrl = data.create_url;
            }

            // Populate dropdown
            this.populateSelect();

        } catch (error) {
            console.error('Error fetching forms:', error);
            select.innerHTML = `<option value="">${this.options.translations.noForms}</option>`;
            select.disabled = true;
        }
    }

    /**
     * Populate select dropdown with forms
     */
    populateSelect() {
        const select = this.wrapper.querySelector('.form-selector__select');

        // Clear existing options
        select.innerHTML = '';

        // Add placeholder option
        const placeholder = document.createElement('option');
        placeholder.value = '';
        placeholder.textContent = this.options.translations.selectForm;
        select.appendChild(placeholder);

        // Add form options
        this.forms.forEach(form => {
            const option = document.createElement('option');
            option.value = form.slug;
            option.textContent = `${form.name} (${form.field_count} ${this.options.translations.fields})`;
            if (form.is_multi_step) {
                option.textContent += ` - ${form.step_count} ${this.options.translations.steps}`;
            }
            if (form.slug === this.selectedSlug) {
                option.selected = true;
            }
            select.appendChild(option);
        });

        // Enable select
        select.disabled = false;

        // Show info for selected form
        if (this.selectedSlug) {
            this.updateFormInfo();
        }
    }

    /**
     * Select a form
     */
    selectForm(slug) {
        this.selectedSlug = slug;

        // Update hidden input
        if (this.targetInput) {
            this.targetInput.value = slug;

            // Trigger change event
            const event = new Event('change', { bubbles: true });
            this.targetInput.dispatchEvent(event);
        }

        // Update form info
        this.updateFormInfo();

        // Call onChange callback
        this.options.onChange(slug);

        // Refresh element preview if in visual builder
        // The input is inside a form with data-element-id attribute
        this.refreshElementPreview();
    }

    /**
     * Refresh the element preview in visual builder
     * This is needed because form elements require server-side rendering
     */
    refreshElementPreview() {
        if (!this.targetInput) return;

        // Find the element ID from the properties form
        const propertiesForm = this.targetInput.closest('form[data-element-id]');
        if (!propertiesForm) return;

        const elementId = propertiesForm.dataset.elementId;
        if (!elementId) return;

        // Use refreshElement if available (from visual-builder.js)
        if (window.refreshElement) {
            // Add a small delay to ensure the property save has completed
            setTimeout(() => {
                window.refreshElement(elementId);
            }, 300);
        }
    }

    /**
     * Update form info display
     */
    updateFormInfo() {
        const infoDiv = this.wrapper.querySelector('.form-selector__info');

        if (!this.selectedSlug) {
            infoDiv.style.display = 'none';
            return;
        }

        const form = this.forms.find(f => f.slug === this.selectedSlug);
        if (!form) {
            infoDiv.style.display = 'none';
            return;
        }

        const formType = form.is_multi_step ? this.options.translations.multiStep : this.options.translations.singleStep;
        const builderUrl = `/admin/form_builder/forms/${form.id}/builder/`;

        infoDiv.innerHTML = `
            <div class="form-selector__info-content">
                <div class="form-selector__info-title">${form.title}</div>
                <div class="form-selector__info-meta">
                    <span><i class="fas fa-th-list"></i> ${form.field_count} ${this.options.translations.fields}</span>
                    ${form.is_multi_step ? `<span><i class="fas fa-layer-group"></i> ${form.step_count} ${this.options.translations.steps}</span>` : ''}
                    <span class="form-selector__info-type ${form.is_multi_step ? 'multi' : 'single'}">
                        ${formType}
                    </span>
                </div>
                <a href="${builderUrl}" target="_blank" class="form-selector__edit-link">
                    <i class="fas fa-edit"></i> ${this.options.translations.openBuilder}
                </a>
            </div>
        `;

        infoDiv.style.display = 'block';
    }

    /**
     * Open Form Builder in new window
     */
    openFormBuilder(formId = null) {
        let url = this.options.createUrl;

        // If editing existing form
        if (formId) {
            url = `/admin/form_builder/forms/${formId}/builder/`;
        }

        // Open in new window
        const width = 1200;
        const height = 800;
        const left = (screen.width - width) / 2;
        const top = (screen.height - height) / 2;

        window.open(
            url,
            'FormBuilder',
            `width=${width},height=${height},left=${left},top=${top},resizable=yes,scrollbars=yes`
        );
    }

    /**
     * Refresh forms list
     */
    refreshForms() {
        const refreshBtn = this.wrapper.querySelector('.form-selector__refresh');
        const icon = refreshBtn.querySelector('i');

        // Add spinning animation
        icon.classList.add('fa-spin');

        this.fetchForms().finally(() => {
            // Remove spinning animation
            setTimeout(() => {
                icon.classList.remove('fa-spin');
            }, 300);
        });
    }

    /**
     * Close and cleanup
     */
    close() {
        if (this.broadcastChannel) {
            this.broadcastChannel.close();
        }

        if (this.wrapper && this.wrapper.parentNode) {
            this.wrapper.parentNode.removeChild(this.wrapper);
        }

        if (this.targetInput) {
            this.targetInput.style.display = '';
        }
    }

    /**
     * Get current value
     */
    getValue() {
        return this.selectedSlug;
    }

    /**
     * Set value programmatically
     */
    setValue(slug) {
        this.selectedSlug = slug;

        const select = this.wrapper.querySelector('.form-selector__select');
        if (select) {
            select.value = slug;
        }

        this.updateFormInfo();
    }
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = FormSelectorUtility;
}

// Make available globally
window.FormSelectorUtility = FormSelectorUtility;
