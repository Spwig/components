/* Copyright (c) 2025-2026 Spwig. Licensed under AGPL-3.0. */

/**
 * Color Picker Utility for Page Builder
 *
 * Advanced color picker with support for multiple formats,
 * opacity control, and preset swatches.
 */

class ColorPickerUtility {
    constructor(options = {}) {
        this.options = {
            propertyKey: options.propertyKey,  // Property key for live preview routing (e.g., 'button_text_color')
            elementId: options.elementId,
            elementType: options.elementType,
            showOpacity: options.showOpacity !== false,
            showSwatches: options.showSwatches !== false,
            showRecent: options.showRecent !== false,
            formats: options.formats || ['hex', 'rgb', 'rgba', 'hsl', 'hsla'],
            swatches: options.swatches || this.getDefaultSwatches(),
            maxRecent: options.maxRecent || 10,
            onChange: options.onChange || (() => {}),
            onClose: options.onClose || (() => {}),
            translations: options.translations || {}
        };

        this.currentColor = null;
        this.currentFormat = 'hex';
        this.recentColors = this.loadRecentColors();
        this.pickerElement = null;
        this.targetInput = null;
        this.isOpen = false;
    }

    getDefaultSwatches() {
        return [
            // Brand colors
            '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6',
            // Neutral colors
            '#000000', '#374151', '#6b7280', '#9ca3af', '#d1d5db', '#f3f4f6', '#ffffff',
            // Additional colors
            '#dc2626', '#ea580c', '#ca8a04', '#65a30d', '#059669',
            '#0891b2', '#2563eb', '#7c3aed', '#c026d3', '#e11d48'
        ];
    }

    /**
     * Map element property names to CSS properties for live preview
     * @param {string} propertyName - Element property name (e.g., 'text_color')
     * @returns {string} CSS property name (e.g., 'color')
     */
    mapPropertyToCss(propertyName) {
        const propertyMap = {
            // Text and typography
            'text_color': 'color',
            'color': 'color',

            // Background colors
            'background_color': 'backgroundColor',
            'backgroundColor': 'backgroundColor',
            'background-color': 'backgroundColor',

            // Border colors
            'border_color': 'borderColor',
            'borderColor': 'borderColor',
            'border-color': 'borderColor',
            'border_top_color': 'borderTopColor',
            'border_right_color': 'borderRightColor',
            'border_bottom_color': 'borderBottomColor',
            'border_left_color': 'borderLeftColor',

            // Outline and shadow colors
            'outline_color': 'outlineColor',
            'accent_color': 'accentColor',

            // Custom properties (will use CSS custom property format)
            'primary_color': '--primary-color',
            'secondary_color': '--secondary-color'
        };

        return propertyMap[propertyName] || propertyName;
    }

    /**
     * Update live preview of color changes in the page builder
     * @param {string} colorValue - The color value to preview
     */
    updateLivePreview(colorValue) {
        // Use options.elementId if available (from PropertyRenderer), fall back to DOM-derived elementId
        const elementId = this.options.elementId || this.elementId;
        if (!elementId) return;

        // Use propertyKey for element-specific routing (e.g., 'button_text_color' routes to button element)
        // Falls back to CSS property mapping if no propertyKey provided
        const property = this.options.propertyKey || this.mapPropertyToCss(this.propertyName);

        if (window.livePreview) {
            // Use LivePreviewManager for instant visual updates
            window.livePreview.updateElement(elementId, {
                [property]: colorValue
            }, {
                sync: false  // Visual only, don't sync to server yet
            });
        } else if (window.updateElementPreview) {
            // Fallback to legacy method
            window.updateElementPreview(elementId, {
                [property]: colorValue
            });
        }
    }

    attach(inputElement, initialValue = '') {
        this.targetInput = inputElement;

        // Get element ID for live preview support
        const form = inputElement.closest('.element-properties-form');
        this.elementId = form ? form.dataset.elementId : null;
        this.propertyName = inputElement.name; // e.g., 'text_color', 'border_color'

        // Use the input's current value as the default color
        const currentColor = inputElement.value || initialValue || '';

        // Create trigger button using util-btn classes
        const triggerBtn = document.createElement('button');
        triggerBtn.className = 'util-btn util-btn-primary color-picker-trigger';
        triggerBtn.type = 'button';

        // Determine icon color: use selected color if valid and not transparent
        const getIconColor = (color) => {
            if (!color || color === 'transparent' || color === 'rgba(0,0,0,0)') {
                return ''; // Use default icon color
            }
            return color;
        };

        const iconColor = getIconColor(currentColor);
        triggerBtn.innerHTML = `
            <i class="fas fa-palette" style="color: ${iconColor}"></i>
        `;

        // Insert after input
        inputElement.parentNode.insertBefore(triggerBtn, inputElement.nextSibling);

        // Set up event listeners
        triggerBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            // Always use the current input value when opening
            this.open(inputElement, inputElement.value || initialValue);
        });

        // Update preview when input changes
        inputElement.addEventListener('input', (e) => {
            const icon = triggerBtn.querySelector('.fas.fa-palette');
            if (icon) {
                const newIconColor = getIconColor(e.target.value);
                icon.style.color = newIconColor;
            }

            // Update live preview for direct input changes
            this.updateLivePreview(e.target.value);
        });

        // Set initial value if input is empty and we have an initial value
        if (!inputElement.value && currentColor) {
            inputElement.value = currentColor;
        }
    }

    open(inputElement, initialValue = '') {
        if (this.isOpen) {
            this.close();
            return;
        }

        this.targetInput = inputElement;
        this.initialColor = initialValue || inputElement.value || '';

        // Parse the color and ensure we always have a valid color object
        this.currentColor = this.parseColor(this.initialColor);
        if (!this.currentColor) {
            // Default to black if no valid color provided
            this.currentColor = this.parseColor('#000000') || {
                hsl: { h: 0, s: 0, l: 0 },
                rgb: { r: 0, g: 0, b: 0 },
                alpha: 1
            };
        }

        this.isOpen = true;

        // Create picker UI
        this.createPickerUI();

        // Position near input
        this.positionPicker();

        // Add close handler for clicking outside
        setTimeout(() => {
            document.addEventListener('click', this.handleOutsideClick);
        }, 0);
    }

    close() {
        if (this.pickerElement) {
            this.pickerElement.remove();
            this.pickerElement = null;
        }

        this.isOpen = false;
        document.removeEventListener('click', this.handleOutsideClick);

        // Clean up drag event listeners
        if (this.dragCleanup) {
            this.dragCleanup();
            this.dragCleanup = null;
        }

        if (this.options.onClose) {
            this.options.onClose(this.currentColor);
        }
    }

    handleOutsideClick = (e) => {
        if (this.pickerElement && !this.pickerElement.contains(e.target) &&
            !e.target.closest('.util-btn.color-picker-trigger')) {
            this.close();
        }
    }

    createPickerUI() {
        // Remove existing picker if any
        if (this.pickerElement) {
            this.pickerElement.remove();
        }

        const picker = document.createElement('div');
        picker.className = 'utility-popup color-picker';
        picker.innerHTML = `
            <div class="utility-header">
                <span class="utility-title">${this.t('selectColor')}</span>
                <div class="utility-tools">
                    <button class="color-picker-eyedropper" type="button" title="${this.t('pickFromScreen')}">
                        <i class="fas fa-eye-dropper"></i>
                    </button>
                    <button class="utility-close" type="button">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            </div>

            <div class="utility-body">
                <!-- Color Preview -->
                <div class="color-preview-section">
                    <div class="color-preview-box">
                        <div class="preview-label">${this.t('current')}</div>
                        <div class="preview-color current-color" style="background-color: ${this.initialColor || 'transparent'}"></div>
                    </div>
                    <div class="color-preview-arrow">→</div>
                    <div class="color-preview-box">
                        <div class="preview-label">${this.t('new')}</div>
                        <div class="preview-color new-color" style="background-color: ${this.formatColor(this.currentColor, 'rgba')}"></div>
                    </div>
                </div>

                <!-- Color Canvas -->
                <div class="color-picker-canvas-wrapper">
                    <canvas class="color-picker-canvas" width="208" height="150"></canvas>
                    <div class="color-picker-cursor"></div>
                </div>

                <!-- Hue Slider -->
                <div class="color-picker-hue-wrapper">
                    <canvas class="color-picker-hue" width="208" height="20"></canvas>
                    <div class="color-picker-hue-cursor"></div>
                </div>

                ${this.options.showOpacity ? `
                <!-- Opacity Slider -->
                <div class="color-picker-opacity-wrapper">
                    <canvas class="color-picker-opacity" width="208" height="20"></canvas>
                    <div class="color-picker-opacity-cursor"></div>
                    <span class="opacity-value">100%</span>
                </div>
                ` : ''}

                <!-- Format Selector and Value -->
                <div class="color-picker-format">
                    <select class="format-selector">
                        ${this.options.formats.map(format =>
                            `<option value="${format}" ${format === this.currentFormat ? 'selected' : ''}>${format.toUpperCase()}</option>`
                        ).join('')}
                    </select>
                    <input type="text" class="color-value-input" />
                </div>

                ${this.options.showSwatches ? `
                <!-- Swatches -->
                <div class="color-picker-swatches">
                    <div class="swatches-title">${this.t('presets')}</div>
                    <div class="swatches-grid">
                        ${this.options.swatches.map(color => {
                            const hasAlpha = this.colorHasTransparency(color);
                            return `<button class="swatch" style="background-color: ${color}" data-color="${color}" ${hasAlpha ? 'data-alpha="true"' : ''} type="button"></button>`;
                        }).join('')}
                    </div>
                </div>
                ` : ''}

                ${this.options.showRecent && this.recentColors.length > 0 ? `
                <!-- Recent Colors -->
                <div class="color-picker-recent">
                    <div class="recent-title">${this.t('recent')}</div>
                    <div class="recent-grid">
                        ${this.recentColors.map(color => {
                            const hasAlpha = this.colorHasTransparency(color);
                            return `<button class="swatch" style="background-color: ${color}" data-color="${color}" ${hasAlpha ? 'data-alpha="true"' : ''} type="button"></button>`;
                        }).join('')}
                    </div>
                </div>
                ` : ''}
            </div>

            <div class="utility-footer">
                <button class="btn btn-clear" type="button">${this.t('clear')}</button>
                <button class="btn btn-apply" type="button">${this.t('apply')}</button>
            </div>
        `;

        document.body.appendChild(picker);
        this.pickerElement = picker;

        // Make the picker draggable by its header
        const header = picker.querySelector('.utility-header');
        if (header) {
            this.makeDraggable(picker, header);
        }

        // Initialize components
        this.initializeCanvas();
        this.initializeHueSlider();
        if (this.options.showOpacity) {
            this.initializeOpacitySlider();
        }
        this.initializeEventHandlers();

        // Set initial color
        this.updateFromColor(this.currentColor);
    }

    initializeCanvas() {
        const canvas = this.pickerElement.querySelector('.color-picker-canvas');
        const ctx = canvas.getContext('2d');
        const cursor = this.pickerElement.querySelector('.color-picker-cursor');

        // Draw saturation/value gradient
        this.drawCanvas();

        // Handle canvas click
        canvas.addEventListener('mousedown', (e) => {
            const rect = canvas.getBoundingClientRect();
            const norm = (v, lo, hi) => Math.max(0, Math.min(1, (v - lo) / (hi - lo)));
            const x = norm(e.clientX, rect.left, rect.right);     // 0..1 (HSV S)
            const y = norm(e.clientY, rect.top, rect.bottom);     // 0..1 (1 - HSV V)

            this.updateFromCanvas(x, y);

            // Handle drag
            const handleMove = (e2) => {
                const r = canvas.getBoundingClientRect();
                const x = norm(e2.clientX, r.left, r.right);
                const y = norm(e2.clientY, r.top, r.bottom);
                this.updateFromCanvas(x, y);
            };

            const handleUp = () => {
                document.removeEventListener('mousemove', handleMove);
                document.removeEventListener('mouseup', handleUp);
            };

            document.addEventListener('mousemove', handleMove);
            document.addEventListener('mouseup', handleUp);
        });
    }

    drawCanvas() {
        const canvas = this.pickerElement.querySelector('.color-picker-canvas');
        const ctx = canvas.getContext('2d');

        // Ensure we have a valid color - default to black if not
        if (!this.currentColor) {
            this.currentColor = this.parseColor('#000000') || {
                hsl: { h: 0, s: 0, l: 0 },
                rgb: { r: 0, g: 0, b: 0 },
                alpha: 1
            };
        }

        const { h } = this.currentColor.hsl;

        // Create horizontal gradient (white to hue)
        const gradientH = ctx.createLinearGradient(0, 0, canvas.width, 0);
        gradientH.addColorStop(0, '#ffffff');
        gradientH.addColorStop(1, `hsl(${h}, 100%, 50%)`);
        ctx.fillStyle = gradientH;
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        // Create vertical gradient (transparent to black)
        const gradientV = ctx.createLinearGradient(0, 0, 0, canvas.height);
        gradientV.addColorStop(0, 'rgba(0, 0, 0, 0)');
        gradientV.addColorStop(1, 'rgba(0, 0, 0, 1)');
        ctx.fillStyle = gradientV;
        ctx.fillRect(0, 0, canvas.width, canvas.height);
    }

    initializeHueSlider() {
        const canvas = this.pickerElement.querySelector('.color-picker-hue');
        const ctx = canvas.getContext('2d');
        const cursor = this.pickerElement.querySelector('.color-picker-hue-cursor');

        // Draw hue gradient
        const gradient = ctx.createLinearGradient(0, 0, canvas.width, 0);
        for (let i = 0; i <= 360; i += 30) {
            gradient.addColorStop(i / 360, `hsl(${i}, 100%, 50%)`);
        }
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        // Handle hue slider click
        canvas.addEventListener('mousedown', (e) => {
            const rect = canvas.getBoundingClientRect();
            const x = e.clientX - rect.left;

            this.updateHue((x / canvas.width) * 360);

            // Handle drag
            const handleMove = (e) => {
                const x = Math.max(0, Math.min(canvas.width, e.clientX - rect.left));
                this.updateHue((x / canvas.width) * 360);
            };

            const handleUp = () => {
                document.removeEventListener('mousemove', handleMove);
                document.removeEventListener('mouseup', handleUp);
            };

            document.addEventListener('mousemove', handleMove);
            document.addEventListener('mouseup', handleUp);
        });
    }

    initializeOpacitySlider() {
        const canvas = this.pickerElement.querySelector('.color-picker-opacity');
        const ctx = canvas.getContext('2d');
        const cursor = this.pickerElement.querySelector('.color-picker-opacity-cursor');

        // Draw opacity gradient
        this.drawOpacitySlider();

        // Handle opacity slider click
        canvas.addEventListener('mousedown', (e) => {
            const rect = canvas.getBoundingClientRect();
            const x = e.clientX - rect.left;

            this.updateOpacity(x / canvas.width);

            // Handle drag
            const handleMove = (e) => {
                const x = Math.max(0, Math.min(canvas.width, e.clientX - rect.left));
                this.updateOpacity(x / canvas.width);
            };

            const handleUp = () => {
                document.removeEventListener('mousemove', handleMove);
                document.removeEventListener('mouseup', handleUp);
            };

            document.addEventListener('mousemove', handleMove);
            document.addEventListener('mouseup', handleUp);
        });
    }

    drawOpacitySlider() {
        const canvas = this.pickerElement.querySelector('.color-picker-opacity');
        const ctx = canvas.getContext('2d');
        const { r, g, b } = this.currentColor.rgb;

        // Draw checkerboard background
        const squareSize = 5;
        for (let y = 0; y < canvas.height; y += squareSize) {
            for (let x = 0; x < canvas.width; x += squareSize) {
                ctx.fillStyle = ((x / squareSize) + (y / squareSize)) % 2 === 0 ? '#ccc' : '#fff';
                ctx.fillRect(x, y, squareSize, squareSize);
            }
        }

        // Draw opacity gradient
        const gradient = ctx.createLinearGradient(0, 0, canvas.width, 0);
        gradient.addColorStop(0, `rgba(${r}, ${g}, ${b}, 0)`);
        gradient.addColorStop(1, `rgba(${r}, ${g}, ${b}, 1)`);
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, canvas.width, canvas.height);
    }

    initializeEventHandlers() {
        // Close button
        this.pickerElement.querySelector('.utility-close').addEventListener('click', () => {
            this.close();
        });

        // Eyedropper button
        const eyedropperBtn = this.pickerElement.querySelector('.color-picker-eyedropper');
        if (eyedropperBtn) {
            if (window.EyeDropper) {
                eyedropperBtn.addEventListener('click', async () => {
                    try {
                        const eyeDropper = new window.EyeDropper();
                        const result = await eyeDropper.open();
                        // Result is in sRGBHex format
                        const color = this.parseColor(result.sRGBHex);
                        if (color) {
                            this.currentColor = color;
                            this.updateFromColor(color);
                        }
                    } catch (err) {
                        // User cancelled or error occurred
                        console.log('EyeDropper cancelled or failed:', err);
                    }
                });
            } else {
                // Disable if API not available
                eyedropperBtn.disabled = true;
                eyedropperBtn.style.opacity = '0.5';
                eyedropperBtn.title = 'EyeDropper not supported in this browser';
            }
        }

        // Clear button
        this.pickerElement.querySelector('.btn-clear').addEventListener('click', () => {
            this.applyColor('');
            this.close();
        });

        // Apply button
        this.pickerElement.querySelector('.btn-apply').addEventListener('click', () => {
            this.applyColor(this.formatColor(this.currentColor, this.currentFormat));
            this.addToRecent(this.formatColor(this.currentColor, 'hex'));
            this.close();
        });

        // Format selector
        this.pickerElement.querySelector('.format-selector').addEventListener('change', (e) => {
            this.currentFormat = e.target.value;
            this.updateColorInput();
        });

        // Color value input with debouncing for hex values
        const colorInput = this.pickerElement.querySelector('.color-value-input');
        let inputTimeout;
        colorInput.addEventListener('input', (e) => {
            const value = e.target.value;

            // Clear previous timeout
            clearTimeout(inputTimeout);

            // For hex values, wait for user to finish typing
            if (this.currentFormat === 'hex' && value.startsWith('#')) {
                inputTimeout = setTimeout(() => {
                    const color = this.parseColor(value);
                    if (color) {
                        this.currentColor = color;
                        this.updateFromColor(color);
                    }
                }, 1500); // Wait 1500ms after user stops typing
            } else {
                // For other formats, update immediately
                const color = this.parseColor(value);
                if (color) {
                    this.currentColor = color;
                    this.updateFromColor(color);
                }
            }
        });

        // Also update on blur for hex values
        colorInput.addEventListener('blur', (e) => {
            clearTimeout(inputTimeout);
            const color = this.parseColor(e.target.value);
            if (color) {
                this.currentColor = color;
                this.updateFromColor(color);
            }
        });

        // Swatches
        this.pickerElement.querySelectorAll('.swatch').forEach(swatch => {
            swatch.addEventListener('click', () => {
                const color = this.parseColor(swatch.dataset.color);
                if (color) {
                    this.currentColor = color;
                    this.updateFromColor(color);
                    this.emitChange();  // Trigger live preview update on swatch click
                }
            });
        });
    }

    updateFromCanvas(x, y) {
        const h = this.currentColor.hsl.h;
        const sV = x;        // HSV saturation
        const v = 1 - y;     // HSV value (top is 1)
        const { sL, l } = this.hsvToHsl(h, sV, v);

        this.currentColor = this.hslToColor(h, Math.round(sL * 100), Math.round(l * 100), this.currentColor.alpha);
        this.updateUI();
        this.emitChange();
    }

    updateHue(hue) {
        const { s, l } = this.currentColor.hsl;
        this.currentColor = this.hslToColor(hue, s, l, this.currentColor.alpha);
        this.drawCanvas();
        if (this.options.showOpacity) {
            this.drawOpacitySlider();
        }
        this.updateUI();
        this.emitChange();
    }

    updateOpacity(opacity) {
        this.currentColor.alpha = opacity;
        this.updateUI();
        this.emitChange();
    }

    updateFromColor(color) {
        this.currentColor = color;
        this.drawCanvas();
        if (this.options.showOpacity) {
            this.drawOpacitySlider();
        }
        this.updateUI();
    }

    updateUI() {
        // Guard against null pickerElement (can happen if parent closes)
        if (!this.pickerElement) return;

        // Update preview
        const newColorPreview = this.pickerElement.querySelector('.new-color');
        if (newColorPreview) {
            newColorPreview.style.backgroundColor = this.formatColor(this.currentColor, 'rgba');
        }

        // Update canvas cursor
        const { h, s, l } = this.currentColor.hsl;  // s,l in 0..100
        const { sV, v } = this.hslToHsv(h, s / 100, l / 100);
        const x = sV;                  // 0..1
        const y = 1 - v;               // 0..1

        const canvasCursor = this.pickerElement.querySelector('.color-picker-cursor');
        if (canvasCursor) {
            canvasCursor.style.left = `${x * 100}%`;
            canvasCursor.style.top = `${y * 100}%`;
        }

        // Update hue cursor
        const hueCursor = this.pickerElement.querySelector('.color-picker-hue-cursor');
        if (hueCursor) {
            hueCursor.style.left = `${(this.currentColor.hsl.h / 360) * 100}%`;
        }

        // Update opacity cursor
        if (this.options.showOpacity) {
            const opacityCursor = this.pickerElement.querySelector('.color-picker-opacity-cursor');
            const opacityValue = this.pickerElement.querySelector('.opacity-value');
            if (opacityCursor) {
                opacityCursor.style.left = `${this.currentColor.alpha * 100}%`;
            }
            if (opacityValue) {
                opacityValue.textContent = `${Math.round(this.currentColor.alpha * 100)}%`;
            }
        }

        // Update color input
        this.updateColorInput();
    }

    updateColorInput() {
        const input = this.pickerElement.querySelector('.color-value-input');
        input.value = this.formatColor(this.currentColor, this.currentFormat);
    }

    applyColor(colorString) {
        if (this.targetInput) {
            this.targetInput.value = colorString;
            this.targetInput.dispatchEvent(new Event('input', { bubbles: true }));
            this.targetInput.dispatchEvent(new Event('change', { bubbles: true }));

            // Update trigger preview
            const trigger = this.targetInput.nextElementSibling;
            if (trigger && trigger.classList.contains('color-picker-trigger')) {
                const preview = trigger.querySelector('.color-preview');
                if (preview) {
                    preview.style.backgroundColor = colorString || 'transparent';
                }
            }
        }

        // Update live preview when color is applied
        this.updateLivePreview(colorString);

        // Also trigger onChange callback when color is applied
        if (this.options.onChange) {
            this.options.onChange(colorString);
        }
    }

    emitChange() {
        const colorValue = this.formatColor(this.currentColor, this.currentFormat);

        // Update live preview immediately for instant feedback
        this.updateLivePreview(colorValue);

        // Notify change callback
        if (this.options.onChange) {
            this.options.onChange(colorValue);
        }
    }

    positionPicker() {
        if (!this.pickerElement || !this.targetInput) return;

        const inputRect = this.targetInput.getBoundingClientRect();
        const pickerRect = this.pickerElement.getBoundingClientRect();

        let top = inputRect.bottom + 8;
        let left = inputRect.left;

        // Check if popup would go below viewport
        if (top + pickerRect.height > window.innerHeight) {
            // Try to position above the input
            top = inputRect.top - pickerRect.height - 8;

            // If that would go above viewport, position at top of viewport with padding
            if (top < 0) {
                top = 10;
            }
        }

        // Check if popup would go off the right edge
        if (left + pickerRect.width > window.innerWidth) {
            left = window.innerWidth - pickerRect.width - 8;
        }

        // Ensure left doesn't go negative
        if (left < 0) {
            left = 10;
        }

        // Final check - ensure the popup is fully visible
        top = Math.max(10, Math.min(top, window.innerHeight - pickerRect.height - 10));
        left = Math.max(10, Math.min(left, window.innerWidth - pickerRect.width - 10));

        this.pickerElement.style.position = 'fixed';
        this.pickerElement.style.top = `${top}px`;
        this.pickerElement.style.left = `${left}px`;
        this.pickerElement.style.zIndex = '10000';
    }

    // Color conversion utilities
    parseColor(colorString) {
        if (!colorString) return null;

        // Remove spaces
        colorString = colorString.trim();

        // Try hex
        if (colorString.startsWith('#')) {
            return this.hexToColor(colorString);
        }

        // Try rgb/rgba
        if (colorString.startsWith('rgb')) {
            return this.rgbStringToColor(colorString);
        }

        // Try hsl/hsla
        if (colorString.startsWith('hsl')) {
            return this.hslStringToColor(colorString);
        }

        // Try as hex without #
        if (/^[0-9a-fA-F]{3,8}$/.test(colorString)) {
            return this.hexToColor('#' + colorString);
        }

        return null;
    }

    hexToColor(hex) {
        const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})?$/i.exec(hex);
        if (!result) {
            // Try short format
            const shortResult = /^#?([a-f\d])([a-f\d])([a-f\d])$/i.exec(hex);
            if (!shortResult) return null;

            const r = parseInt(shortResult[1] + shortResult[1], 16);
            const g = parseInt(shortResult[2] + shortResult[2], 16);
            const b = parseInt(shortResult[3] + shortResult[3], 16);
            return this.rgbToColor(r, g, b, 1);
        }

        const r = parseInt(result[1], 16);
        const g = parseInt(result[2], 16);
        const b = parseInt(result[3], 16);
        const a = result[4] ? parseInt(result[4], 16) / 255 : 1;

        return this.rgbToColor(r, g, b, a);
    }

    rgbStringToColor(rgbString) {
        const match = rgbString.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?\)/);
        if (!match) return null;

        return this.rgbToColor(
            parseInt(match[1]),
            parseInt(match[2]),
            parseInt(match[3]),
            match[4] ? parseFloat(match[4]) : 1
        );
    }

    hslStringToColor(hslString) {
        const match = hslString.match(/hsla?\((\d+),\s*(\d+)%,\s*(\d+)%(?:,\s*([\d.]+))?\)/);
        if (!match) return null;

        return this.hslToColor(
            parseInt(match[1]),
            parseInt(match[2]),
            parseInt(match[3]),
            match[4] ? parseFloat(match[4]) : 1
        );
    }

    rgbToColor(r, g, b, a = 1) {
        const hsl = this.rgbToHsl(r, g, b);
        return {
            rgb: { r, g, b },
            hsl: hsl,
            alpha: a
        };
    }

    hslToColor(h, s, l, a = 1) {
        const rgb = this.hslToRgb(h, s, l);
        return {
            rgb: rgb,
            hsl: { h, s, l },
            alpha: a
        };
    }

    rgbToHsl(r, g, b) {
        r /= 255;
        g /= 255;
        b /= 255;

        const max = Math.max(r, g, b);
        const min = Math.min(r, g, b);
        let h, s, l = (max + min) / 2;

        if (max === min) {
            h = s = 0;
        } else {
            const d = max - min;
            s = l > 0.5 ? d / (2 - max - min) : d / (max + min);

            switch (max) {
                case r: h = ((g - b) / d + (g < b ? 6 : 0)) / 6; break;
                case g: h = ((b - r) / d + 2) / 6; break;
                case b: h = ((r - g) / d + 4) / 6; break;
            }
        }

        return {
            h: Math.round(h * 360),
            s: Math.round(s * 100),
            l: Math.round(l * 100)
        };
    }

    hslToRgb(h, s, l) {
        h /= 360;
        s /= 100;
        l /= 100;

        let r, g, b;

        if (s === 0) {
            r = g = b = l;
        } else {
            const hue2rgb = (p, q, t) => {
                if (t < 0) t += 1;
                if (t > 1) t -= 1;
                if (t < 1/6) return p + (q - p) * 6 * t;
                if (t < 1/2) return q;
                if (t < 2/3) return p + (q - p) * (2/3 - t) * 6;
                return p;
            };

            const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
            const p = 2 * l - q;

            r = hue2rgb(p, q, h + 1/3);
            g = hue2rgb(p, q, h);
            b = hue2rgb(p, q, h - 1/3);
        }

        return {
            r: Math.round(r * 255),
            g: Math.round(g * 255),
            b: Math.round(b * 255)
        };
    }

    formatColor(color, format) {
        if (!color) return '';

        const { r, g, b } = color.rgb;
        const { h, s, l } = color.hsl;
        const a = color.alpha;

        switch (format) {
            case 'hex':
                if (a < 1) {
                    const alpha = Math.round(a * 255).toString(16).padStart(2, '0');
                    return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}${alpha}`;
                }
                return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;

            case 'rgb':
                return `rgb(${r}, ${g}, ${b})`;

            case 'rgba':
                return `rgba(${r}, ${g}, ${b}, ${a})`;

            case 'hsl':
                return `hsl(${h}, ${s}%, ${l}%)`;

            case 'hsla':
                return `hsla(${h}, ${s}%, ${l}%, ${a})`;

            default:
                return this.formatColor(color, 'hex');
        }
    }

    // Recent colors management
    loadRecentColors() {
        try {
            const stored = localStorage.getItem('pb_recent_colors');
            return stored ? JSON.parse(stored) : [];
        } catch {
            return [];
        }
    }

    saveRecentColors() {
        try {
            localStorage.setItem('pb_recent_colors', JSON.stringify(this.recentColors));
        } catch {
            // Ignore storage errors
        }
    }

    addToRecent(color) {
        if (!color) return;

        // Remove if already exists
        this.recentColors = this.recentColors.filter(c => c !== color);

        // Add to beginning
        this.recentColors.unshift(color);

        // Limit size
        if (this.recentColors.length > this.options.maxRecent) {
            this.recentColors.pop();
        }

        this.saveRecentColors();
    }

    // Helper to check if a color string has transparency
    colorHasTransparency(colorString) {
        if (!colorString) return false;

        // Check for rgba/hsla formats
        if (colorString.includes('rgba') || colorString.includes('hsla')) {
            const match = colorString.match(/[\d.]+(?=\))/);
            if (match) {
                const alpha = parseFloat(match[0]);
                return alpha < 1;
            }
        }

        // Check for 8-digit hex (with alpha)
        if (colorString.match(/^#[0-9a-fA-F]{8}$/)) {
            return true;
        }

        return false;
    }

    makeDraggable(popup, handle) {
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
            const rect = popup.getBoundingClientRect();
            initialX = rect.left;
            initialY = rect.top;

            // Add cursor style
            handle.style.cursor = 'grabbing';

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

            // Keep popup within viewport
            const popupRect = popup.getBoundingClientRect();
            newLeft = Math.max(0, Math.min(newLeft, window.innerWidth - popupRect.width));
            newTop = Math.max(0, Math.min(newTop, window.innerHeight - popupRect.height));

            // Apply new position
            popup.style.left = `${newLeft}px`;
            popup.style.top = `${newTop}px`;
        };

        const stopDrag = () => {
            if (!isDragging) return;

            isDragging = false;
            handle.style.cursor = 'grab';
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

    // HSV<->HSL conversion helpers
    hsvToHsl(h, sV, v) { // sV,v in [0..1]; returns {h, sL, l} in [0..1]
        const l = v * (1 - sV / 2);
        const sL = (l === 0 || l === 1) ? 0 : (v - l) / Math.min(l, 1 - l);
        return { h, sL, l };
    }

    hslToHsv(h, sL, l) { // sL,l in [0..1]; returns {h, sV, v} in [0..1]
        const v = l + sL * Math.min(l, 1 - l);
        const sV = v === 0 ? 0 : 2 * (1 - l / v);
        return { h, sV, v };
    }

    // Translation helper
    t(key) {
        // Check if global translations are available
        const globalTranslations = window.ColorPickerTranslations || {};

        const translations = {
            selectColor: 'Select Color',
            presets: 'Presets',
            recent: 'Recent',
            clear: 'Clear',
            apply: 'Apply',
            pickFromScreen: 'Pick from Screen',
            current: 'Current',
            new: 'New',
            ...globalTranslations,
            ...this.options.translations
        };

        return translations[key] || key;
    }
}

// Make globally available
window.ColorPickerUtility = ColorPickerUtility;