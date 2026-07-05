/* Copyright (c) 2025-2026 Spwig. Licensed under AGPL-3.0. */

/**
 * Modern Spacing Editor Utility
 *
 * Follows page builder design principles:
 * - Uses utility-popup base structure
 * - Implements draggable header
 * - Supports dark theme
 * - Proper CSS scoping
 * - LivePreviewManager integration
 */

class SpacingEditor {
    constructor(options = {}) {
        this.options = {
            propertyKey: options.propertyKey,  // Property key for live preview routing (e.g., 'button_padding')
            elementId: options.elementId,
            elementType: options.elementType,
            mode: options.mode || 'both', // 'margin', 'padding', or 'both'
            units: options.units || ['px', 'em', 'rem', '%', 'auto'],
            defaultUnit: options.defaultUnit || 'px',
            min: options.min || 0,
            max: options.max || 200,
            step: options.step || 1,
            showPresets: options.showPresets !== false,
            showVisualEditor: options.showVisualEditor !== false,
            onChange: options.onChange || (() => {}),
            onApply: options.onApply || (() => {}),
            onClose: options.onClose || (() => {})
        };

        // Default spacing structure
        this.spacing = {
            margin: {
                top: { value: 0, unit: this.options.defaultUnit },
                right: { value: 0, unit: this.options.defaultUnit },
                bottom: { value: 0, unit: this.options.defaultUnit },
                left: { value: 0, unit: this.options.defaultUnit },
                linked: true
            },
            padding: {
                top: { value: 0, unit: this.options.defaultUnit },
                right: { value: 0, unit: this.options.defaultUnit },
                bottom: { value: 0, unit: this.options.defaultUnit },
                left: { value: 0, unit: this.options.defaultUnit },
                linked: true
            }
        };

        // UI References
        this.targetElement = null;
        this.triggerButton = null;
        this.popup = null;
        this.elementId = null;
        this.isOpen = false;
        this.dragCleanup = null;

        // Bind methods
        this.updateSpacingValue = this.updateSpacingValue.bind(this);
        this.generateCSS = this.generateCSS.bind(this);
        this.updatePreview = this.updatePreview.bind(this);
        this.handleOutsideClick = this.handleOutsideClick.bind(this);
    }

    /**
     * Attach spacing editor to an input element
     */
    attach(element, currentValue) {
        this.targetElement = element;

        // Get element ID for live preview support
        const form = element.closest('.element-properties-form');
        this.elementId = form ? form.dataset.elementId : null;

        // Parse current value if provided
        if (currentValue) {
            this.parseValue(currentValue);
        }

        // Create trigger button
        this.createTriggerButton();
    }

    /**
     * Create trigger button following design standards
     */
    createTriggerButton() {
        this.triggerButton = document.createElement('button');
        this.triggerButton.type = 'button';
        this.triggerButton.className = 'util-btn util-btn-primary spacing-editor-trigger';
        this.triggerButton.innerHTML = '<i class="fas fa-expand-arrows-alt"></i>';
        this.triggerButton.title = 'Open Spacing Editor';

        // Insert after the input element
        this.targetElement.parentNode.insertBefore(this.triggerButton, this.targetElement.nextSibling);

        // Handle trigger click
        this.triggerButton.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            this.open();
        });
    }

    /**
     * Parse input value (CSS or JSON)
     */
    parseValue(value) {
        if (!value) return;

        try {
            // Try to parse as JSON first (our format)
            const parsed = JSON.parse(value);
            if (parsed.margin || parsed.padding) {
                this.spacing = { ...this.spacing, ...parsed };
                return;
            }
        } catch (e) {
            // Not JSON, try to parse as CSS
        }

        // Parse CSS shorthand values
        this.parseCSSValue(value);
    }

    /**
     * Parse CSS shorthand values
     */
    parseCSSValue(cssValue) {
        const marginMatch = cssValue.match(/margin:\s*([^;]+)/);
        const paddingMatch = cssValue.match(/padding:\s*([^;]+)/);

        if (marginMatch) {
            this.parseSpacingShorthand('margin', marginMatch[1].trim());
        }

        if (paddingMatch) {
            this.parseSpacingShorthand('padding', paddingMatch[1].trim());
        }
    }

    /**
     * Parse spacing shorthand (e.g., "10px 20px")
     */
    parseSpacingShorthand(type, value) {
        const parts = value.split(/\s+/);
        const numericValue = (str) => parseFloat(str) || 0;
        const unitValue = (str) => str.replace(/[0-9.-]/g, '') || 'px';

        switch (parts.length) {
            case 1:
                // all sides
                this.spacing[type].top = { value: numericValue(parts[0]), unit: unitValue(parts[0]) };
                this.spacing[type].right = { value: numericValue(parts[0]), unit: unitValue(parts[0]) };
                this.spacing[type].bottom = { value: numericValue(parts[0]), unit: unitValue(parts[0]) };
                this.spacing[type].left = { value: numericValue(parts[0]), unit: unitValue(parts[0]) };
                break;
            case 2:
                // vertical horizontal
                this.spacing[type].top = { value: numericValue(parts[0]), unit: unitValue(parts[0]) };
                this.spacing[type].bottom = { value: numericValue(parts[0]), unit: unitValue(parts[0]) };
                this.spacing[type].right = { value: numericValue(parts[1]), unit: unitValue(parts[1]) };
                this.spacing[type].left = { value: numericValue(parts[1]), unit: unitValue(parts[1]) };
                break;
            case 4:
                // top right bottom left
                this.spacing[type].top = { value: numericValue(parts[0]), unit: unitValue(parts[0]) };
                this.spacing[type].right = { value: numericValue(parts[1]), unit: unitValue(parts[1]) };
                this.spacing[type].bottom = { value: numericValue(parts[2]), unit: unitValue(parts[2]) };
                this.spacing[type].left = { value: numericValue(parts[3]), unit: unitValue(parts[3]) };
                break;
        }
    }

    /**
     * Open spacing editor popup
     */
    open() {
        if (this.isOpen) return;

        // Create popup using utility base structure
        this.popup = document.createElement('div');
        this.popup.className = 'spacing-editor-popup utility-popup';
        this.popup.innerHTML = this.createPopupHTML();

        document.body.appendChild(this.popup);
        this.isOpen = true;

        // Make popup draggable
        const header = this.popup.querySelector('.utility-header');
        if (header) {
            this.makeDraggable(this.popup, header);
        }

        // Position popup
        this.position();

        // Setup event listeners
        this.setupEventListeners();

        // Update UI to reflect current values
        this.updateUI();

        // Setup outside click handler
        setTimeout(() => {
            document.addEventListener('click', this.handleOutsideClick);
        }, 100);
    }

    /**
     * Create popup HTML following utility base structure
     */
    createPopupHTML() {
        const showMargin = this.options.mode === 'both' || this.options.mode === 'margin';
        const showPadding = this.options.mode === 'both' || this.options.mode === 'padding';

        return `
            <div class="utility-header">
                <h4 class="utility-title">Spacing Editor</h4>
                <div class="utility-tools">
                    <button class="utility-close close-btn">&times;</button>
                </div>
            </div>

            <div class="utility-body">
                ${this.options.showVisualEditor ? this.createVisualEditorHTML() : ''}

                ${this.options.mode === 'both' ? `
                    <div class="admin-tabs">
                        <button class="admin-tab-btn active" data-tab="margin">Margin</button>
                        <button class="admin-tab-btn" data-tab="padding">Padding</button>
                    </div>
                ` : ''}

                <div class="spacing-content">
                    ${showMargin ? this.createSpacingSection('margin', 'Margin') : ''}
                    ${showPadding ? this.createSpacingSection('padding', 'Padding') : ''}
                </div>

                ${this.options.showPresets ? this.createPresetsHTML() : ''}

                <div class="spacing-actions">
                    <button class="apply-btn">Apply</button>
                    <button class="clear-btn">Clear</button>
                </div>
            </div>
        `;
    }


    /**
     * Create spacing section HTML
     */
    createSpacingSection(type, label) {
        const isVisible = this.options.mode !== 'both' || type === 'margin';

        return `
            <div class="spacing-section spacing-${type}" ${isVisible ? '' : 'style="display: none;"'}>
                <div class="section-header">
                    <span class="section-label">${label}</span>
                    <button class="link-btn ${this.spacing[type].linked ? 'linked' : ''}"
                            data-type="${type}" title="Link/Unlink values">
                        <i class="fas fa-${this.spacing[type].linked ? 'link' : 'unlink'}"></i>
                    </button>
                </div>

                <div class="spacing-inputs">
                    ${['top', 'right', 'bottom', 'left'].map(side => `
                        <div class="spacing-input-group">
                            <label class="spacing-label">${side}</label>
                            <div class="input-with-unit">
                                <input type="number"
                                       class="spacing-input"
                                       data-type="${type}"
                                       data-side="${side}"
                                       min="${this.options.min}"
                                       max="${this.options.max}"
                                       step="${this.options.step}"
                                       value="${this.spacing[type][side].value}">
                                <select class="unit-select" data-type="${type}" data-side="${side}">
                                    ${this.options.units.map(unit =>
                                        `<option value="${unit}" ${this.spacing[type][side].unit === unit ? 'selected' : ''}>${unit}</option>`
                                    ).join('')}
                                </select>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    /**
     * Create visual editor HTML
     */
    createVisualEditorHTML() {
        return `
            <div class="visual-spacing-editor">
                <div class="visual-container">
                    <div class="margin-visual">
                        <div class="margin-handle margin-top" data-type="margin" data-side="top"></div>
                        <div class="margin-handle margin-right" data-type="margin" data-side="right"></div>
                        <div class="margin-handle margin-bottom" data-type="margin" data-side="bottom"></div>
                        <div class="margin-handle margin-left" data-type="margin" data-side="left"></div>

                        <div class="padding-visual">
                            <div class="padding-handle padding-top" data-type="padding" data-side="top"></div>
                            <div class="padding-handle padding-right" data-type="padding" data-side="right"></div>
                            <div class="padding-handle padding-bottom" data-type="padding" data-side="bottom"></div>
                            <div class="padding-handle padding-left" data-type="padding" data-side="left"></div>

                            <div class="content-area">Content</div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Create presets HTML
     */
    createPresetsHTML() {
        const presets = [
            { label: 'None', value: '0px' },
            { label: 'Small', value: '8px' },
            { label: 'Medium', value: '16px' },
            { label: 'Large', value: '24px' },
            { label: 'XL', value: '32px' }
        ];

        return `
            <div class="spacing-presets">
                <div class="presets-label">Quick Presets:</div>
                <div class="preset-buttons">
                    ${presets.map(preset =>
                        `<button class="preset-btn" data-value="${preset.value}">${preset.label}</button>`
                    ).join('')}
                </div>
            </div>
        `;
    }

    /**
     * Make popup draggable by header
     */
    makeDraggable(element, handle) {
        let isDragging = false;
        let initialX = 0;
        let initialY = 0;

        const startDrag = (e) => {
            // Only drag from the header, not from buttons
            if (e.target.closest('button')) return;

            isDragging = true;
            const rect = element.getBoundingClientRect();
            initialX = e.clientX - rect.left;
            initialY = e.clientY - rect.top;

            // Add cursor style
            handle.style.cursor = 'grabbing';
            handle.classList.add('dragging');

            // Prevent text selection
            e.preventDefault();
        };

        const doDrag = (e) => {
            if (!isDragging) return;

            const newX = e.clientX - initialX;
            const newY = e.clientY - initialY;

            // Keep popup within viewport
            const maxX = window.innerWidth - element.offsetWidth;
            const maxY = window.innerHeight - element.offsetHeight;

            const constrainedX = Math.max(0, Math.min(maxX, newX));
            const constrainedY = Math.max(0, Math.min(maxY, newY));

            element.style.left = constrainedX + 'px';
            element.style.top = constrainedY + 'px';
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

        // Store cleanup function
        this.dragCleanup = () => {
            handle.removeEventListener('mousedown', startDrag);
            document.removeEventListener('mousemove', doDrag);
            document.removeEventListener('mouseup', stopDrag);
        };
    }

    /**
     * Position popup near trigger button
     */
    position() {
        if (!this.popup || !this.triggerButton) return;

        const triggerRect = this.triggerButton.getBoundingClientRect();
        const popupRect = this.popup.getBoundingClientRect();

        let left = triggerRect.right + 10;
        let top = triggerRect.top;

        // Keep popup within viewport
        if (left + popupRect.width > window.innerWidth) {
            left = triggerRect.left - popupRect.width - 10;
        }

        if (top + popupRect.height > window.innerHeight) {
            top = window.innerHeight - popupRect.height - 10;
        }

        if (left < 0) left = 10;
        if (top < 0) top = 10;

        this.popup.style.left = left + 'px';
        this.popup.style.top = top + 'px';
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Close button
        this.popup.querySelector('.close-btn').addEventListener('click', () => this.close());

        // Tab switching
        if (this.options.mode === 'both') {
            this.popup.querySelectorAll('.admin-tab-btn').forEach(tab => {
                tab.addEventListener('click', (e) => this.switchTab(e.target.dataset.tab));
            });
        }

        // Spacing inputs
        this.popup.querySelectorAll('.spacing-input').forEach(input => {
            input.addEventListener('input', (e) => {
                this.updateSpacingValue(e.target.dataset.type, e.target.dataset.side, 'value', parseFloat(e.target.value) || 0);
            });
        });

        // Unit selects
        this.popup.querySelectorAll('.unit-select').forEach(select => {
            select.addEventListener('change', (e) => {
                this.updateSpacingValue(e.target.dataset.type, e.target.dataset.side, 'unit', e.target.value);
            });
        });

        // Link buttons
        this.popup.querySelectorAll('.link-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const type = e.target.closest('.link-btn').dataset.type;
                this.toggleLink(type);
            });
        });

        // Preset buttons
        this.popup.querySelectorAll('.preset-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.applyPreset(e.target.dataset.value));
        });

        // Visual editor handles
        this.popup.querySelectorAll('.margin-handle, .padding-handle').forEach(handle => {
            this.setupHandleDrag(handle);
        });

        // Action buttons
        this.popup.querySelector('.apply-btn').addEventListener('click', () => this.apply());
        this.popup.querySelector('.clear-btn').addEventListener('click', () => this.clear());
    }

    /**
     * Setup drag functionality for visual handles
     */
    setupHandleDrag(handle) {
        const type = handle.dataset.type;
        const side = handle.dataset.side;

        handle.addEventListener('mousedown', (e) => {
            e.preventDefault();

            const startValue = this.spacing[type][side].value;
            const startX = e.clientX;
            const startY = e.clientY;
            const isVertical = ['top', 'bottom'].includes(side);

            const handleMouseMove = (e) => {
                const delta = isVertical ? (startY - e.clientY) : (e.clientX - startX);
                const newValue = Math.max(0, startValue + (delta / 2)); // Scale factor
                this.updateSpacingValue(type, side, 'value', Math.round(newValue));
            };

            const handleMouseUp = () => {
                document.removeEventListener('mousemove', handleMouseMove);
                document.removeEventListener('mouseup', handleMouseUp);
            };

            document.addEventListener('mousemove', handleMouseMove);
            document.addEventListener('mouseup', handleMouseUp);
        });
    }

    /**
     * Switch tab in both mode
     */
    switchTab(tab) {
        // Update tab buttons
        this.popup.querySelectorAll('.admin-tab-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tab);
        });

        // Update section visibility
        this.popup.querySelectorAll('.spacing-section').forEach(section => {
            section.style.display = section.classList.contains(`spacing-${tab}`) ? 'block' : 'none';
        });
    }

    /**
     * Toggle link state for spacing type
     */
    toggleLink(type) {
        this.spacing[type].linked = !this.spacing[type].linked;
        this.updateUI();
    }

    /**
     * Apply preset value
     */
    applyPreset(value) {
        const activeTab = this.popup.querySelector('.admin-tab-btn.active')?.dataset.tab ||
                         (this.options.mode === 'margin' ? 'margin' : 'padding');

        const numericValue = parseFloat(value) || 0;
        const unit = value.replace(/[0-9.-]/g, '') || 'px';

        ['top', 'right', 'bottom', 'left'].forEach(side => {
            this.spacing[activeTab][side] = { value: numericValue, unit };
        });

        this.updateUI();
        this.updatePreview();
    }

    /**
     * Update spacing value
     */
    updateSpacingValue(type, side, property, value) {
        this.spacing[type][side][property] = value;

        // If linked, update all sides
        if (this.spacing[type].linked && property === 'value') {
            ['top', 'right', 'bottom', 'left'].forEach(s => {
                if (s !== side) {
                    this.spacing[type][s][property] = value;
                }
            });
        }

        this.updateUI();
        this.updatePreview();
    }

    /**
     * Update UI to reflect current values
     */
    updateUI() {
        if (!this.popup) return;

        // Update inputs
        ['margin', 'padding'].forEach(type => {
            ['top', 'right', 'bottom', 'left'].forEach(side => {
                const input = this.popup.querySelector(`.spacing-input[data-type="${type}"][data-side="${side}"]`);
                const select = this.popup.querySelector(`.unit-select[data-type="${type}"][data-side="${side}"]`);

                if (input) input.value = this.spacing[type][side].value;
                if (select) select.value = this.spacing[type][side].unit;
            });

            // Update link button
            const linkBtn = this.popup.querySelector(`.link-btn[data-type="${type}"]`);
            if (linkBtn) {
                linkBtn.classList.toggle('linked', this.spacing[type].linked);
                linkBtn.querySelector('i').className = `fas fa-${this.spacing[type].linked ? 'link' : 'unlink'}`;
            }
        });

        // Update visual editor if present
        this.updateVisualEditor();
    }

    /**
     * Update visual editor display
     */
    updateVisualEditor() {
        // This would update the visual representation
        // Implementation depends on the visual editor design
    }

    /**
     * Generate CSS from current spacing values
     */
    generateCSS() {
        const css = [];

        ['margin', 'padding'].forEach(type => {
            if (this.options.mode === type || this.options.mode === 'both') {
                const values = this.spacing[type];
                const cssValue = this.formatSpacingValue(values);
                if (cssValue) {
                    css.push(`${type}: ${cssValue}`);
                }
            }
        });

        return css.join('; ');
    }

    /**
     * Format spacing values as CSS
     */
    formatSpacingValue(values) {
        const top = `${values.top.value}${values.top.unit}`;
        const right = `${values.right.value}${values.right.unit}`;
        const bottom = `${values.bottom.value}${values.bottom.unit}`;
        const left = `${values.left.value}${values.left.unit}`;

        // Optimize shorthand
        if (top === right && right === bottom && bottom === left) {
            return top; // All same
        } else if (top === bottom && left === right) {
            return `${top} ${right}`; // Vertical/horizontal
        } else {
            return `${top} ${right} ${bottom} ${left}`; // All different
        }
    }

    /**
     * Update live preview
     */
    updatePreview() {
        const css = this.generateCSS();

        if (this.elementId) {
            // Use LivePreviewManager for instant updates
            if (window.livePreview) {
                // Use propertyKey for element-specific routing (e.g., 'button_padding' routes to button element)
                // If propertyKey is set, send as single property; otherwise send individual CSS properties
                const updates = this.options.propertyKey
                    ? { [this.options.propertyKey]: css }
                    : this.parseGeneratedCSS(css);

                window.livePreview.updateElement(this.elementId, updates, {
                    instant: true,
                    sync: false // Don't sync to server (handled by onChange)
                });
            } else if (window.updateElementPreview) {
                // Fallback to legacy method
                window.updateElementPreview(this.elementId, { spacing: css });
            }
        }

        // Trigger onChange callback
        if (this.options.onChange) {
            this.options.onChange(css);
        }
    }

    /**
     * Parse generated CSS to individual properties for LivePreviewManager
     */
    parseGeneratedCSS(css) {
        const properties = {};

        ['margin', 'padding'].forEach(type => {
            const values = this.spacing[type];
            if (this.options.mode === type || this.options.mode === 'both') {
                properties[`${type}Top`] = `${values.top.value}${values.top.unit}`;
                properties[`${type}Right`] = `${values.right.value}${values.right.unit}`;
                properties[`${type}Bottom`] = `${values.bottom.value}${values.bottom.unit}`;
                properties[`${type}Left`] = `${values.left.value}${values.left.unit}`;
            }
        });

        return properties;
    }

    /**
     * Apply spacing and close
     */
    apply() {
        const css = this.generateCSS();

        // Update target element
        this.targetElement.value = css;

        // Trigger events
        this.targetElement.dispatchEvent(new Event('input', { bubbles: true }));
        this.targetElement.dispatchEvent(new Event('change', { bubbles: true }));

        // Trigger onApply callback
        if (this.options.onApply) {
            this.options.onApply(css);
        }

        this.close();
    }

    /**
     * Clear all spacing values
     */
    clear() {
        ['margin', 'padding'].forEach(type => {
            ['top', 'right', 'bottom', 'left'].forEach(side => {
                this.spacing[type][side] = { value: 0, unit: this.options.defaultUnit };
            });
        });

        this.updateUI();
        this.updatePreview();
    }

    /**
     * Handle outside click to close popup
     */
    handleOutsideClick(e) {
        if (this.popup && !this.popup.contains(e.target) && e.target !== this.triggerButton) {
            this.close();
        }
    }

    /**
     * Close spacing editor
     */
    close() {
        if (!this.isOpen) return;

        // Remove outside click listener
        document.removeEventListener('click', this.handleOutsideClick);

        // Clean up drag event listeners
        if (this.dragCleanup) {
            this.dragCleanup();
            this.dragCleanup = null;
        }

        if (this.popup) {
            this.popup.remove();
            this.popup = null;
        }

        this.isOpen = false;

        if (this.options.onClose) {
            this.options.onClose();
        }
    }
}

// Export for global use
window.SpacingEditor = SpacingEditor;