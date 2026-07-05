/* Copyright (c) 2025-2026 Spwig. Licensed under AGPL-3.0. */

/**
 * Focal Point Editor
 * Version 1.0.0
 *
 * Visual focal point selector for responsive image cropping with:
 * - Interactive canvas with draggable crosshair marker
 * - 9-point grid quick presets
 * - Aspect ratio previews (1:1, 16:9, 4:3, 3:2)
 * - Rule of thirds overlay
 * - Zoom controls
 * - Keyboard navigation (arrow keys)
 * - Breakpoint-specific focal points (desktop/tablet/mobile)
 * - Undo/history support
 */

class FocalPointEditor {
    constructor(options = {}) {
        this.options = {
            showGrid: options.showGrid ?? true,
            showAspectRatios: options.showAspectRatios ?? true,
            enableBreakpoints: options.enableBreakpoints ?? true,
            enableKeyboard: options.enableKeyboard ?? true,
            defaultZoom: options.defaultZoom ?? 100,
            maxHistory: options.maxHistory ?? 20,
            ...options
        };

        this.popup = null;
        this.inputElement = null;
        this.imageUrl = options.imageUrl || null;
        this.currentBreakpoint = 'default';
        this.focalPoints = {
            default: { x: 0.5, y: 0.5 },
            tablet: null,
            mobile: null
        };
        this.linked = true; // All breakpoints use same focal point
        this.showGrid = true;
        this.zoom = 100;
        this.history = [];
        this.historyIndex = -1;
        this.isDragging = false;
        this.imageNaturalWidth = 0;
        this.imageNaturalHeight = 0;

        // Store callbacks from property renderer
        this.onChange = options.onChange || (() => {});
        this.onApply = options.onApply || (() => {});

        // Bind methods
        this.open = this.open.bind(this);
        this.close = this.close.bind(this);
        this.handleCanvasClick = this.handleCanvasClick.bind(this);
        this.handleCanvasDrag = this.handleCanvasDrag.bind(this);
        this.handleKeydown = this.handleKeydown.bind(this);

        // Auto-attach if wrapper provided via options
        if (options.wrapper) {
            this.attachToWrapper(options.wrapper);
        }
    }

    /**
     * Attach to a wrapper element created by property renderer
     * @param {HTMLElement} wrapper - The .property-input-with-utility wrapper
     */
    attachToWrapper(wrapper) {
        // Prevent duplicate initialization
        if (wrapper.dataset.focalPointInitialized === 'true') {
            return;
        }
        wrapper.dataset.focalPointInitialized = 'true';

        this.inputElement = wrapper.querySelector('input');
        const triggerButton = wrapper.querySelector('.focal-point-btn, .utility-trigger-btn');

        if (this.inputElement) {
            // Parse existing value
            const existingValue = this.inputElement.value;
            if (existingValue) {
                try {
                    const parsed = JSON.parse(existingValue);
                    if (parsed.default) {
                        this.focalPoints = { ...this.focalPoints, ...parsed };
                        this.linked = parsed.linked ?? true;
                    } else if (parsed.x !== undefined && parsed.y !== undefined) {
                        this.focalPoints.default = parsed;
                    }
                } catch (e) {
                    console.warn('[FocalPointEditor] Could not parse existing value:', e);
                }
            }
        }

        if (triggerButton && !triggerButton.dataset.hasClickHandler) {
            triggerButton.dataset.hasClickHandler = 'true';
            triggerButton.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.open();
            });
        }
    }

    /**
     * Attach the editor to an input element
     * @param {HTMLInputElement} inputElement - Hidden input storing JSON value
     * @param {string} valueOrUrl - Current value (for most utilities) or image URL (if not already set)
     */
    attach(inputElement, valueOrUrl) {
        this.inputElement = inputElement;
        // Only set imageUrl if not already set via constructor options
        // This allows property renderer to pass the image URL via options.imageUrl
        // while the second parameter here contains the focal point value
        if (!this.imageUrl && valueOrUrl && !valueOrUrl.startsWith('{')) {
            this.imageUrl = valueOrUrl;
        }

        // Parse existing value
        const existingValue = inputElement.value;
        if (existingValue) {
            try {
                const parsed = JSON.parse(existingValue);
                if (parsed.default) {
                    this.focalPoints = parsed;
                    this.linked = parsed.linked ?? true;
                } else if (parsed.x !== undefined && parsed.y !== undefined) {
                    this.focalPoints.default = parsed;
                }
            } catch (e) {
                console.warn('[FocalPointEditor] Could not parse existing value:', e);
            }
        }

        // Create trigger button
        this.createTrigger();
    }

    /**
     * Create the trigger button that opens the editor
     */
    createTrigger() {
        if (!this.inputElement) return;

        const wrapper = this.inputElement.closest('.focal-point-input-wrapper');
        if (!wrapper) return;

        // Remove existing trigger if any
        const existingTrigger = wrapper.querySelector('.focal-point-trigger');
        if (existingTrigger) existingTrigger.remove();

        const trigger = document.createElement('button');
        trigger.type = 'button';
        trigger.className = 'focal-point-trigger';
        trigger.innerHTML = `
            <span class="focal-point-preview" style="--fp-x: ${this.focalPoints.default.x * 100}%; --fp-y: ${this.focalPoints.default.y * 100}%;"></span>
            <span class="focal-point-label">Focal Point</span>
            <span class="focal-point-value">${this.formatPosition(this.focalPoints.default)}</span>
            <i class="fas fa-crosshairs"></i>
        `;

        trigger.addEventListener('click', (e) => {
            e.preventDefault();
            this.open();
        });

        wrapper.appendChild(trigger);
        this.trigger = trigger;
    }

    /**
     * Format position for display
     */
    formatPosition(point) {
        if (!point) return 'Not set';
        const x = Math.round(point.x * 100);
        const y = Math.round(point.y * 100);

        // Check for common positions
        if (x === 50 && y === 50) return 'Center';
        if (x === 0 && y === 0) return 'Top Left';
        if (x === 100 && y === 0) return 'Top Right';
        if (x === 0 && y === 100) return 'Bottom Left';
        if (x === 100 && y === 100) return 'Bottom Right';
        if (x === 50 && y === 0) return 'Top';
        if (x === 50 && y === 100) return 'Bottom';
        if (x === 0 && y === 50) return 'Left';
        if (x === 100 && y === 50) return 'Right';

        return `${x}% x ${y}%`;
    }

    /**
     * Set or update the image URL
     * @param {string} url - The image URL
     */
    setImageUrl(url) {
        this.imageUrl = url;
    }

    /**
     * Open the focal point editor popup
     */
    open() {
        if (this.popup) this.close();

        // If no image URL set, try to get it from the form's src input
        if (!this.imageUrl && this.inputElement) {
            const form = this.inputElement.closest('form') || this.inputElement.closest('.property-panel');
            if (form) {
                const srcInput = form.querySelector('#prop-src');
                if (srcInput && srcInput.value) {
                    this.imageUrl = srcInput.value;
                }
            }
        }

        // Validate we have an image URL
        if (!this.imageUrl) {
            console.warn('[FocalPointEditor] No image URL available. Please select an image first.');
            // Show alert to user
            AdminModal.alert({message: 'Please select an image first before setting the focal point.', type: 'warning'});
            return;
        }

        // Save initial state for undo
        this.saveToHistory();

        this.createPopup();
        this.positionPopup();
        this.loadImage();

        // Add keyboard listener
        if (this.options.enableKeyboard) {
            document.addEventListener('keydown', this.handleKeydown);
        }

        // Close on escape
        document.addEventListener('keydown', this.handleEscape);
    }

    /**
     * Close the editor popup
     */
    close() {
        if (this.popup) {
            this.popup.remove();
            this.popup = null;
        }

        document.removeEventListener('keydown', this.handleKeydown);
        document.removeEventListener('keydown', this.handleEscape);
    }

    /**
     * Handle escape key to close
     */
    handleEscape = (e) => {
        if (e.key === 'Escape') {
            this.close();
        }
    }

    /**
     * Create the popup HTML structure
     */
    createPopup() {
        this.popup = document.createElement('div');
        this.popup.className = 'focal-point-popup';

        this.popup.innerHTML = `
            <div class="focal-point-header">
                <h3><i class="fas fa-crosshairs"></i> Focal Point</h3>
                <button type="button" class="focal-point-close"><i class="fas fa-times"></i></button>
            </div>

            ${this.options.enableBreakpoints ? `
            <div class="focal-point-breakpoint-tabs">
                <button type="button" class="focal-point-breakpoint-tab active" data-breakpoint="default">
                    <i class="fas fa-desktop"></i> Desktop
                </button>
                <button type="button" class="focal-point-breakpoint-tab" data-breakpoint="tablet">
                    <i class="fas fa-tablet-alt"></i> Tablet
                </button>
                <button type="button" class="focal-point-breakpoint-tab" data-breakpoint="mobile">
                    <i class="fas fa-mobile-alt"></i> Mobile
                </button>
            </div>
            ` : ''}

            <div class="focal-point-body">
                <div class="focal-point-canvas-container">
                    <img class="focal-point-image" alt="Preview" />
                    <div class="focal-point-marker draggable">
                        <div class="focal-point-marker-center"></div>
                    </div>
                    <div class="focal-point-grid ${this.showGrid ? 'visible' : ''}">
                        <div class="focal-point-grid-line horizontal"></div>
                        <div class="focal-point-grid-line horizontal"></div>
                        <div class="focal-point-grid-line vertical"></div>
                        <div class="focal-point-grid-line vertical"></div>
                    </div>
                </div>

                <div class="focal-point-zoom">
                    <button type="button" class="focal-point-zoom-btn" data-zoom="-10"><i class="fas fa-minus"></i></button>
                    <input type="range" class="focal-point-zoom-slider" min="50" max="200" value="${this.zoom}" />
                    <button type="button" class="focal-point-zoom-btn" data-zoom="+10"><i class="fas fa-plus"></i></button>
                    <span class="focal-point-zoom-value">${this.zoom}%</span>
                </div>

                <div class="focal-point-controls">
                    <div class="focal-point-quick-grid">
                        <button type="button" class="focal-point-quick-btn" data-x="0" data-y="0" title="Top Left"><i class="fas fa-arrow-up" style="transform: rotate(-45deg)"></i></button>
                        <button type="button" class="focal-point-quick-btn" data-x="0.5" data-y="0" title="Top"><i class="fas fa-arrow-up"></i></button>
                        <button type="button" class="focal-point-quick-btn" data-x="1" data-y="0" title="Top Right"><i class="fas fa-arrow-up" style="transform: rotate(45deg)"></i></button>
                        <button type="button" class="focal-point-quick-btn" data-x="0" data-y="0.5" title="Left"><i class="fas fa-arrow-left"></i></button>
                        <button type="button" class="focal-point-quick-btn" data-x="0.5" data-y="0.5" title="Center"><i class="fas fa-circle"></i></button>
                        <button type="button" class="focal-point-quick-btn" data-x="1" data-y="0.5" title="Right"><i class="fas fa-arrow-right"></i></button>
                        <button type="button" class="focal-point-quick-btn" data-x="0" data-y="1" title="Bottom Left"><i class="fas fa-arrow-down" style="transform: rotate(45deg)"></i></button>
                        <button type="button" class="focal-point-quick-btn" data-x="0.5" data-y="1" title="Bottom"><i class="fas fa-arrow-down"></i></button>
                        <button type="button" class="focal-point-quick-btn" data-x="1" data-y="1" title="Bottom Right"><i class="fas fa-arrow-down" style="transform: rotate(-45deg)"></i></button>
                    </div>

                    <div class="focal-point-info">
                        <div class="focal-point-coordinates">
                            Position: <span class="focal-point-position-value">${this.formatPosition(this.getCurrentFocalPoint())}</span>
                        </div>
                        <div class="focal-point-options">
                            <label class="focal-point-option">
                                <input type="checkbox" class="focal-point-grid-toggle" ${this.showGrid ? 'checked' : ''} />
                                Show rule of thirds
                            </label>
                            ${this.options.enableBreakpoints ? `
                            <label class="focal-point-option">
                                <input type="checkbox" class="focal-point-link-toggle" ${this.linked ? 'checked' : ''} />
                                Link all breakpoints
                            </label>
                            ` : ''}
                        </div>
                        <div class="focal-point-keyboard-hint">
                            <kbd>Arrow</kbd> = 1% &nbsp; <kbd>Shift</kbd>+<kbd>Arrow</kbd> = 5% &nbsp; <kbd>R</kbd> = Reset &nbsp; <kbd>G</kbd> = Grid
                        </div>
                    </div>
                </div>

                ${this.options.showAspectRatios ? `
                <div class="focal-point-previews">
                    <div class="focal-point-previews-label">Preview at:</div>
                    <div class="focal-point-previews-grid">
                        <div class="focal-point-preview-item" data-ratio="1:1">
                            <div class="focal-point-preview-box ratio-1-1">
                                <img class="focal-point-ratio-preview" data-ratio="1:1" />
                            </div>
                            <span class="focal-point-preview-label">1:1</span>
                        </div>
                        <div class="focal-point-preview-item" data-ratio="16:9">
                            <div class="focal-point-preview-box ratio-16-9">
                                <img class="focal-point-ratio-preview" data-ratio="16:9" />
                            </div>
                            <span class="focal-point-preview-label">16:9</span>
                        </div>
                        <div class="focal-point-preview-item" data-ratio="4:3">
                            <div class="focal-point-preview-box ratio-4-3">
                                <img class="focal-point-ratio-preview" data-ratio="4:3" />
                            </div>
                            <span class="focal-point-preview-label">4:3</span>
                        </div>
                        <div class="focal-point-preview-item" data-ratio="3:2">
                            <div class="focal-point-preview-box ratio-3-2">
                                <img class="focal-point-ratio-preview" data-ratio="3:2" />
                            </div>
                            <span class="focal-point-preview-label">3:2</span>
                        </div>
                    </div>
                </div>
                ` : ''}
            </div>

            <div class="focal-point-footer">
                <button type="button" class="focal-point-btn focal-point-btn-danger focal-point-undo-btn" disabled>
                    <i class="fas fa-undo"></i> Undo
                </button>
                <button type="button" class="focal-point-btn focal-point-btn-secondary focal-point-reset-btn">
                    Reset
                </button>
                <button type="button" class="focal-point-btn focal-point-btn-secondary focal-point-cancel-btn">
                    Cancel
                </button>
                <button type="button" class="focal-point-btn focal-point-btn-primary focal-point-apply-btn">
                    Apply
                </button>
            </div>
        `;

        document.body.appendChild(this.popup);
        this.bindEvents();
        this.makeDraggable();
    }

    /**
     * Bind all event handlers
     */
    bindEvents() {
        // Close button
        this.popup.querySelector('.focal-point-close').addEventListener('click', () => this.close());

        // Cancel button
        this.popup.querySelector('.focal-point-cancel-btn').addEventListener('click', () => this.close());

        // Apply button
        this.popup.querySelector('.focal-point-apply-btn').addEventListener('click', () => {
            this.apply();
            this.close();
        });

        // Reset button
        this.popup.querySelector('.focal-point-reset-btn').addEventListener('click', () => {
            this.setFocalPoint(0.5, 0.5);
        });

        // Undo button
        const undoBtn = this.popup.querySelector('.focal-point-undo-btn');
        undoBtn.addEventListener('click', () => this.undo());

        // Grid toggle
        const gridToggle = this.popup.querySelector('.focal-point-grid-toggle');
        if (gridToggle) {
            gridToggle.addEventListener('change', () => {
                this.showGrid = gridToggle.checked;
                this.popup.querySelector('.focal-point-grid').classList.toggle('visible', this.showGrid);
            });
        }

        // Link toggle
        const linkToggle = this.popup.querySelector('.focal-point-link-toggle');
        if (linkToggle) {
            linkToggle.addEventListener('change', () => {
                this.linked = linkToggle.checked;
            });
        }

        // Breakpoint tabs
        this.popup.querySelectorAll('.focal-point-breakpoint-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                this.switchBreakpoint(tab.dataset.breakpoint);
            });
        });

        // Quick position buttons
        this.popup.querySelectorAll('.focal-point-quick-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const x = parseFloat(btn.dataset.x);
                const y = parseFloat(btn.dataset.y);
                this.setFocalPoint(x, y);
            });
        });

        // Canvas click
        const canvas = this.popup.querySelector('.focal-point-canvas-container');
        canvas.addEventListener('click', this.handleCanvasClick);

        // Marker drag
        const marker = this.popup.querySelector('.focal-point-marker');
        marker.addEventListener('mousedown', (e) => {
            e.preventDefault();
            this.isDragging = true;
            document.addEventListener('mousemove', this.handleCanvasDrag);
            document.addEventListener('mouseup', () => {
                this.isDragging = false;
                document.removeEventListener('mousemove', this.handleCanvasDrag);
            }, { once: true });
        });

        // Zoom controls
        this.popup.querySelectorAll('.focal-point-zoom-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const delta = parseInt(btn.dataset.zoom);
                this.setZoom(this.zoom + delta);
            });
        });

        const zoomSlider = this.popup.querySelector('.focal-point-zoom-slider');
        zoomSlider.addEventListener('input', () => {
            this.setZoom(parseInt(zoomSlider.value));
        });
    }

    /**
     * Handle canvas click to set focal point
     */
    handleCanvasClick(e) {
        const canvas = this.popup.querySelector('.focal-point-canvas-container');
        const img = canvas.querySelector('.focal-point-image');
        const rect = img.getBoundingClientRect();

        const x = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
        const y = Math.max(0, Math.min(1, (e.clientY - rect.top) / rect.height));

        this.setFocalPoint(x, y);
    }

    /**
     * Handle marker drag
     */
    handleCanvasDrag(e) {
        if (!this.isDragging) return;

        const canvas = this.popup.querySelector('.focal-point-canvas-container');
        const img = canvas.querySelector('.focal-point-image');
        const rect = img.getBoundingClientRect();

        const x = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
        const y = Math.max(0, Math.min(1, (e.clientY - rect.top) / rect.height));

        this.setFocalPoint(x, y, false); // Don't save to history during drag
    }

    /**
     * Handle keyboard navigation
     */
    handleKeydown(e) {
        if (!this.popup) return;

        // Check if typing in an input
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

        const step = e.shiftKey ? 0.05 : 0.01; // 5% or 1%
        const current = this.getCurrentFocalPoint();
        let x = current.x;
        let y = current.y;

        switch (e.key) {
            case 'ArrowUp':
                e.preventDefault();
                y = Math.max(0, y - step);
                this.setFocalPoint(x, y);
                break;
            case 'ArrowDown':
                e.preventDefault();
                y = Math.min(1, y + step);
                this.setFocalPoint(x, y);
                break;
            case 'ArrowLeft':
                e.preventDefault();
                x = Math.max(0, x - step);
                this.setFocalPoint(x, y);
                break;
            case 'ArrowRight':
                e.preventDefault();
                x = Math.min(1, x + step);
                this.setFocalPoint(x, y);
                break;
            case 'r':
            case 'R':
                e.preventDefault();
                this.setFocalPoint(0.5, 0.5);
                break;
            case 'g':
            case 'G':
                e.preventDefault();
                const gridToggle = this.popup.querySelector('.focal-point-grid-toggle');
                if (gridToggle) {
                    gridToggle.checked = !gridToggle.checked;
                    gridToggle.dispatchEvent(new Event('change'));
                }
                break;
            case 'z':
                if (e.ctrlKey || e.metaKey) {
                    e.preventDefault();
                    this.undo();
                }
                break;
        }
    }

    /**
     * Get current focal point for active breakpoint
     */
    getCurrentFocalPoint() {
        if (this.linked || !this.focalPoints[this.currentBreakpoint]) {
            return this.focalPoints.default;
        }
        return this.focalPoints[this.currentBreakpoint];
    }

    /**
     * Set focal point
     */
    setFocalPoint(x, y, saveHistory = true) {
        if (saveHistory) {
            this.saveToHistory();
        }

        const point = { x, y };

        if (this.linked) {
            this.focalPoints.default = point;
        } else {
            this.focalPoints[this.currentBreakpoint] = point;
        }

        this.updateMarker();
        this.updateDisplay();
        this.updateQuickButtons();
        this.updateRatioPreviews();
        this.updateUndoButton();
    }

    /**
     * Switch active breakpoint
     */
    switchBreakpoint(breakpoint) {
        this.currentBreakpoint = breakpoint;

        // Update tab styles
        this.popup.querySelectorAll('.focal-point-breakpoint-tab').forEach(tab => {
            tab.classList.toggle('active', tab.dataset.breakpoint === breakpoint);
        });

        // If this breakpoint doesn't have a focal point and not linked, use default
        if (!this.linked && !this.focalPoints[breakpoint]) {
            this.focalPoints[breakpoint] = { ...this.focalPoints.default };
        }

        this.updateMarker();
        this.updateDisplay();
        this.updateQuickButtons();
    }

    /**
     * Update marker position
     */
    updateMarker() {
        const marker = this.popup.querySelector('.focal-point-marker');
        const point = this.getCurrentFocalPoint();

        marker.style.left = `${point.x * 100}%`;
        marker.style.top = `${point.y * 100}%`;
    }

    /**
     * Update coordinate display
     */
    updateDisplay() {
        const positionValue = this.popup.querySelector('.focal-point-position-value');
        positionValue.textContent = this.formatPosition(this.getCurrentFocalPoint());
    }

    /**
     * Update quick position button states
     */
    updateQuickButtons() {
        const point = this.getCurrentFocalPoint();
        this.popup.querySelectorAll('.focal-point-quick-btn').forEach(btn => {
            const x = parseFloat(btn.dataset.x);
            const y = parseFloat(btn.dataset.y);
            const isActive = Math.abs(point.x - x) < 0.01 && Math.abs(point.y - y) < 0.01;
            btn.classList.toggle('active', isActive);
        });
    }

    /**
     * Update aspect ratio previews
     */
    updateRatioPreviews() {
        if (!this.imageUrl) return;

        const point = this.getCurrentFocalPoint();

        this.popup.querySelectorAll('.focal-point-ratio-preview').forEach(img => {
            img.src = this.imageUrl;
            img.style.objectFit = 'cover';
            img.style.objectPosition = `${point.x * 100}% ${point.y * 100}%`;
            img.style.width = '100%';
            img.style.height = '100%';
        });
    }

    /**
     * Set zoom level
     */
    setZoom(value) {
        this.zoom = Math.max(50, Math.min(200, value));

        const img = this.popup.querySelector('.focal-point-image');
        img.style.transform = `scale(${this.zoom / 100})`;
        img.style.transformOrigin = 'center center';

        const zoomSlider = this.popup.querySelector('.focal-point-zoom-slider');
        zoomSlider.value = this.zoom;

        const zoomValue = this.popup.querySelector('.focal-point-zoom-value');
        zoomValue.textContent = `${this.zoom}%`;
    }

    /**
     * Load the image into the canvas
     */
    loadImage() {
        const img = this.popup.querySelector('.focal-point-image');
        img.src = this.imageUrl;

        img.onload = () => {
            this.imageNaturalWidth = img.naturalWidth;
            this.imageNaturalHeight = img.naturalHeight;
            this.updateMarker();
            this.updateRatioPreviews();
        };
    }

    /**
     * Position popup in viewport
     */
    positionPopup() {
        const popup = this.popup;
        const viewportWidth = window.innerWidth;
        const viewportHeight = window.innerHeight;

        // Center in viewport
        popup.style.left = '50%';
        popup.style.top = '50%';
        popup.style.transform = 'translate(-50%, -50%)';
    }

    /**
     * Make popup header draggable
     */
    makeDraggable() {
        const header = this.popup.querySelector('.focal-point-header');
        let isDragging = false;
        let startX, startY, startLeft, startTop;

        header.addEventListener('mousedown', (e) => {
            if (e.target.closest('.focal-point-close')) return;

            isDragging = true;
            this.popup.style.transform = 'none';

            const rect = this.popup.getBoundingClientRect();
            startLeft = rect.left;
            startTop = rect.top;
            startX = e.clientX;
            startY = e.clientY;

            this.popup.style.left = `${startLeft}px`;
            this.popup.style.top = `${startTop}px`;

            document.addEventListener('mousemove', onMouseMove);
            document.addEventListener('mouseup', onMouseUp);
        });

        const onMouseMove = (e) => {
            if (!isDragging) return;

            const deltaX = e.clientX - startX;
            const deltaY = e.clientY - startY;

            this.popup.style.left = `${startLeft + deltaX}px`;
            this.popup.style.top = `${startTop + deltaY}px`;
        };

        const onMouseUp = () => {
            isDragging = false;
            document.removeEventListener('mousemove', onMouseMove);
            document.removeEventListener('mouseup', onMouseUp);
        };
    }

    /**
     * Save current state to history
     */
    saveToHistory() {
        // Remove any future states if we're not at the end
        if (this.historyIndex < this.history.length - 1) {
            this.history = this.history.slice(0, this.historyIndex + 1);
        }

        // Add current state
        this.history.push(JSON.parse(JSON.stringify(this.focalPoints)));

        // Limit history size
        if (this.history.length > this.options.maxHistory) {
            this.history.shift();
        }

        this.historyIndex = this.history.length - 1;
    }

    /**
     * Undo last change
     */
    undo() {
        if (this.historyIndex > 0) {
            this.historyIndex--;
            this.focalPoints = JSON.parse(JSON.stringify(this.history[this.historyIndex]));
            this.updateMarker();
            this.updateDisplay();
            this.updateQuickButtons();
            this.updateRatioPreviews();
            this.updateUndoButton();
        }
    }

    /**
     * Update undo button state
     */
    updateUndoButton() {
        const undoBtn = this.popup.querySelector('.focal-point-undo-btn');
        undoBtn.disabled = this.historyIndex <= 0;
    }

    /**
     * Apply focal point and update input
     */
    apply() {
        if (!this.inputElement) return;

        // Build value object
        let value;
        if (this.linked) {
            // Simple format
            value = this.focalPoints.default;
        } else {
            // Breakpoint format
            value = {
                default: this.focalPoints.default,
                linked: false
            };
            if (this.focalPoints.tablet) {
                value.tablet = this.focalPoints.tablet;
            }
            if (this.focalPoints.mobile) {
                value.mobile = this.focalPoints.mobile;
            }
        }

        this.inputElement.value = JSON.stringify(value);
        this.inputElement.dispatchEvent(new Event('change', { bubbles: true }));
        this.inputElement.dispatchEvent(new Event('input', { bubbles: true }));

        // Update trigger preview
        if (this.trigger) {
            const preview = this.trigger.querySelector('.focal-point-preview');
            preview.style.setProperty('--fp-x', `${this.focalPoints.default.x * 100}%`);
            preview.style.setProperty('--fp-y', `${this.focalPoints.default.y * 100}%`);

            const valueLabel = this.trigger.querySelector('.focal-point-value');
            valueLabel.textContent = this.formatPosition(this.focalPoints.default);
        }

        // Trigger live preview update
        this.updateLivePreview();
    }

    /**
     * Update live preview in page builder
     */
    updateLivePreview() {
        const elementId = this.inputElement?.closest('form')?.dataset?.elementId;
        if (!elementId) return;

        const point = this.focalPoints.default;
        const objectPosition = `${point.x * 100}% ${point.y * 100}%`;

        if (window.livePreview) {
            window.livePreview.updateElement(elementId, {
                focal_point: this.focalPoints,
                object_position: objectPosition
            }, { sync: false });
        }
    }

    /**
     * Get value for CSS object-position
     */
    formatForCSS(breakpoint = 'default') {
        const point = this.focalPoints[breakpoint] || this.focalPoints.default;
        return `${point.x * 100}% ${point.y * 100}%`;
    }

    /**
     * Get full value object
     */
    getValue() {
        if (this.linked) {
            return this.focalPoints.default;
        }
        return {
            default: this.focalPoints.default,
            tablet: this.focalPoints.tablet,
            mobile: this.focalPoints.mobile,
            linked: false
        };
    }

    /**
     * Set value programmatically
     */
    setValue(value) {
        if (value.default) {
            this.focalPoints = value;
            this.linked = value.linked ?? true;
        } else if (value.x !== undefined && value.y !== undefined) {
            this.focalPoints.default = value;
            this.linked = true;
        }
    }
}

// Make available globally
window.FocalPointEditor = FocalPointEditor;

// Auto-initialize when used with property renderer
if (typeof window !== 'undefined') {
    window.initFocalPointEditor = function(inputElement, imageUrl, options = {}) {
        const editor = new FocalPointEditor(options);
        editor.attach(inputElement, imageUrl);
        return editor;
    };
}
