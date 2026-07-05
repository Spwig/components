/* Copyright (c) 2025-2026 Spwig. Licensed under AGPL-3.0. */

/**
 * Visibility Rules Editor Utility v1.0.1
 *
 * Allows merchants to configure visibility rules for page builder elements.
 * Rules control when elements are shown based on conditions like:
 * - User authentication status
 * - Device type (mobile, tablet, desktop)
 * - Time-based conditions
 * - User groups/roles
 * - Geographic location
 *
 * Uses the utility base structure for consistent styling.
 */

class VisibilityRulesEditor {
    constructor(options = {}) {
        this.options = {
            onChange: options.onChange || (() => {}),
            onApply: options.onApply || (() => {}),
            onClose: options.onClose || (() => {})
        };

        // Rules data
        this.rules = [];
        this.availableRuleTypes = [];
        this.savedRuleGroups = [];
        this.countries = [];

        // UI References
        this.targetElement = null;
        this.triggerButton = null;
        this.popup = null;
        this.elementId = null;
        this.isOpen = false;
        this.dragCleanup = null;

        // Bind methods
        this.handleOutsideClick = this.handleOutsideClick.bind(this);
        this.updatePreview = this.updatePreview.bind(this);

        // Load available rule types and data
        this.loadRuleTypes();
        this.loadCountries();
        this.loadSavedRuleGroups();
    }

    /**
     * Load available rule types from the API
     */
    async loadRuleTypes() {
        // Define available rule types inline for now
        // This can be expanded to load from an API endpoint
        this.availableRuleTypes = [
            {
                type: 'user_authenticated',
                label: 'User Logged In',
                icon: 'fa-user-check',
                category: 'user',
                description: 'Show only to logged in users',
                hasConfig: false
            },
            {
                type: 'user_not_authenticated',
                label: 'User Not Logged In',
                icon: 'fa-user-slash',
                category: 'user',
                description: 'Show only to guests',
                hasConfig: false
            },
            {
                type: 'user_group',
                label: 'User Group',
                icon: 'fa-users',
                category: 'user',
                description: 'Show to specific user groups',
                hasConfig: true,
                configFields: [
                    { name: 'groups', type: 'multiselect', label: 'Groups', options: [] }
                ]
            },
            {
                type: 'device_mobile',
                label: 'Mobile Only',
                icon: 'fa-mobile-alt',
                category: 'device',
                description: 'Show only on mobile devices',
                hasConfig: false
            },
            {
                type: 'device_tablet',
                label: 'Tablet Only',
                icon: 'fa-tablet-alt',
                category: 'device',
                description: 'Show only on tablets',
                hasConfig: false
            },
            {
                type: 'device_desktop',
                label: 'Desktop Only',
                icon: 'fa-desktop',
                category: 'device',
                description: 'Show only on desktop',
                hasConfig: false
            },
            {
                type: 'time_range',
                label: 'Time Range',
                icon: 'fa-clock',
                category: 'time',
                description: 'Show during specific hours',
                hasConfig: true,
                configFields: [
                    { name: 'start_time', type: 'time', label: 'Start Time' },
                    { name: 'end_time', type: 'time', label: 'End Time' }
                ]
            },
            {
                type: 'date_range',
                label: 'Date Range',
                icon: 'fa-calendar',
                category: 'time',
                description: 'Show during specific dates',
                hasConfig: true,
                configFields: [
                    { name: 'start_date', type: 'date', label: 'Start Date' },
                    { name: 'end_date', type: 'date', label: 'End Date' }
                ]
            },
            {
                type: 'day_of_week',
                label: 'Day of Week',
                icon: 'fa-calendar-day',
                category: 'time',
                description: 'Show on specific days',
                hasConfig: true,
                configFields: [
                    {
                        name: 'days',
                        type: 'checkboxes',
                        label: 'Days',
                        options: [
                            { value: 'monday', label: 'Mon' },
                            { value: 'tuesday', label: 'Tue' },
                            { value: 'wednesday', label: 'Wed' },
                            { value: 'thursday', label: 'Thu' },
                            { value: 'friday', label: 'Fri' },
                            { value: 'saturday', label: 'Sat' },
                            { value: 'sunday', label: 'Sun' }
                        ]
                    }
                ]
            },
            {
                type: 'geo_country',
                label: 'Country',
                icon: 'fa-globe',
                category: 'location',
                description: 'Show or hide based on visitor country',
                hasConfig: true,
                configFields: [
                    {
                        name: 'operator',
                        type: 'select',
                        label: 'Condition',
                        options: [
                            { value: 'include', label: 'Show only to visitors from' },
                            { value: 'exclude', label: 'Hide from visitors from' }
                        ]
                    },
                    { name: 'countries', type: 'multiselect', label: 'Countries', optionsKey: 'countries' }
                ]
            },
            {
                type: 'cart_has_items',
                label: 'Cart Has Items',
                icon: 'fa-shopping-cart',
                category: 'ecommerce',
                description: 'Show when cart has items',
                hasConfig: false
            },
            {
                type: 'cart_empty',
                label: 'Cart Empty',
                icon: 'fa-shopping-cart',
                category: 'ecommerce',
                description: 'Show when cart is empty',
                hasConfig: false
            },
            {
                type: 'has_purchased',
                label: 'Has Purchased',
                icon: 'fa-receipt',
                category: 'ecommerce',
                description: 'Show to customers who have made a purchase',
                hasConfig: false
            },
            {
                type: 'first_visit',
                label: 'First Visit',
                icon: 'fa-door-open',
                category: 'behavior',
                description: 'Show to first-time visitors',
                hasConfig: false
            },
            {
                type: 'returning_visitor',
                label: 'Returning Visitor',
                icon: 'fa-redo',
                category: 'behavior',
                description: 'Show to returning visitors',
                hasConfig: false
            }
        ];
    }

    /**
     * Load countries from the GeoIP API
     */
    async loadCountries() {
        try {
            const response = await fetch('/api/geoip/v1/countries/');
            if (response.ok) {
                const data = await response.json();
                this.countries = data.map(country => ({
                    value: country.code,
                    label: `${country.flag} ${country.name}`
                }));
            }
        } catch (e) {
            console.warn('Failed to load countries:', e);
            this.countries = [];
        }
    }

    /**
     * Load saved rule groups from the Page Builder API
     */
    async loadSavedRuleGroups() {
        try {
            const response = await fetch('/api/page-builder/visibility-rules/');
            if (response.ok) {
                const data = await response.json();
                if (data.success && data.rule_groups) {
                    this.savedRuleGroups = data.rule_groups;
                }
            }
        } catch (e) {
            console.warn('Failed to load saved rule groups:', e);
            this.savedRuleGroups = [];
        }
    }

    /**
     * Attach editor to an input element
     */
    attach(element, currentValue) {
        this.targetElement = element;

        // Get element ID for API calls
        const form = element.closest('.element-properties-form');
        this.elementId = form ? form.dataset.elementId : null;

        // Parse current value if provided
        if (currentValue) {
            this.parseValue(currentValue);
        }

        // Create trigger button
        this.createTriggerButton();

        // Update display
        this.updateDisplay();
    }

    /**
     * Parse input value
     */
    parseValue(value) {
        if (!value) {
            this.rules = [];
            return;
        }

        try {
            const parsed = typeof value === 'string' ? JSON.parse(value) : value;
            this.rules = Array.isArray(parsed) ? parsed : [];
        } catch (e) {
            console.warn('Failed to parse visibility rules:', e);
            this.rules = [];
        }
    }

    /**
     * Create trigger button following design standards
     */
    createTriggerButton() {
        const wrapper = document.createElement('div');
        wrapper.className = 'visibility-rules-trigger-wrapper';

        // Create summary display
        this.summaryDisplay = document.createElement('div');
        this.summaryDisplay.className = 'visibility-rules-summary';
        wrapper.appendChild(this.summaryDisplay);

        // Create trigger button
        this.triggerButton = document.createElement('button');
        this.triggerButton.type = 'button';
        this.triggerButton.className = 'util-btn util-btn-primary visibility-rules-trigger';
        this.triggerButton.innerHTML = '<i class="fas fa-eye"></i>';
        this.triggerButton.title = 'Configure Visibility Rules';

        wrapper.appendChild(this.triggerButton);

        // Hide original input
        this.targetElement.style.display = 'none';

        // Insert wrapper after the input element
        this.targetElement.parentNode.insertBefore(wrapper, this.targetElement.nextSibling);

        // Handle trigger click
        this.triggerButton.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            this.open();
        });
    }

    /**
     * Update the summary display
     */
    updateDisplay() {
        if (!this.summaryDisplay) return;

        if (this.rules.length === 0) {
            this.summaryDisplay.innerHTML = `
                <span class="visibility-rules-empty">
                    <i class="fas fa-eye"></i>
                    Always visible
                </span>
            `;
        } else {
            const ruleIcons = this.rules.slice(0, 3).map(rule => {
                // Handle saved rule groups
                if (rule.type === 'rule_group') {
                    return `<i class="fas fa-layer-group" title="${rule.name || 'Saved Rule Group'}"></i>`;
                }
                const ruleType = this.availableRuleTypes.find(t => t.type === rule.type);
                const icon = ruleType ? ruleType.icon : 'fa-filter';
                return `<i class="fas ${icon}" title="${ruleType ? ruleType.label : rule.type}"></i>`;
            }).join('');

            const moreCount = this.rules.length > 3 ? `+${this.rules.length - 3}` : '';

            this.summaryDisplay.innerHTML = `
                <span class="visibility-rules-active">
                    ${ruleIcons}
                    ${moreCount ? `<span class="more-count">${moreCount}</span>` : ''}
                    <span class="rule-count">${this.rules.length} rule${this.rules.length !== 1 ? 's' : ''}</span>
                </span>
            `;
        }
    }

    /**
     * Open the editor popup
     */
    open() {
        if (this.isOpen) return;

        this.createPopup();
        this.isOpen = true;

        // Add outside click listener
        setTimeout(() => {
            document.addEventListener('mousedown', this.handleOutsideClick);
        }, 100);
    }

    /**
     * Close the editor popup
     */
    close() {
        if (!this.isOpen) return;

        if (this.popup) {
            this.popup.remove();
            this.popup = null;
        }

        if (this.dragCleanup) {
            this.dragCleanup();
            this.dragCleanup = null;
        }

        document.removeEventListener('mousedown', this.handleOutsideClick);
        this.isOpen = false;
        this.options.onClose();
    }

    /**
     * Handle clicks outside the popup
     */
    handleOutsideClick(e) {
        if (this.popup && !this.popup.contains(e.target) &&
            !this.triggerButton.contains(e.target)) {
            this.close();
        }
    }

    /**
     * Create the editor popup using utility base structure
     */
    createPopup() {
        this.popup = document.createElement('div');
        this.popup.className = 'utility-popup visibility-rules-popup';
        this.popup.innerHTML = `
            <div class="utility-header">
                <span class="utility-title"><i class="fas fa-eye"></i> Visibility Rules</span>
                <div class="utility-tools">
                    <button type="button" class="utility-close" title="Close">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            </div>
            <div class="utility-body">
                <div class="visibility-rules-description">
                    <p>Control when this element is visible. Multiple rules use AND logic (all must match).</p>
                </div>
                <div class="visibility-rules-list"></div>
                <div class="visibility-rules-add">
                    <button type="button" class="btn-add-rule">
                        <i class="fas fa-plus"></i> Add Rule
                    </button>
                </div>
            </div>
            <div class="utility-footer">
                <button type="button" class="btn btn-clear">Cancel</button>
                <button type="button" class="btn btn-apply">Apply</button>
            </div>
        `;

        // Position popup near trigger
        const triggerRect = this.triggerButton.getBoundingClientRect();
        this.popup.style.position = 'fixed';
        this.popup.style.top = `${triggerRect.bottom + 10}px`;
        this.popup.style.left = `${Math.max(10, triggerRect.left - 150)}px`;
        this.popup.style.zIndex = '10001';

        document.body.appendChild(this.popup);

        // Render current rules
        this.renderRulesList();

        // Setup event listeners
        this.setupPopupEvents();

        // Make draggable using utility header
        this.makeDraggable();
    }

    /**
     * Render the rules list
     */
    renderRulesList() {
        const listEl = this.popup.querySelector('.visibility-rules-list');
        if (!listEl) return;

        if (this.rules.length === 0) {
            listEl.innerHTML = `
                <div class="visibility-rules-empty-state">
                    <i class="fas fa-eye-slash"></i>
                    <p>No rules configured</p>
                    <p class="hint">Element is always visible</p>
                </div>
            `;
            return;
        }

        listEl.innerHTML = this.rules.map((rule, index) => {
            // Handle saved rule groups
            if (rule.type === 'rule_group') {
                return `
                    <div class="visibility-rule-item" data-index="${index}">
                        <div class="rule-icon">
                            <i class="fas fa-layer-group"></i>
                        </div>
                        <div class="rule-info">
                            <span class="rule-label">${rule.name || 'Saved Rule Group'}</span>
                            <span class="rule-config">Rule Group #${rule.rule_group_id}</span>
                        </div>
                        <div class="rule-actions">
                            <button type="button" class="btn-remove-rule" title="Remove">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </div>
                `;
            }

            const ruleType = this.availableRuleTypes.find(t => t.type === rule.type);
            const icon = ruleType ? ruleType.icon : 'fa-filter';
            const label = ruleType ? ruleType.label : rule.type;
            const configDisplay = this.formatRuleConfig(rule);

            return `
                <div class="visibility-rule-item" data-index="${index}">
                    <div class="rule-icon">
                        <i class="fas ${icon}"></i>
                    </div>
                    <div class="rule-info">
                        <span class="rule-label">${label}</span>
                        ${configDisplay ? `<span class="rule-config">${configDisplay}</span>` : ''}
                    </div>
                    <div class="rule-actions">
                        ${ruleType && ruleType.hasConfig ? `
                            <button type="button" class="btn-edit-rule" title="Edit">
                                <i class="fas fa-pencil-alt"></i>
                            </button>
                        ` : ''}
                        <button type="button" class="btn-remove-rule" title="Remove">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
            `;
        }).join('');

        // Add event listeners to rule items
        listEl.querySelectorAll('.btn-remove-rule').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const index = parseInt(e.target.closest('.visibility-rule-item').dataset.index);
                this.removeRule(index);
            });
        });

        listEl.querySelectorAll('.btn-edit-rule').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const index = parseInt(e.target.closest('.visibility-rule-item').dataset.index);
                this.editRule(index);
            });
        });
    }

    /**
     * Format rule configuration for display
     */
    formatRuleConfig(rule) {
        if (!rule.config) return '';

        const parts = [];

        if (rule.config.start_time && rule.config.end_time) {
            parts.push(`${rule.config.start_time} - ${rule.config.end_time}`);
        }

        if (rule.config.start_date && rule.config.end_date) {
            parts.push(`${rule.config.start_date} to ${rule.config.end_date}`);
        }

        if (rule.config.days && Array.isArray(rule.config.days)) {
            parts.push(rule.config.days.join(', '));
        }

        if (rule.config.countries && Array.isArray(rule.config.countries)) {
            const operatorLabel = rule.config.operator === 'exclude' ? 'Hide from: ' : 'Show to: ';
            const countriesList = rule.config.countries.slice(0, 3).join(', ') +
                (rule.config.countries.length > 3 ? `... (+${rule.config.countries.length - 3})` : '');
            parts.push(operatorLabel + countriesList);
        }

        if (rule.config.groups && Array.isArray(rule.config.groups)) {
            parts.push(rule.config.groups.join(', '));
        }

        return parts.join(' | ');
    }

    /**
     * Setup popup event listeners
     */
    setupPopupEvents() {
        // Close button
        this.popup.querySelector('.utility-close').addEventListener('click', () => {
            this.close();
        });

        // Cancel button
        this.popup.querySelector('.btn-clear').addEventListener('click', () => {
            this.close();
        });

        // Apply button
        this.popup.querySelector('.btn-apply').addEventListener('click', () => {
            this.apply();
        });

        // Add rule button
        this.popup.querySelector('.btn-add-rule').addEventListener('click', () => {
            this.showRuleTypeSelector();
        });
    }

    /**
     * Show rule type selector
     */
    showRuleTypeSelector() {
        // Group rules by category
        const categories = {};
        this.availableRuleTypes.forEach(ruleType => {
            if (!categories[ruleType.category]) {
                categories[ruleType.category] = [];
            }
            categories[ruleType.category].push(ruleType);
        });

        const categoryLabels = {
            saved: 'Saved Rule Groups',
            user: 'User',
            device: 'Device',
            time: 'Time & Date',
            location: 'Location',
            ecommerce: 'E-Commerce',
            behavior: 'Behavior'
        };

        // Get language prefix for admin URLs
        const lang = document.documentElement.lang || 'en';
        const manageRulesUrl = `/${lang}/admin/page_builder/rulegroup/`;

        // Build saved rule groups section HTML
        let savedRulesHtml = `
            <div class="rule-category">
                <h5>${categoryLabels.saved}</h5>
                ${this.savedRuleGroups.length > 0 ? `
                    <div class="rule-type-list">
                        ${this.savedRuleGroups.map(group => `
                            <button type="button" class="rule-type-option saved-rule-group" data-group-id="${group.id}">
                                <i class="fas fa-layer-group"></i>
                                <span class="rule-type-label">${group.name}</span>
                                <span class="rule-type-desc">${group.rules_summary || group.description || `${group.rules_count} rules (${group.logic_operator})`}</span>
                            </button>
                        `).join('')}
                    </div>
                ` : `
                    <div class="rule-type-empty">
                        <p>No saved rule groups yet</p>
                    </div>
                `}
                <div class="rule-category-actions">
                    <a href="${manageRulesUrl}" target="_blank" class="btn-manage-rules">
                        <i class="fas fa-cog"></i> Manage Rule Groups
                    </a>
                </div>
            </div>
        `;

        // Create selector modal
        const selector = document.createElement('div');
        selector.className = 'visibility-rule-selector';
        selector.innerHTML = `
            <div class="rule-selector-header">
                <h4>Add Visibility Rule</h4>
                <button type="button" class="btn-close-selector">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div class="rule-selector-content">
                ${savedRulesHtml}
                ${Object.entries(categories).filter(([cat]) => cat !== 'saved').map(([category, types]) => `
                    <div class="rule-category">
                        <h5>${categoryLabels[category] || category}</h5>
                        <div class="rule-type-list">
                            ${types.map(ruleType => `
                                <button type="button" class="rule-type-option" data-type="${ruleType.type}">
                                    <i class="fas ${ruleType.icon}"></i>
                                    <span class="rule-type-label">${ruleType.label}</span>
                                    <span class="rule-type-desc">${ruleType.description}</span>
                                </button>
                            `).join('')}
                        </div>
                    </div>
                `).join('')}
            </div>
        `;

        // Show selector
        const content = this.popup.querySelector('.utility-body');
        content.appendChild(selector);

        // Add event listeners
        selector.querySelector('.btn-close-selector').addEventListener('click', () => {
            selector.remove();
        });

        // Handle saved rule group selection
        selector.querySelectorAll('.saved-rule-group').forEach(btn => {
            btn.addEventListener('click', () => {
                const groupId = parseInt(btn.dataset.groupId);
                const group = this.savedRuleGroups.find(g => g.id === groupId);
                if (group) {
                    this.addRule({
                        type: 'rule_group',
                        rule_group_id: groupId,
                        name: group.name
                    });
                }
                selector.remove();
            });
        });

        // Handle regular rule type selection
        selector.querySelectorAll('.rule-type-option:not(.saved-rule-group)').forEach(btn => {
            btn.addEventListener('click', () => {
                const type = btn.dataset.type;
                const ruleType = this.availableRuleTypes.find(t => t.type === type);

                if (ruleType && ruleType.hasConfig) {
                    selector.remove();
                    this.showRuleConfigForm(ruleType);
                } else {
                    this.addRule({ type });
                    selector.remove();
                }
            });
        });
    }

    /**
     * Show rule configuration form
     */
    showRuleConfigForm(ruleType, existingRule = null, editIndex = null) {
        const isEdit = editIndex !== null;
        const config = existingRule ? existingRule.config : {};

        const form = document.createElement('div');
        form.className = 'visibility-rule-config-form';
        form.innerHTML = `
            <div class="rule-config-header">
                <h4>
                    <i class="fas ${ruleType.icon}"></i>
                    ${isEdit ? 'Edit' : 'Configure'} ${ruleType.label}
                </h4>
                <button type="button" class="btn-close-config">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div class="rule-config-content">
                ${ruleType.configFields.map(field => this.renderConfigField(field, config[field.name])).join('')}
            </div>
            <div class="rule-config-actions">
                <button type="button" class="btn btn-clear">Cancel</button>
                <button type="button" class="btn btn-apply">
                    ${isEdit ? 'Update' : 'Add'} Rule
                </button>
            </div>
        `;

        // Show form
        const content = this.popup.querySelector('.utility-body');
        content.appendChild(form);

        // Add event listeners
        form.querySelector('.btn-close-config').addEventListener('click', () => {
            form.remove();
        });

        form.querySelector('.btn-clear').addEventListener('click', () => {
            form.remove();
        });

        form.querySelector('.btn-apply').addEventListener('click', () => {
            const formConfig = {};

            ruleType.configFields.forEach(field => {
                const input = form.querySelector(`[name="${field.name}"]`);
                if (input) {
                    if (field.type === 'checkboxes') {
                        const checkedBoxes = form.querySelectorAll(`input[name="${field.name}"]:checked`);
                        formConfig[field.name] = Array.from(checkedBoxes).map(cb => cb.value);
                    } else {
                        formConfig[field.name] = input.value;
                    }
                }
            });

            const rule = { type: ruleType.type, config: formConfig };

            if (isEdit) {
                this.rules[editIndex] = rule;
                this.renderRulesList();
            } else {
                this.addRule(rule);
            }

            form.remove();
        });
    }

    /**
     * Render a configuration field
     */
    renderConfigField(field, value) {
        // Get options from optionsKey if specified (dynamic options)
        let options = field.options || [];
        if (field.optionsKey && this[field.optionsKey]) {
            options = this[field.optionsKey];
        }

        switch (field.type) {
            case 'time':
                return `
                    <div class="control-group">
                        <label>${field.label}</label>
                        <input type="time" name="${field.name}" value="${value || ''}">
                    </div>
                `;

            case 'date':
                return `
                    <div class="control-group">
                        <label>${field.label}</label>
                        <input type="date" name="${field.name}" value="${value || ''}">
                    </div>
                `;

            case 'checkboxes':
                return `
                    <div class="control-group config-field-checkboxes">
                        <label>${field.label}</label>
                        <div class="checkbox-group">
                            ${options.map(opt => `
                                <label class="checkbox-option">
                                    <input type="checkbox" name="${field.name}" value="${opt.value}"
                                        ${value && Array.isArray(value) && value.includes(opt.value) ? 'checked' : ''}>
                                    <span>${opt.label}</span>
                                </label>
                            `).join('')}
                        </div>
                    </div>
                `;

            case 'multiselect':
                return `
                    <div class="control-group">
                        <label>${field.label}</label>
                        <select name="${field.name}" multiple class="multiselect-field" size="8">
                            ${options.map(opt => `
                                <option value="${opt.value}"
                                    ${value && Array.isArray(value) && value.includes(opt.value) ? 'selected' : ''}>
                                    ${opt.label}
                                </option>
                            `).join('')}
                        </select>
                        <small class="field-hint">Hold Ctrl/Cmd to select multiple</small>
                    </div>
                `;

            case 'select':
                return `
                    <div class="control-group">
                        <label>${field.label}</label>
                        <select name="${field.name}" class="select-field">
                            ${options.map(opt => `
                                <option value="${opt.value}" ${value === opt.value ? 'selected' : ''}>
                                    ${opt.label}
                                </option>
                            `).join('')}
                        </select>
                    </div>
                `;

            default:
                return `
                    <div class="control-group">
                        <label>${field.label}</label>
                        <input type="text" name="${field.name}" value="${value || ''}">
                    </div>
                `;
        }
    }

    /**
     * Add a rule
     */
    addRule(rule) {
        this.rules.push(rule);
        this.renderRulesList();
    }

    /**
     * Remove a rule
     */
    removeRule(index) {
        this.rules.splice(index, 1);
        this.renderRulesList();
    }

    /**
     * Edit a rule
     */
    editRule(index) {
        const rule = this.rules[index];
        const ruleType = this.availableRuleTypes.find(t => t.type === rule.type);

        if (ruleType && ruleType.hasConfig) {
            this.showRuleConfigForm(ruleType, rule, index);
        }
    }

    /**
     * Apply changes
     */
    apply() {
        // Update input value
        const value = JSON.stringify(this.rules);
        this.targetElement.value = value;

        // Trigger change event
        this.targetElement.dispatchEvent(new Event('change', { bubbles: true }));

        // Update display
        this.updateDisplay();

        // Call callbacks
        this.options.onApply(this.rules);
        this.options.onChange(this.rules);

        // Close popup
        this.close();
    }

    /**
     * Update preview (for live preview integration)
     */
    updatePreview() {
        if (!this.elementId || !window.livePreview) return;
        // Visibility rules don't affect live preview styling
    }

    /**
     * Make popup draggable using utility header
     */
    makeDraggable() {
        const header = this.popup.querySelector('.utility-header');
        if (!header) return;

        let isDragging = false;
        let startX, startY, initialLeft, initialTop;

        const onMouseDown = (e) => {
            if (e.target.closest('.utility-close') || e.target.closest('.utility-tools button')) return;

            isDragging = true;
            startX = e.clientX;
            startY = e.clientY;

            const rect = this.popup.getBoundingClientRect();
            initialLeft = rect.left;
            initialTop = rect.top;

            header.style.cursor = 'grabbing';
            header.classList.add('dragging');
            e.preventDefault();
        };

        const onMouseMove = (e) => {
            if (!isDragging) return;

            const deltaX = e.clientX - startX;
            const deltaY = e.clientY - startY;

            this.popup.style.left = `${initialLeft + deltaX}px`;
            this.popup.style.top = `${initialTop + deltaY}px`;
        };

        const onMouseUp = () => {
            isDragging = false;
            header.style.cursor = 'grab';
            header.classList.remove('dragging');
        };

        header.addEventListener('mousedown', onMouseDown);
        document.addEventListener('mousemove', onMouseMove);
        document.addEventListener('mouseup', onMouseUp);

        header.style.cursor = 'grab';

        this.dragCleanup = () => {
            header.removeEventListener('mousedown', onMouseDown);
            document.removeEventListener('mousemove', onMouseMove);
            document.removeEventListener('mouseup', onMouseUp);
        };
    }

    /**
     * Get current value
     */
    getValue() {
        return this.rules;
    }

    /**
     * Set value
     */
    setValue(value) {
        this.parseValue(value);
        this.updateDisplay();
    }

    /**
     * Destroy the editor
     */
    destroy() {
        this.close();
        if (this.triggerButton) {
            this.triggerButton.remove();
        }
        if (this.summaryDisplay) {
            this.summaryDisplay.parentElement.remove();
        }
    }
}

// Make available globally
window.VisibilityRulesEditor = VisibilityRulesEditor;
