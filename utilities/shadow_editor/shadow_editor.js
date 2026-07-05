/* Copyright (c) 2025-2026 Spwig. Licensed under AGPL-3.0. */

/**
 * Shadow Editor Utility for Page Builder
 * Following the design principles from color picker and typography editor
 */

class ShadowEditor {
    constructor(options = {}) {
        this.options = {
            propertyKey: options.propertyKey,  // Property key for live preview routing (e.g., 'button_shadow')
            elementId: options.elementId,
            elementType: options.elementType,
            shadowType: options.shadowType || 'box', // 'box' or 'text'
            onChange: options.onChange || (() => {}),
            onApply: options.onApply || (() => {}),
            translations: options.translations || {}
        };

        this.isOpen = false;
        this.popup = null;
        this.targetElement = null;
        this.triggerButton = null;
        this.elementId = null;
        this.initialValue = '';

        // Shadow data - start with empty array to preserve 'none' state
        this.shadows = [];
        this.selectedShadowIndex = -1;

        // Color picker instances
        this.colorPickers = new Map();
    }

    createDefaultShadow() {
        return {
            type: this.options.shadowType,
            offsetX: 0,
            offsetY: 4,
            blur: 6,
            spread: this.options.shadowType === 'box' ? 0 : null,
            color: '#000000',
            opacity: 0.2,
            inset: false
        };
    }

    attach(element, value = '') {
        this.targetElement = element;
        this.initialValue = value || element.value || '';

        // Get element ID for live preview
        const elementIdInput = document.querySelector('input[name="element_id"]');
        this.elementId = elementIdInput ? elementIdInput.value : null;

        // Parse initial value
        this.parseShadow(this.initialValue);

        // Create trigger button
        this.createTrigger();
    }

    createTrigger() {
        this.triggerButton = document.createElement('button');
        this.triggerButton.className = 'util-btn util-btn-primary shadow-editor-trigger';
        this.triggerButton.type = 'button';
        this.triggerButton.innerHTML = '<i class="fas fa-layer-group"></i>';
        this.triggerButton.title = 'Shadow Editor';

        // Insert after target element
        if (this.targetElement.nextSibling) {
            this.targetElement.parentNode.insertBefore(this.triggerButton, this.targetElement.nextSibling);
        } else {
            this.targetElement.parentNode.appendChild(this.triggerButton);
        }

        // Click to open
        this.triggerButton.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            if (this.isOpen) {
                this.close();
            } else {
                this.open();
            }
        });
    }

    open() {
        if (this.isOpen) return;
        this.isOpen = true;

        // Store initial value for reset and re-parse shadows from current input
        this.initialValue = this.targetElement.value || '';
        this.parseShadow(this.initialValue);

        // Create popup
        this.createPopup();
        document.body.appendChild(this.popup);

        // Position popup
        this.position();

        // Initialize UI without triggering callbacks (initial render only)
        this.updateUIWithoutCallbacks();

        // Setup event listeners
        this.setupEventListeners();

        // Make draggable
        this.makeDraggable(this.popup, this.popup.querySelector('.shadow-editor-header'));
    }

    close() {
        if (!this.isOpen) return;
        this.isOpen = false;

        // Clean up color pickers
        this.colorPickers.forEach(picker => {
            if (picker && picker.close) {
                picker.close();
            }
        });
        this.colorPickers.clear();

        // Remove popup
        if (this.popup) {
            this.popup.remove();
            this.popup = null;
        }

        // Remove document listeners
        document.removeEventListener('mousedown', this.handleOutsideClick);
    }

    createPopup() {
        const isTextShadow = this.options.shadowType === 'text';

        this.popup = document.createElement('div');
        this.popup.className = 'shadow-editor-popup';
        this.popup.innerHTML = `
            <div class="shadow-editor-header">
                <h3 class="shadow-editor-title">${isTextShadow ? 'Text Shadow' : 'Box Shadow'} Editor</h3>
                <button type="button" class="shadow-editor-close">
                    <i class="fas fa-times"></i>
                </button>
            </div>

            <div class="shadow-editor-body">
                <!-- Preview Section -->
                <div class="shadow-preview-section">
                    <div class="preview-box">
                        <span class="preview-label">Current</span>
                        <div class="preview-shadow preview-current">
                            ${isTextShadow ?
                                `<span class="shadow-text" style="text-shadow: ${this.initialValue || 'none'}">Shadow</span>` :
                                `<div class="shadow-box" style="box-shadow: ${this.initialValue || 'none'}"></div>`
                            }
                        </div>
                    </div>
                    <i class="preview-arrow fas fa-arrow-right"></i>
                    <div class="preview-box">
                        <span class="preview-label">New</span>
                        <div class="preview-shadow preview-new">
                            ${isTextShadow ?
                                `<span class="shadow-text">Shadow</span>` :
                                `<div class="shadow-box"></div>`
                            }
                        </div>
                    </div>
                </div>

                <!-- Shadow Type Tabs -->
                <div class="admin-tabs shadow-type-tabs">
                    <button class="admin-tab-btn active" data-type="box">
                        <i class="fas fa-square"></i>
                        Box Shadow
                    </button>
                    <button class="admin-tab-btn" data-type="text">
                        <i class="fas fa-font"></i>
                        Text Shadow
                    </button>
                </div>

                <!-- Shadows List -->
                <div class="shadows-section">
                    <div class="shadows-header">
                        <h4>Shadows</h4>
                        <button class="add-shadow-btn" title="Add Shadow">
                            <i class="fas fa-plus"></i>
                        </button>
                    </div>
                    <div class="shadows-list"></div>
                </div>

                <!-- Presets -->
                <div class="shadow-presets-section">
                    <h4>Presets</h4>
                    <div class="presets-grid">
                        <button class="preset-btn" data-preset="elevation-sm" title="Small elevation">
                            <div class="preset-preview"></div>
                            <span>Small</span>
                        </button>
                        <button class="preset-btn" data-preset="elevation-md" title="Medium elevation">
                            <div class="preset-preview"></div>
                            <span>Medium</span>
                        </button>
                        <button class="preset-btn" data-preset="elevation-lg" title="Large elevation">
                            <div class="preset-preview"></div>
                            <span>Large</span>
                        </button>
                        <button class="preset-btn" data-preset="soft" title="Soft shadow">
                            <div class="preset-preview"></div>
                            <span>Soft</span>
                        </button>
                        <button class="preset-btn" data-preset="hard" title="Hard shadow">
                            <div class="preset-preview"></div>
                            <span>Hard</span>
                        </button>
                        <button class="preset-btn" data-preset="inset" title="Inset shadow">
                            <div class="preset-preview"></div>
                            <span>Inset</span>
                        </button>
                    </div>
                </div>
            </div>

            <div class="shadow-editor-footer">
                <button class="btn btn-clear">Clear</button>
                <button class="btn btn-apply">Apply</button>
            </div>
        `;

        // Update tab visibility based on shadow type
        if (isTextShadow) {
            this.popup.querySelector('[data-type="text"]').classList.add('active');
            this.popup.querySelector('[data-type="box"]').classList.remove('active');
        }

        // Hide tabs if shadow type is specific (detected from config)
        // If we're attached to a specific shadow type property, hide the tabs
        this.updateTabVisibility();
    }

    updateTabVisibility() {
        const tabsContainer = this.popup.querySelector('.shadow-type-tabs');
        if (!tabsContainer) return;

        // Hide tabs if a specific shadow type was configured
        // When shadowType is explicitly set to 'box' or 'text', we don't show tabs
        // Only show tabs if shadowType could be either (in a generic shadow property)
        const isSpecificType = this.options.shadowType &&
                              (this.options.shadowType === 'box' || this.options.shadowType === 'text');

        if (isSpecificType) {
            // Hide the tabs completely - this is a specific shadow type property
            tabsContainer.style.display = 'none';
        } else {
            // Show tabs - this is a generic shadow property that could be either type
            tabsContainer.style.display = '';
        }
    }

    setupEventListeners() {
        // Close button
        this.popup.querySelector('.shadow-editor-close').addEventListener('click', () => this.close());

        // Tab switching
        this.popup.querySelectorAll('.admin-tab-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.options.shadowType = btn.dataset.type;
                // Convert shadows to new type
                this.shadows.forEach(shadow => {
                    shadow.type = btn.dataset.type;
                    if (btn.dataset.type === 'text') {
                        delete shadow.spread;
                        delete shadow.inset;
                    } else {
                        shadow.spread = shadow.spread ?? 0;
                    }
                });
                this.updateTabs();
                this.updatePreview();
            });
        });

        // Add shadow button
        this.popup.querySelector('.add-shadow-btn').addEventListener('click', () => {
            this.addShadow();
        });

        // Preset buttons
        this.popup.querySelectorAll('.preset-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.applyPreset(btn.dataset.preset);
            });
        });

        // Footer buttons
        this.popup.querySelector('.btn-clear').addEventListener('click', () => {
            // Truly clear all shadows (generates 'none' CSS)
            this.shadows = [];
            this.selectedShadowIndex = -1;
            this.updateUI();
            this.updatePreview();  // Update live preview when clearing
        });

        this.popup.querySelector('.btn-apply').addEventListener('click', () => {
            this.applyValue();
        });

        // Click outside to close
        this.handleOutsideClick = (e) => {
            if (this.popup && !this.popup.contains(e.target) &&
                !this.triggerButton.contains(e.target)) {
                // Check if clicking on a color picker (ColorPickerUtility uses 'utility-popup color-picker')
                const isColorPicker = e.target.closest('.utility-popup.color-picker') ||
                                     e.target.closest('.color-picker-trigger');
                if (!isColorPicker) {
                    this.close();
                }
            }
        };

        setTimeout(() => {
            document.addEventListener('mousedown', this.handleOutsideClick);
        }, 100);
    }

    updateUI() {
        this.updateTabs();
        this.updateShadows();
        this.updatePreview();
        this.updatePresets();
    }

    updateUIWithoutCallbacks() {
        // Update UI elements without triggering onChange or live preview
        // Used when initially opening the popup to show current state
        this.updateTabs();
        this.updateShadows();
        this.updatePreviewVisualOnly();
        this.updatePresets();
    }

    updateTabs() {
        // Update tab buttons
        this.popup.querySelectorAll('.admin-tab-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.type === this.options.shadowType);
        });

        // Update preview section
        const isTextShadow = this.options.shadowType === 'text';
        const currentPreview = this.popup.querySelector('.preview-current');
        const newPreview = this.popup.querySelector('.preview-new');

        if (isTextShadow) {
            currentPreview.innerHTML = `<span class="shadow-text" style="text-shadow: ${this.initialValue || 'none'}">Shadow</span>`;
            newPreview.innerHTML = `<span class="shadow-text">Shadow</span>`;
        } else {
            currentPreview.innerHTML = `<div class="shadow-box" style="box-shadow: ${this.initialValue || 'none'}"></div>`;
            newPreview.innerHTML = `<div class="shadow-box"></div>`;
        }
    }

    updateShadows() {
        const container = this.popup.querySelector('.shadows-list');
        container.innerHTML = '';

        // Show empty state when no shadows
        if (this.shadows.length === 0) {
            container.innerHTML = `
                <div class="shadows-empty-state">
                    <i class="fas fa-ban"></i>
                    <p>No shadow applied</p>
                    <small>Click + to add a shadow</small>
                </div>
            `;
            return;
        }

        this.shadows.forEach((shadow, index) => {
            const isBoxShadow = shadow.type === 'box';
            const shadowEl = document.createElement('div');
            shadowEl.className = `shadow-item ${index === this.selectedShadowIndex ? 'selected' : ''}`;
            shadowEl.innerHTML = `
                <div class="shadow-item-header">
                    <span class="shadow-number">Shadow ${index + 1}</span>
                    ${this.shadows.length > 1 ? `
                        <button class="remove-shadow-btn" title="Remove">
                            <i class="fas fa-trash"></i>
                        </button>
                    ` : ''}
                </div>

                <div class="shadow-controls">
                    <!-- Position -->
                    <div class="control-row">
                        <label>Position</label>
                        <div class="position-controls">
                            <div class="input-with-label">
                                <label title="Horizontal offset (negative = left, positive = right)">
                                    <i class="fas fa-arrows-alt-h"></i>
                                </label>
                                <input type="number" class="offset-x" value="${shadow.offsetX}" placeholder="0">
                                <span class="unit">px</span>
                            </div>
                            <div class="input-with-label">
                                <label title="Vertical offset (negative = up, positive = down)">
                                    <i class="fas fa-arrows-alt-v"></i>
                                </label>
                                <input type="number" class="offset-y" value="${shadow.offsetY}" placeholder="0">
                                <span class="unit">px</span>
                            </div>
                        </div>
                    </div>

                    <!-- Blur -->
                    <div class="control-row">
                        <label>Blur</label>
                        <div class="slider-control">
                            <input type="range" class="blur-slider" min="0" max="50" value="${shadow.blur}">
                            <input type="number" class="blur-input" min="0" value="${shadow.blur}">
                            <span class="unit">px</span>
                        </div>
                    </div>

                    ${isBoxShadow ? `
                        <!-- Spread -->
                        <div class="control-row">
                            <label>Spread</label>
                            <div class="slider-control">
                                <input type="range" class="spread-slider" min="-20" max="20" value="${shadow.spread}">
                                <input type="number" class="spread-input" value="${shadow.spread}">
                                <span class="unit">px</span>
                            </div>
                        </div>
                    ` : ''}

                    <!-- Color -->
                    <div class="control-row">
                        <label>Color</label>
                        <div class="color-control">
                            <div class="color-preview" style="background: ${shadow.color}"></div>
                            <input type="text" class="color-input" value="${shadow.color}">
                        </div>
                    </div>

                    <!-- Opacity -->
                    <div class="control-row">
                        <label>Opacity</label>
                        <div class="slider-control">
                            <input type="range" class="opacity-slider" min="0" max="100" value="${Math.round(shadow.opacity * 100)}">
                            <input type="number" class="opacity-input" min="0" max="100" value="${Math.round(shadow.opacity * 100)}">
                            <span class="unit">%</span>
                        </div>
                    </div>

                    ${isBoxShadow ? `
                        <!-- Inset -->
                        <div class="control-row">
                            <label>Inset</label>
                            <label class="switch">
                                <input type="checkbox" class="inset-checkbox" ${shadow.inset ? 'checked' : ''}>
                                <span class="switch-slider"></span>
                            </label>
                        </div>
                    ` : ''}
                </div>
            `;

            // Select on click
            shadowEl.addEventListener('click', (e) => {
                if (!e.target.closest('.remove-shadow-btn')) {
                    this.selectedShadowIndex = index;
                    this.updateShadows();
                }
            });

            // Position controls
            const offsetX = shadowEl.querySelector('.offset-x');
            const offsetY = shadowEl.querySelector('.offset-y');

            offsetX.addEventListener('input', (e) => {
                shadow.offsetX = parseInt(e.target.value) || 0;
                this.updatePreview();
            });

            offsetY.addEventListener('input', (e) => {
                shadow.offsetY = parseInt(e.target.value) || 0;
                this.updatePreview();
            });

            // Blur controls
            const blurSlider = shadowEl.querySelector('.blur-slider');
            const blurInput = shadowEl.querySelector('.blur-input');

            blurSlider.addEventListener('input', (e) => {
                shadow.blur = parseInt(e.target.value);
                blurInput.value = e.target.value;
                this.updatePreview();
            });

            blurInput.addEventListener('input', (e) => {
                shadow.blur = parseInt(e.target.value) || 0;
                blurSlider.value = e.target.value;
                this.updatePreview();
            });

            // Spread controls (box shadow only)
            if (isBoxShadow) {
                const spreadSlider = shadowEl.querySelector('.spread-slider');
                const spreadInput = shadowEl.querySelector('.spread-input');

                spreadSlider?.addEventListener('input', (e) => {
                    shadow.spread = parseInt(e.target.value);
                    spreadInput.value = e.target.value;
                    this.updatePreview();
                });

                spreadInput?.addEventListener('input', (e) => {
                    shadow.spread = parseInt(e.target.value) || 0;
                    spreadSlider.value = e.target.value;
                    this.updatePreview();
                });

                // Inset checkbox
                const insetCheckbox = shadowEl.querySelector('.inset-checkbox');
                insetCheckbox?.addEventListener('change', (e) => {
                    shadow.inset = e.target.checked;
                    this.updatePreview();
                });
            }

            // Color controls
            const colorPreview = shadowEl.querySelector('.color-preview');
            const colorInput = shadowEl.querySelector('.color-input');

            // Both preview and input open color picker
            colorPreview.addEventListener('click', (e) => {
                e.stopPropagation();
                this.openColorPicker(index, colorInput);
            });

            colorInput.addEventListener('click', (e) => {
                e.stopPropagation();
                this.openColorPicker(index, colorInput);
            });

            colorInput.addEventListener('input', (e) => {
                shadow.color = e.target.value;
                colorPreview.style.background = shadow.color;
                this.updatePreview();
            });

            // Opacity controls
            const opacitySlider = shadowEl.querySelector('.opacity-slider');
            const opacityInput = shadowEl.querySelector('.opacity-input');

            opacitySlider.addEventListener('input', (e) => {
                shadow.opacity = parseInt(e.target.value) / 100;
                opacityInput.value = e.target.value;
                this.updatePreview();
            });

            opacityInput.addEventListener('input', (e) => {
                shadow.opacity = parseInt(e.target.value) / 100;
                opacitySlider.value = e.target.value;
                this.updatePreview();
            });

            // Remove button
            const removeBtn = shadowEl.querySelector('.remove-shadow-btn');
            removeBtn?.addEventListener('click', (e) => {
                e.stopPropagation();
                this.removeShadow(index);
            });

            container.appendChild(shadowEl);
        });
    }

    updatePreviewVisualOnly() {
        // Update only the popup's preview UI without triggering callbacks or live preview
        const css = this.generateCSS();
        const isTextShadow = this.options.shadowType === 'text';

        const newPreview = this.popup.querySelector('.preview-new');
        if (isTextShadow) {
            const textEl = newPreview.querySelector('.shadow-text');
            if (textEl) textEl.style.textShadow = css;
        } else {
            const boxEl = newPreview.querySelector('.shadow-box');
            if (boxEl) boxEl.style.boxShadow = css;
        }
    }

    updatePreview() {
        const css = this.generateCSS();
        const isTextShadow = this.options.shadowType === 'text';

        // Update new preview
        const newPreview = this.popup.querySelector('.preview-new');
        if (isTextShadow) {
            const textEl = newPreview.querySelector('.shadow-text');
            if (textEl) textEl.style.textShadow = css;
        } else {
            const boxEl = newPreview.querySelector('.shadow-box');
            if (boxEl) boxEl.style.boxShadow = css;
        }

        // Live update in page builder - Use LivePreviewManager for instant updates
        if (this.elementId) {
            // Use propertyKey for element-specific routing (e.g., 'button_shadow' routes to button element)
            // Falls back to CSS property name if no propertyKey provided
            const property = this.options.propertyKey || (isTextShadow ? 'textShadow' : 'boxShadow');

            if (window.livePreview) {
                // Use new LivePreviewManager for instant visual updates
                window.livePreview.updateElement(this.elementId, {
                    [property]: css
                }, { sync: false }); // Visual only, don't sync to server yet
            } else if (window.updateElementPreview) {
                // Fallback to legacy method with correct object format
                window.updateElementPreview(this.elementId, {
                    [property]: css
                });
            }
        }

        // Notify change
        this.options.onChange(css);
    }

    updatePresets() {
        const presets = {
            'elevation-sm': { box: '0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24)', text: '1px 1px 2px rgba(0,0,0,0.3)' },
            'elevation-md': { box: '0 3px 6px rgba(0,0,0,0.16), 0 3px 6px rgba(0,0,0,0.23)', text: '2px 2px 4px rgba(0,0,0,0.3)' },
            'elevation-lg': { box: '0 10px 20px rgba(0,0,0,0.19), 0 6px 6px rgba(0,0,0,0.23)', text: '3px 3px 6px rgba(0,0,0,0.3)' },
            'soft': { box: '0 0 20px rgba(0,0,0,0.15)', text: '0 0 10px rgba(0,0,0,0.3)' },
            'hard': { box: '5px 5px 0 rgba(0,0,0,0.5)', text: '3px 3px 0 rgba(0,0,0,0.5)' },
            'inset': { box: 'inset 0 2px 4px rgba(0,0,0,0.2)', text: '0 0 5px rgba(0,0,0,0.5)' }
        };

        const isTextShadow = this.options.shadowType === 'text';

        this.popup.querySelectorAll('.preset-btn').forEach(btn => {
            const preset = btn.dataset.preset;
            const preview = btn.querySelector('.preset-preview');
            if (presets[preset] && preview) {
                if (isTextShadow) {
                    preview.innerHTML = 'Aa';
                    preview.style.textShadow = presets[preset].text;
                } else {
                    preview.innerHTML = '';
                    preview.style.boxShadow = presets[preset].box;
                }
            }
        });
    }

    addShadow() {
        if (this.shadows.length >= 5) {
            AdminModal.alert({message: 'Maximum 5 shadows allowed', type: 'warning'});
            return;
        }

        this.shadows.push(this.createDefaultShadow());
        this.selectedShadowIndex = this.shadows.length - 1;
        this.updateShadows();
        this.updatePreview();
    }

    removeShadow(index) {
        if (this.shadows.length <= 1) return;

        this.shadows.splice(index, 1);

        if (this.selectedShadowIndex >= this.shadows.length) {
            this.selectedShadowIndex = this.shadows.length - 1;
        }

        this.updateShadows();
        this.updatePreview();
    }

    openColorPicker(index, inputElement) {
        // Create color picker if it doesn't exist
        if (!this.colorPickers.has(index)) {
            if (window.ColorPickerUtility) {
                const picker = new window.ColorPickerUtility({
                    showOpacity: false, // We handle opacity separately
                    onChange: (color) => {
                        const shadow = this.shadows[index];
                        shadow.color = color;

                        // Update the color input and preview
                        const shadowEl = this.popup.querySelectorAll('.shadow-item')[index];
                        if (shadowEl) {
                            const colorInput = shadowEl.querySelector('.color-input');
                            const colorPreview = shadowEl.querySelector('.color-preview');
                            if (colorInput) colorInput.value = color;
                            if (colorPreview) colorPreview.style.background = color;
                        }

                        this.updatePreview();
                    }
                });
                this.colorPickers.set(index, picker);
            }
        }

        const picker = this.colorPickers.get(index);
        if (picker) {
            const shadow = this.shadows[index];
            // ColorPickerUtility.attach() expects to be called with the input element
            picker.attach(inputElement, shadow.color);
        }
    }

    generateCSS() {
        if (this.shadows.length === 0) {
            return 'none';
        }

        return this.shadows.map(shadow => {
            const parts = [];

            // Inset (box shadow only)
            if (shadow.type === 'box' && shadow.inset) {
                parts.push('inset');
            }

            // Offsets
            parts.push(`${shadow.offsetX}px`);
            parts.push(`${shadow.offsetY}px`);

            // Blur
            parts.push(`${shadow.blur}px`);

            // Spread (box shadow only)
            if (shadow.type === 'box' && shadow.spread !== undefined) {
                parts.push(`${shadow.spread}px`);
            }

            // Color with opacity
            const color = this.addAlphaToColor(shadow.color, shadow.opacity);
            parts.push(color);

            return parts.join(' ');
        }).join(', ');
    }

    addAlphaToColor(color, alpha) {
        if (alpha >= 1) {
            return color;
        }

        // Convert hex to rgba
        if (color.startsWith('#')) {
            const r = parseInt(color.slice(1, 3), 16);
            const g = parseInt(color.slice(3, 5), 16);
            const b = parseInt(color.slice(5, 7), 16);
            return `rgba(${r}, ${g}, ${b}, ${alpha})`;
        }

        // Convert rgb() to rgba()
        const rgbMatch = color.match(/^rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)$/i);
        if (rgbMatch) {
            return `rgba(${rgbMatch[1]}, ${rgbMatch[2]}, ${rgbMatch[3]}, ${alpha})`;
        }

        // If already rgba, replace the alpha value
        const rgbaMatch = color.match(/^rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*[\d.]+\s*\)$/i);
        if (rgbaMatch) {
            return `rgba(${rgbaMatch[1]}, ${rgbaMatch[2]}, ${rgbaMatch[3]}, ${alpha})`;
        }

        return color;
    }

    parseShadow(css) {
        // Reset shadows to empty array - preserves 'none' state
        this.shadows = [];
        this.selectedShadowIndex = -1;

        // If no value or 'none', keep empty array (no shadow)
        if (!css || css === 'none' || css.trim() === '') {
            return;
        }

        // Split multiple shadows
        const shadows = css.split(/,(?![^(]*\))/);

        shadows.forEach((shadowStr, idx) => {
            const shadow = this.createDefaultShadow();
            const parts = shadowStr.trim().split(/\s+(?![^(]*\))/);

            let index = 0;

            // Check for inset
            if (parts[index] === 'inset') {
                shadow.inset = true;
                index++;
            }

            // Parse numbers
            const numbers = [];
            while (index < parts.length && /^-?\d+px$/.test(parts[index])) {
                numbers.push(parseInt(parts[index]));
                index++;
            }

            if (numbers.length >= 2) {
                shadow.offsetX = numbers[0];
                shadow.offsetY = numbers[1];
            }
            if (numbers.length >= 3) {
                shadow.blur = numbers[2];
            }
            if (numbers.length >= 4 && shadow.type === 'box') {
                shadow.spread = numbers[3];
            }

            // Parse color
            if (index < parts.length) {
                const colorStr = parts.slice(index).join(' ');
                // Extract opacity from rgba
                const rgbaMatch = colorStr.match(/rgba?\(([^)]+)\)/);
                if (rgbaMatch) {
                    const values = rgbaMatch[1].split(',').map(v => v.trim());
                    if (values.length === 4) {
                        shadow.opacity = parseFloat(values[3]);
                        shadow.color = `rgb(${values[0]}, ${values[1]}, ${values[2]})`;
                    } else {
                        shadow.color = colorStr;
                    }
                } else {
                    shadow.color = colorStr;
                }
            }

            this.shadows.push(shadow);

            // Select the first shadow by default
            if (idx === 0) {
                this.selectedShadowIndex = 0;
            }
        });
    }

    applyPreset(preset) {
        const presets = {
            'elevation-sm': [{
                ...this.createDefaultShadow(),
                offsetY: 1,
                blur: 3,
                opacity: 0.12
            }, {
                ...this.createDefaultShadow(),
                offsetY: 1,
                blur: 2,
                opacity: 0.24
            }],
            'elevation-md': [{
                ...this.createDefaultShadow(),
                offsetY: 3,
                blur: 6,
                opacity: 0.16
            }, {
                ...this.createDefaultShadow(),
                offsetY: 3,
                blur: 6,
                opacity: 0.23
            }],
            'elevation-lg': [{
                ...this.createDefaultShadow(),
                offsetY: 10,
                blur: 20,
                opacity: 0.19
            }, {
                ...this.createDefaultShadow(),
                offsetY: 6,
                blur: 6,
                opacity: 0.23
            }],
            'soft': [{
                ...this.createDefaultShadow(),
                offsetX: 0,
                offsetY: 0,
                blur: 20,
                opacity: 0.15
            }],
            'hard': [{
                ...this.createDefaultShadow(),
                offsetX: 5,
                offsetY: 5,
                blur: 0,
                opacity: 0.5
            }],
            'inset': [{
                ...this.createDefaultShadow(),
                offsetX: 0,
                offsetY: 2,
                blur: 4,
                opacity: 0.2,
                inset: true
            }]
        };

        if (presets[preset]) {
            this.shadows = presets[preset].map(s => ({
                ...s,
                type: this.options.shadowType
            }));
            this.selectedShadowIndex = 0;
            this.updateUI();
        }
    }

    applyValue() {
        const css = this.generateCSS();

        // Update input
        this.targetElement.value = css;

        // Trigger events
        this.targetElement.dispatchEvent(new Event('input', { bubbles: true }));
        this.targetElement.dispatchEvent(new Event('change', { bubbles: true }));

        // Callback
        this.options.onApply(css);

        // Close
        this.close();
    }

    position() {
        if (!this.popup || !this.triggerButton) return;

        const triggerRect = this.triggerButton.getBoundingClientRect();
        const popupRect = this.popup.getBoundingClientRect();

        // Calculate initial position
        let top = triggerRect.bottom + 8;
        let left = triggerRect.left;

        // Ensure popup stays within viewport
        const padding = 10;

        // Check right edge
        if (left + popupRect.width > window.innerWidth - padding) {
            left = window.innerWidth - popupRect.width - padding;
        }

        // Check left edge
        if (left < padding) {
            left = padding;
        }

        // Check bottom edge
        if (top + popupRect.height > window.innerHeight - padding) {
            // Try positioning above
            top = triggerRect.top - popupRect.height - 8;
        }

        // Check top edge
        if (top < padding) {
            top = padding;
        }

        this.popup.style.left = `${left}px`;
        this.popup.style.top = `${top}px`;
    }

    makeDraggable(element, handle) {
        let isDragging = false;
        let startX = 0;
        let startY = 0;
        let startLeft = 0;
        let startTop = 0;

        handle.style.cursor = 'move';

        handle.addEventListener('mousedown', (e) => {
            // Don't drag if clicking close button
            if (e.target.closest('.shadow-editor-close')) return;

            isDragging = true;
            startX = e.clientX;
            startY = e.clientY;

            const rect = element.getBoundingClientRect();
            startLeft = rect.left;
            startTop = rect.top;

            // Prevent text selection
            e.preventDefault();
        });

        document.addEventListener('mousemove', (e) => {
            if (!isDragging) return;

            const deltaX = e.clientX - startX;
            const deltaY = e.clientY - startY;

            let newLeft = startLeft + deltaX;
            let newTop = startTop + deltaY;

            // Keep within viewport
            const rect = element.getBoundingClientRect();
            const padding = 10;

            newLeft = Math.max(padding, Math.min(window.innerWidth - rect.width - padding, newLeft));
            newTop = Math.max(padding, Math.min(window.innerHeight - rect.height - padding, newTop));

            element.style.left = `${newLeft}px`;
            element.style.top = `${newTop}px`;
        });

        document.addEventListener('mouseup', () => {
            isDragging = false;
        });
    }
}

// Make globally available
window.ShadowEditor = ShadowEditor;
