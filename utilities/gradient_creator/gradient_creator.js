/* Copyright (c) 2025-2026 Spwig. Licensed under AGPL-3.0. */

/**
 * Gradient Creator Utility for Page Builder
 * Following the design principles from color picker and typography editor
 */

class GradientCreator {
    constructor(options = {}) {
        this.options = {
            onChange: options.onChange || (() => {}),
            onApply: options.onApply || (() => {}),
            translations: options.translations || {},
            createTrigger: options.createTrigger !== false  // Default to true
        };

        this.isOpen = false;
        this.popup = null;
        this.targetElement = null;
        this.triggerButton = null;
        this.elementId = null;
        this.initialValue = '';

        // Gradient data
        this.gradient = {
            type: 'linear',
            angle: 90,
            position: 'center center',
            shape: 'ellipse',
            stops: [
                { color: '#3b82f6', position: 0, opacity: 1 },
                { color: '#8b5cf6', position: 100, opacity: 1 }
            ]
        };

        this.selectedStopIndex = 0;
        this.isDraggingStop = false;
        this.draggedStopIndex = null;

        // Color picker instances for each stop
        this.colorPickers = new Map();
    }

    attach(element, value = '') {
        this.targetElement = element;
        this.initialValue = value || element.value || '';

        // Get element ID for live preview
        const form = element.closest('.element-properties-form');
        this.elementId = form ? form.dataset.elementId : null;

        // Parse initial value
        if (this.initialValue) {
            this.parseGradient(this.initialValue);
        }

        // Create trigger button only if option is enabled
        if (this.options.createTrigger) {
            this.createTrigger();
        }
    }

    createTrigger() {
        this.triggerButton = document.createElement('button');
        this.triggerButton.className = 'util-btn gradient-creator-trigger';
        this.triggerButton.type = 'button';
        this.triggerButton.innerHTML = `
            <div class="gradient-preview" style="background: ${this.generateCSS()}"></div>
            <i class="fas fa-palette"></i>
        `;

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

        // Store initial value for reset
        this.initialValue = this.targetElement.value || '';

        // Create popup
        this.createPopup();
        document.body.appendChild(this.popup);

        // Position popup
        this.position();

        // Initialize UI
        this.updateUI();

        // Setup event listeners
        this.setupEventListeners();

        // Make draggable
        this.makeDraggable(this.popup, this.popup.querySelector('.utility-header'));
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
        this.popup = document.createElement('div');
        this.popup.className = 'utility-popup gradient-creator';
        this.popup.innerHTML = `
            <div class="utility-header">
                <h3 class="utility-title">Gradient Editor</h3>
                <button type="button" class="utility-close">
                    <i class="fas fa-times"></i>
                </button>
            </div>

            <div class="utility-body">
                <!-- Preview Section -->
                <div class="gradient-preview-section">
                    <div class="preview-box">
                        <span class="preview-label">Current</span>
                        <div class="preview-gradient preview-current" style="background: ${this.initialValue || 'transparent'}"></div>
                    </div>
                    <i class="preview-arrow fas fa-arrow-right"></i>
                    <div class="preview-box">
                        <span class="preview-label">New</span>
                        <div class="preview-gradient preview-new"></div>
                    </div>
                </div>

                <!-- Gradient Bar -->
                <div class="gradient-bar-section">
                    <div class="gradient-bar">
                        <div class="gradient-track"></div>
                    </div>
                </div>

                <!-- Type Tabs -->
                <div class="admin-tabs">
                    <button class="admin-tab-btn active" data-type="linear">
                        <i class="fas fa-arrows-alt-h"></i>
                        Linear
                    </button>
                    <button class="admin-tab-btn" data-type="radial">
                        <i class="fas fa-circle"></i>
                        Radial
                    </button>
                    <button class="admin-tab-btn" data-type="conic">
                        <i class="fas fa-sync"></i>
                        Conic
                    </button>
                </div>

                <!-- Tab Content -->
                <div class="gradient-tab-content">
                    <!-- Linear Options -->
                    <div class="tab-pane active" data-pane="linear">
                        <div class="control-group">
                            <label>Direction</label>
                            <div class="angle-controls">
                                <input type="range" class="angle-slider" min="0" max="360" value="90">
                                <input type="number" class="angle-input" min="0" max="360" value="90">
                                <span>°</span>
                            </div>
                            <div class="angle-presets">
                                <button class="angle-btn" data-angle="0" title="To Top">
                                    <i class="fas fa-arrow-up"></i>
                                </button>
                                <button class="angle-btn" data-angle="45" title="To Top Right">
                                    <i class="fas fa-arrow-up" style="transform: rotate(45deg)"></i>
                                </button>
                                <button class="angle-btn active" data-angle="90" title="To Right">
                                    <i class="fas fa-arrow-right"></i>
                                </button>
                                <button class="angle-btn" data-angle="135" title="To Bottom Right">
                                    <i class="fas fa-arrow-down" style="transform: rotate(-45deg)"></i>
                                </button>
                                <button class="angle-btn" data-angle="180" title="To Bottom">
                                    <i class="fas fa-arrow-down"></i>
                                </button>
                                <button class="angle-btn" data-angle="225" title="To Bottom Left">
                                    <i class="fas fa-arrow-down" style="transform: rotate(45deg)"></i>
                                </button>
                                <button class="angle-btn" data-angle="270" title="To Left">
                                    <i class="fas fa-arrow-left"></i>
                                </button>
                                <button class="angle-btn" data-angle="315" title="To Top Left">
                                    <i class="fas fa-arrow-up" style="transform: rotate(-45deg)"></i>
                                </button>
                            </div>
                        </div>
                    </div>

                    <!-- Radial Options -->
                    <div class="tab-pane" data-pane="radial">
                        <div class="control-group">
                            <label>Shape</label>
                            <div class="button-group">
                                <button class="shape-btn active" data-shape="ellipse">Ellipse</button>
                                <button class="shape-btn" data-shape="circle">Circle</button>
                            </div>
                        </div>
                        <div class="control-group">
                            <label>Position</label>
                            <select class="position-select">
                                <option value="center center">Center</option>
                                <option value="top left">Top Left</option>
                                <option value="top center">Top Center</option>
                                <option value="top right">Top Right</option>
                                <option value="center left">Center Left</option>
                                <option value="center right">Center Right</option>
                                <option value="bottom left">Bottom Left</option>
                                <option value="bottom center">Bottom Center</option>
                                <option value="bottom right">Bottom Right</option>
                            </select>
                        </div>
                    </div>

                    <!-- Conic Options -->
                    <div class="tab-pane" data-pane="conic">
                        <div class="control-group">
                            <label>Starting Angle</label>
                            <div class="angle-controls">
                                <input type="range" class="conic-angle-slider" min="0" max="360" value="0">
                                <input type="number" class="conic-angle-input" min="0" max="360" value="0">
                                <span>°</span>
                            </div>
                        </div>
                        <div class="control-group">
                            <label>Center Position</label>
                            <select class="conic-position-select">
                                <option value="center center">Center</option>
                                <option value="top left">Top Left</option>
                                <option value="top center">Top Center</option>
                                <option value="top right">Top Right</option>
                                <option value="center left">Center Left</option>
                                <option value="center right">Center Right</option>
                                <option value="bottom left">Bottom Left</option>
                                <option value="bottom center">Bottom Center</option>
                                <option value="bottom right">Bottom Right</option>
                            </select>
                        </div>
                    </div>
                </div>

                <!-- Color Stops -->
                <div class="color-stops-section">
                    <div class="stops-header">
                        <h4>Color Stops</h4>
                        <button class="add-stop-btn" title="Add Color Stop">
                            <i class="fas fa-plus"></i>
                        </button>
                    </div>
                    <div class="color-stops-list"></div>
                </div>

                <!-- Presets -->
                <div class="gradient-presets-section">
                    <h4>Presets</h4>
                    <div class="presets-grid">
                        <button class="preset-btn" data-preset="ocean"></button>
                        <button class="preset-btn" data-preset="sunset"></button>
                        <button class="preset-btn" data-preset="forest"></button>
                        <button class="preset-btn" data-preset="berry"></button>
                        <button class="preset-btn" data-preset="flame"></button>
                        <button class="preset-btn" data-preset="night"></button>
                    </div>
                </div>
            </div>

            <div class="utility-footer">
                <button class="btn btn-clear">Clear</button>
                <button class="btn btn-apply">Apply</button>
            </div>
        `;
    }

    setupEventListeners() {
        // Close button
        this.popup.querySelector('.utility-close').addEventListener('click', () => this.close());

        // Tab switching
        this.popup.querySelectorAll('.admin-tab-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.gradient.type = btn.dataset.type;
                this.updateTabs();
                this.updatePreview();
            });
        });

        // Linear controls
        const angleSlider = this.popup.querySelector('.angle-slider');
        const angleInput = this.popup.querySelector('.angle-input');

        angleSlider?.addEventListener('input', (e) => {
            this.gradient.angle = parseInt(e.target.value);
            angleInput.value = e.target.value;
            this.updateAngleButtons();
            this.updatePreview();
        });

        angleInput?.addEventListener('input', (e) => {
            this.gradient.angle = parseInt(e.target.value) || 0;
            angleSlider.value = e.target.value;
            this.updateAngleButtons();
            this.updatePreview();
        });

        // Angle preset buttons
        this.popup.querySelectorAll('.angle-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const angle = parseInt(btn.dataset.angle);
                this.gradient.angle = angle;
                angleSlider.value = angle;
                angleInput.value = angle;
                this.updateAngleButtons();
                this.updatePreview();
            });
        });

        // Radial controls
        this.popup.querySelectorAll('.shape-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.gradient.shape = btn.dataset.shape;
                this.popup.querySelectorAll('.shape-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.updatePreview();
            });
        });

        const positionSelect = this.popup.querySelector('.position-select');
        positionSelect?.addEventListener('change', (e) => {
            this.gradient.position = e.target.value;
            this.updatePreview();
        });

        // Conic controls
        const conicAngleSlider = this.popup.querySelector('.conic-angle-slider');
        const conicAngleInput = this.popup.querySelector('.conic-angle-input');

        conicAngleSlider?.addEventListener('input', (e) => {
            this.gradient.angle = parseInt(e.target.value);
            conicAngleInput.value = e.target.value;
            this.updatePreview();
        });

        conicAngleInput?.addEventListener('input', (e) => {
            this.gradient.angle = parseInt(e.target.value) || 0;
            conicAngleSlider.value = e.target.value;
            this.updatePreview();
        });

        const conicPositionSelect = this.popup.querySelector('.conic-position-select');
        conicPositionSelect?.addEventListener('change', (e) => {
            this.gradient.position = e.target.value;
            this.updatePreview();
        });

        // Add stop button
        this.popup.querySelector('.add-stop-btn').addEventListener('click', () => {
            this.addColorStop();
        });

        // Gradient bar for adding stops
        const gradientBar = this.popup.querySelector('.gradient-bar');
        gradientBar.addEventListener('click', (e) => {
            if (e.target === gradientBar || e.target.classList.contains('gradient-track')) {
                const rect = gradientBar.getBoundingClientRect();
                const position = Math.round(((e.clientX - rect.left) / rect.width) * 100);
                this.addColorStop(position);
            }
        });

        // Preset buttons
        this.popup.querySelectorAll('.preset-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.applyPreset(btn.dataset.preset);
            });
        });

        // Footer buttons
        this.popup.querySelector('.btn-clear').addEventListener('click', () => {
            this.gradient = {
                type: 'linear',
                angle: 90,
                position: 'center center',
                shape: 'ellipse',
                stops: [
                    { color: '#ffffff', position: 0, opacity: 1 },
                    { color: '#000000', position: 100, opacity: 1 }
                ]
            };
            this.selectedStopIndex = 0;
            this.updateUI();
        });

        this.popup.querySelector('.btn-apply').addEventListener('click', () => {
            this.applyValue();
        });

        // Click outside to close
        this.handleOutsideClick = (e) => {
            // Don't close if we don't have a popup
            if (!this.popup) return;

            // Don't close if clicking inside the popup
            if (this.popup.contains(e.target)) return;

            // Don't close if clicking on the trigger button (if it exists)
            if (this.triggerButton && this.triggerButton.contains(e.target)) return;

            // Don't close if clicking on the target element (the element we're attached to)
            if (this.targetElement && this.targetElement.contains(e.target)) return;

            // Don't close if clicking on a color picker (check both old and new class names)
            const clickedUtility = e.target.closest('.utility-popup');
            const isMediaLibrary = e.target.closest('.media-library-modal');

            if (clickedUtility && clickedUtility !== this.popup) {
                // Clicking on any other utility popup (like color picker), don't close
                return;
            }

            // Don't close if clicking on media library
            if (isMediaLibrary) {
                return;
            }

            this.close();
        };

        setTimeout(() => {
            document.addEventListener('mousedown', this.handleOutsideClick);
        }, 100);
    }

    updateUI() {
        this.updateTabs();
        this.updateStops();
        this.updateGradientBar();
        this.updatePreview();
        this.updatePresets();
        this.updateAngleButtons();
    }

    updateTabs() {
        // Update tab buttons
        this.popup.querySelectorAll('.admin-tab-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.type === this.gradient.type);
        });

        // Update tab panes
        this.popup.querySelectorAll('.tab-pane').forEach(pane => {
            pane.classList.toggle('active', pane.dataset.pane === this.gradient.type);
        });
    }

    updateStops() {
        const container = this.popup.querySelector('.color-stops-list');
        container.innerHTML = '';

        this.gradient.stops.forEach((stop, index) => {
            const stopEl = document.createElement('div');
            stopEl.className = `color-stop-item ${index === this.selectedStopIndex ? 'selected' : ''}`;
            stopEl.innerHTML = `
                <div class="stop-color-preview" style="background: ${this.getStopColor(stop)}" title="Click to change color"></div>
                <div class="stop-position">
                    <input type="number" class="stop-position-input" value="${stop.position}" min="0" max="100">
                    <span>%</span>
                </div>
                <div class="stop-opacity">
                    <input type="range" class="stop-opacity-slider" value="${stop.opacity * 100}" min="0" max="100">
                    <span class="stop-opacity-value">${Math.round(stop.opacity * 100)}%</span>
                </div>
                ${this.gradient.stops.length > 2 ? `
                    <button class="stop-remove-btn" title="Remove">
                        <i class="fas fa-trash"></i>
                    </button>
                ` : ''}
            `;

            // Select on click
            stopEl.addEventListener('click', (e) => {
                // Don't update stops if clicking on color preview or remove button
                if (!e.target.closest('.stop-remove-btn') && !e.target.closest('.stop-color-preview')) {
                    this.selectedStopIndex = index;
                    this.updateStops();
                }
            });

            // Color preview click - open color picker
            const colorPreview = stopEl.querySelector('.stop-color-preview');
            colorPreview.addEventListener('click', (e) => {
                e.stopPropagation();
                this.openColorPicker(index, colorPreview);
            });

            // Position input
            const positionInput = stopEl.querySelector('.stop-position-input');
            positionInput.addEventListener('input', (e) => {
                stop.position = Math.max(0, Math.min(100, parseInt(e.target.value) || 0));
                this.sortStops();
                this.updateGradientBar();
                this.updatePreview();
            });

            // Opacity slider
            const opacitySlider = stopEl.querySelector('.stop-opacity-slider');
            const opacityValue = stopEl.querySelector('.stop-opacity-value');
            opacitySlider?.addEventListener('input', (e) => {
                stop.opacity = parseInt(e.target.value) / 100;
                opacityValue.textContent = `${e.target.value}%`;
                colorPreview.style.background = this.getStopColor(stop);
                this.updateGradientBar();
                this.updatePreview();
            });

            // Remove button
            const removeBtn = stopEl.querySelector('.stop-remove-btn');
            removeBtn?.addEventListener('click', (e) => {
                e.stopPropagation();
                this.removeColorStop(index);
            });

            container.appendChild(stopEl);
        });
    }

    updateGradientBar() {
        const track = this.popup.querySelector('.gradient-track');
        const bar = this.popup.querySelector('.gradient-bar');

        // Update gradient background
        track.style.background = this.generateCSS();

        // Remove existing markers
        bar.querySelectorAll('.stop-marker').forEach(m => m.remove());

        // Add stop markers
        this.gradient.stops.forEach((stop, index) => {
            const marker = document.createElement('div');
            marker.className = `stop-marker ${index === this.selectedStopIndex ? 'selected' : ''}`;
            marker.style.left = `${stop.position}%`;
            marker.style.background = stop.color;
            marker.dataset.index = index;

            // Make draggable
            marker.addEventListener('mousedown', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.startDraggingStop(index, e);
            });

            // Select on click
            marker.addEventListener('click', (e) => {
                e.stopPropagation();
                this.selectedStopIndex = index;
                this.updateStops();
                this.updateGradientBar();
            });

            bar.appendChild(marker);
        });
    }

    startDraggingStop(index, e) {
        this.isDraggingStop = true;
        this.draggedStopIndex = index;
        this.selectedStopIndex = index;

        const bar = this.popup.querySelector('.gradient-bar');
        const rect = bar.getBoundingClientRect();

        const handleMouseMove = (e) => {
            if (!this.isDraggingStop) return;

            let position = ((e.clientX - rect.left) / rect.width) * 100;
            position = Math.max(0, Math.min(100, position));

            this.gradient.stops[this.draggedStopIndex].position = Math.round(position);
            this.sortStops();
            this.updateStops();
            this.updateGradientBar();
            this.updatePreview();
        };

        const handleMouseUp = () => {
            this.isDraggingStop = false;
            this.draggedStopIndex = null;
            document.removeEventListener('mousemove', handleMouseMove);
            document.removeEventListener('mouseup', handleMouseUp);
        };

        document.addEventListener('mousemove', handleMouseMove);
        document.addEventListener('mouseup', handleMouseUp);
    }

    updatePreview() {
        const css = this.generateCSS();

        // Update new preview
        const newPreview = this.popup.querySelector('.preview-new');
        newPreview.style.background = css;

        // Update trigger preview (only if trigger button exists)
        if (this.triggerButton) {
            const triggerPreview = this.triggerButton.querySelector('.gradient-preview');
            if (triggerPreview) {
                triggerPreview.style.background = css;
            }
        }

        // Live update in page builder - Use LivePreviewManager for instant updates
        if (this.elementId) {
            if (window.livePreview) {
                window.livePreview.updateElement(this.elementId, {
                    background: css
                }, { sync: false }); // Visual only, don't sync to server yet
            } else if (window.updateElementPreview) {
                // Fallback to old method
                window.updateElementPreview(this.elementId, { background: css });
            }
        }

        // Notify change
        if (this.options.onChange) {
            this.options.onChange(css);
        }
    }

    updatePresets() {
        const presets = {
            ocean: 'linear-gradient(120deg, #89f7fe 0%, #66a6ff 100%)',
            sunset: 'linear-gradient(45deg, #ff9a56 0%, #ff6a88 50%, #ff5e7e 100%)',
            forest: 'linear-gradient(135deg, #667eea 0%, #52e5a7 100%)',
            berry: 'linear-gradient(90deg, #fc5c7d 0%, #6a82fb 100%)',
            flame: 'linear-gradient(45deg, #f93b1d 0%, #ffd319 100%)',
            night: 'linear-gradient(180deg, #2c3e50 0%, #3498db 100%)'
        };

        this.popup.querySelectorAll('.preset-btn').forEach(btn => {
            const preset = btn.dataset.preset;
            if (presets[preset]) {
                btn.style.background = presets[preset];
            }
        });
    }

    updateAngleButtons() {
        const currentAngle = this.gradient.angle;
        this.popup.querySelectorAll('.angle-btn').forEach(btn => {
            const btnAngle = parseInt(btn.dataset.angle);
            btn.classList.toggle('active', btnAngle === currentAngle);
        });
    }

    addColorStop(position = 50) {
        if (this.gradient.stops.length >= 10) {
            AdminModal.alert({message: 'Maximum 10 color stops allowed', type: 'warning'});
            return;
        }

        // Interpolate color at position
        const color = this.interpolateColor(position);

        this.gradient.stops.push({
            color: color,
            position: position,
            opacity: 1
        });

        this.sortStops();

        // Select the new stop
        this.selectedStopIndex = this.gradient.stops.findIndex(s => s.position === position);

        this.updateStops();
        this.updateGradientBar();
        this.updatePreview();
    }

    removeColorStop(index) {
        if (this.gradient.stops.length <= 2) return;

        this.gradient.stops.splice(index, 1);

        if (this.selectedStopIndex >= this.gradient.stops.length) {
            this.selectedStopIndex = this.gradient.stops.length - 1;
        }

        this.updateStops();
        this.updateGradientBar();
        this.updatePreview();
    }

    sortStops() {
        this.gradient.stops.sort((a, b) => a.position - b.position);
    }

    interpolateColor(position) {
        const stops = [...this.gradient.stops].sort((a, b) => a.position - b.position);

        // Find surrounding stops
        let before = stops[0];
        let after = stops[stops.length - 1];

        for (let i = 0; i < stops.length - 1; i++) {
            if (stops[i].position <= position && stops[i + 1].position >= position) {
                before = stops[i];
                after = stops[i + 1];
                break;
            }
        }

        if (before === after) {
            return before.color;
        }

        // Linear interpolation
        const ratio = (position - before.position) / (after.position - before.position);
        return this.mixColors(before.color, after.color, ratio);
    }

    mixColors(color1, color2, ratio) {
        // Parse colors
        const c1 = this.parseColor(color1);
        const c2 = this.parseColor(color2);

        // Interpolate
        const r = Math.round(c1.r + (c2.r - c1.r) * ratio);
        const g = Math.round(c1.g + (c2.g - c1.g) * ratio);
        const b = Math.round(c1.b + (c2.b - c1.b) * ratio);

        return `#${[r, g, b].map(v => v.toString(16).padStart(2, '0')).join('')}`;
    }

    parseColor(color) {
        // Simple hex parser
        if (color.startsWith('#')) {
            const hex = color.slice(1);
            return {
                r: parseInt(hex.slice(0, 2), 16),
                g: parseInt(hex.slice(2, 4), 16),
                b: parseInt(hex.slice(4, 6), 16)
            };
        }
        // Default
        return { r: 0, g: 0, b: 0 };
    }

    openColorPicker(index, triggerElement) {
        // Create color picker if it doesn't exist
        if (!this.colorPickers.has(index)) {
            if (window.ColorPickerUtility) {
                const picker = new window.ColorPickerUtility({
                    onChange: (color) => {
                        const stop = this.gradient.stops[index];
                        stop.color = color;

                        // Parse opacity from color if rgba
                        if (color.startsWith('rgba')) {
                            const match = color.match(/rgba\(.*?,\s*([\d.]+)\)/);
                            if (match) {
                                stop.opacity = parseFloat(match[1]);
                            }
                        }

                        this.updateStops();
                        this.updateGradientBar();
                        this.updatePreview();
                    }
                });
                this.colorPickers.set(index, picker);
            }
        }

        const picker = this.colorPickers.get(index);
        if (picker) {
            const stop = this.gradient.stops[index];
            picker.open(triggerElement, stop.color);
        }
    }

    getStopColor(stop) {
        if (stop.opacity < 1) {
            // Convert hex to rgba
            const color = this.parseColor(stop.color);
            return `rgba(${color.r}, ${color.g}, ${color.b}, ${stop.opacity})`;
        }
        return stop.color;
    }

    generateCSS() {
        const stops = this.gradient.stops
            .map(stop => `${this.getStopColor(stop)} ${stop.position}%`)
            .join(', ');

        switch (this.gradient.type) {
            case 'linear':
                return `linear-gradient(${this.gradient.angle}deg, ${stops})`;
            case 'radial':
                return `radial-gradient(${this.gradient.shape} at ${this.gradient.position}, ${stops})`;
            case 'conic':
                return `conic-gradient(from ${this.gradient.angle}deg at ${this.gradient.position}, ${stops})`;
            default:
                return `linear-gradient(90deg, ${stops})`;
        }
    }

    parseGradient(css) {
        // Basic gradient parser
        if (css.includes('linear-gradient')) {
            this.gradient.type = 'linear';
            const angleMatch = css.match(/(\d+)deg/);
            if (angleMatch) {
                this.gradient.angle = parseInt(angleMatch[1]);
            }
        } else if (css.includes('radial-gradient')) {
            this.gradient.type = 'radial';
            // Parse shape and position
            const shapeMatch = css.match(/(circle|ellipse)/);
            if (shapeMatch) {
                this.gradient.shape = shapeMatch[1];
            }
        } else if (css.includes('conic-gradient')) {
            this.gradient.type = 'conic';
        }

        // Parse color stops (simplified)
        const stopsRegex = /(#[0-9a-f]{3,6}|rgba?\([^)]+\))\s+(\d+)%/gi;
        const stops = [];
        let match;

        while ((match = stopsRegex.exec(css)) !== null) {
            stops.push({
                color: match[1],
                position: parseInt(match[2]),
                opacity: 1
            });
        }

        if (stops.length >= 2) {
            this.gradient.stops = stops;
        }
    }

    applyPreset(preset) {
        const presets = {
            ocean: {
                type: 'linear',
                angle: 120,
                stops: [
                    { color: '#89f7fe', position: 0, opacity: 1 },
                    { color: '#66a6ff', position: 100, opacity: 1 }
                ]
            },
            sunset: {
                type: 'linear',
                angle: 45,
                stops: [
                    { color: '#ff9a56', position: 0, opacity: 1 },
                    { color: '#ff6a88', position: 50, opacity: 1 },
                    { color: '#ff5e7e', position: 100, opacity: 1 }
                ]
            },
            forest: {
                type: 'linear',
                angle: 135,
                stops: [
                    { color: '#667eea', position: 0, opacity: 1 },
                    { color: '#52e5a7', position: 100, opacity: 1 }
                ]
            },
            berry: {
                type: 'linear',
                angle: 90,
                stops: [
                    { color: '#fc5c7d', position: 0, opacity: 1 },
                    { color: '#6a82fb', position: 100, opacity: 1 }
                ]
            },
            flame: {
                type: 'linear',
                angle: 45,
                stops: [
                    { color: '#f93b1d', position: 0, opacity: 1 },
                    { color: '#ffd319', position: 100, opacity: 1 }
                ]
            },
            night: {
                type: 'linear',
                angle: 180,
                stops: [
                    { color: '#2c3e50', position: 0, opacity: 1 },
                    { color: '#3498db', position: 100, opacity: 1 }
                ]
            }
        };

        if (presets[preset]) {
            Object.assign(this.gradient, presets[preset]);
            this.selectedStopIndex = 0;
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
        if (this.options.onApply) {
            this.options.onApply(css);
        }

        // Close
        this.close();
    }

    position() {
        if (!this.popup) return;

        // Use triggerButton if it exists, otherwise use targetElement
        const referenceElement = this.triggerButton || this.targetElement;
        if (!referenceElement) return;

        const triggerRect = referenceElement.getBoundingClientRect();
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
            if (e.target.closest('.utility-close')) return;

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
window.GradientCreator = GradientCreator;
window.GradientCreatorUtility = GradientCreator; // Alias for property renderer