/* Copyright (c) 2025-2026 Spwig. Licensed under AGPL-3.0. */

/**
 * Background Editor Utility for Page Builder
 * Unified interface for color, gradient, image, and video backgrounds
 */

class BackgroundEditor {
    constructor(options = {}) {
        this.options = {
            propertyKey: options.propertyKey || 'background',  // Property key for live preview routing
            elementId: options.elementId,
            elementType: options.elementType,
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

        // Current state being edited
        this.currentState = 'normal'; // 'normal' or 'hover'

        // Background data for both states
        this.backgrounds = {
            normal: {
                type: 'color', // color, gradient, image, video
                color: '#ffffff',
                gradient: 'linear-gradient(90deg, #3b82f6 0%, #8b5cf6 100%)',
                image: {
                    url: '',
                    size: 'cover', // cover, contain, auto, 100% 100%
                    position: 'center center',
                    repeat: 'no-repeat',
                    attachment: 'scroll' // scroll, fixed, local
                },
                video: {
                    url: '',
                    poster: '',
                    autoplay: true,
                    loop: true,
                    muted: true
                },
                overlay: {
                    enabled: false,
                    color: '#000000',
                    opacity: 0.5
                }
            },
            hover: {
                enabled: false,
                type: 'color',
                color: '#f0f0f0',
                gradient: 'linear-gradient(90deg, #8b5cf6 0%, #3b82f6 100%)',
                image: {
                    url: '',
                    size: 'cover',
                    position: 'center center',
                    repeat: 'no-repeat',
                    attachment: 'scroll'
                },
                video: {
                    url: '',
                    poster: '',
                    autoplay: true,
                    loop: true,
                    muted: true
                },
                overlay: {
                    enabled: false,
                    color: '#000000',
                    opacity: 0.5
                }
            }
        };

        // Helper to get current background
        this.background = this.backgrounds.normal;

        // Sub-utility instances
        this.colorPicker = null;
        this.gradientCreator = null;
    }

    attach(element, value = '') {
        this.targetElement = element;
        this.initialValue = value || element.value || '';

        // Get element ID for live preview
        const form = element.closest('.element-properties-form');
        this.elementId = form ? form.dataset.elementId : null;

        // Parse initial value
        if (this.initialValue) {
            this.parseBackground(this.initialValue);
        }

        // Create trigger button
        this.createTrigger();
    }

    createTrigger() {
        this.triggerButton = document.createElement('button');
        this.triggerButton.className = 'util-btn util-btn-primary background-editor-trigger';
        this.triggerButton.type = 'button';
        this.triggerButton.innerHTML = `<i class="fas fa-palette"></i>`;

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

        // Update specific panel previews and UI elements AFTER event listeners are setup
        this.updateImagePreview();
        this.updateVideoPreview();

        // Update overlay UI after everything is initialized
        if (this.updateOverlayUI) {
            this.updateOverlayUI();
        }

        // Make draggable
        this.makeDraggable(this.popup, this.popup.querySelector('.utility-header'));
    }

    close() {
        if (!this.isOpen) return;
        this.isOpen = false;

        // Clean up sub-utilities
        if (this.colorPicker) {
            this.colorPicker.close?.();
            this.colorPicker = null;
        }
        if (this.gradientCreator) {
            this.gradientCreator.close?.();
            this.gradientCreator = null;
        }

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
        this.popup.className = 'utility-popup background-editor';
        this.popup.innerHTML = `
            <div class="utility-header">
                <h3 class="utility-title">Background Settings</h3>
                <button type="button" class="utility-close">
                    <i class="fas fa-times"></i>
                </button>
            </div>

            <div class="utility-body">
                <!-- State Selector -->
                <div class="state-selector">
                    <button class="state-btn active" data-state="normal">
                        <i class="fas fa-mouse-pointer"></i>
                        Normal
                    </button>
                    <button class="state-btn" data-state="hover">
                        <i class="fas fa-hand-pointer"></i>
                        Hover
                    </button>
                </div>

                <!-- Hover Enable Toggle -->
                <div class="hover-enable-section" style="display: none;">
                    <label class="switch">
                        <input type="checkbox" class="hover-enabled" ${this.backgrounds.hover.enabled ? 'checked' : ''}>
                        <span class="switch-slider"></span>
                    </label>
                    <span class="hover-label">Enable hover background</span>
                </div>

                <!-- Preview Section -->
                <div class="background-preview-section">
                    <div class="preview-box">
                        <span class="preview-label">Normal</span>
                        <div class="preview-background preview-normal" data-state="normal">
                            <div class="preview-content">Background</div>
                        </div>
                    </div>
                    <i class="preview-arrow fas fa-exchange-alt"></i>
                    <div class="preview-box">
                        <span class="preview-label">Hover</span>
                        <div class="preview-background preview-hover" data-state="hover">
                            <div class="preview-content">Background</div>
                        </div>
                    </div>
                </div>

                <!-- Type Selector -->
                <div class="background-type-selector">
                    <button class="type-btn active" data-type="color">
                        <i class="fas fa-fill-drip"></i>
                        <span>Color</span>
                    </button>
                    <button class="type-btn" data-type="gradient">
                        <i class="fas fa-palette"></i>
                        <span>Gradient</span>
                    </button>
                    <button class="type-btn" data-type="image">
                        <i class="fas fa-image"></i>
                        <span>Image</span>
                    </button>
                    <button class="type-btn" data-type="video">
                        <i class="fas fa-video"></i>
                        <span>Video</span>
                    </button>
                </div>

                <!-- Content Panels -->
                <div class="background-content">
                    <!-- Color Panel -->
                    <div class="content-panel active" data-panel="color">
                        <div class="color-selector">
                            <div class="color-display" style="background: ${this.background.color}"></div>
                            <input type="text" class="color-input" value="${this.background.color}">
                            <button class="pick-color-btn">
                                <i class="fas fa-eye-dropper"></i>
                            </button>
                        </div>

                        <!-- Quick Color Swatches -->
                        <div class="color-swatches">
                            <div class="swatch" data-color="#ffffff" style="background: #ffffff"></div>
                            <div class="swatch" data-color="#000000" style="background: #000000"></div>
                            <div class="swatch" data-color="#ef4444" style="background: #ef4444"></div>
                            <div class="swatch" data-color="#f59e0b" style="background: #f59e0b"></div>
                            <div class="swatch" data-color="#10b981" style="background: #10b981"></div>
                            <div class="swatch" data-color="#3b82f6" style="background: #3b82f6"></div>
                            <div class="swatch" data-color="#8b5cf6" style="background: #8b5cf6"></div>
                            <div class="swatch" data-color="#ec4899" style="background: #ec4899"></div>
                        </div>
                    </div>

                    <!-- Gradient Panel -->
                    <div class="content-panel" data-panel="gradient">
                        <div class="gradient-selector">
                            <div class="gradient-display" style="background: ${this.background.gradient}"></div>
                            <input type="text" class="gradient-input" value="${this.background.gradient}">
                            <button class="edit-gradient-btn">
                                <i class="fas fa-edit"></i>
                            </button>
                        </div>

                        <!-- Quick Gradient Presets -->
                        <div class="gradient-presets">
                            <div class="preset" data-gradient="linear-gradient(120deg, #89f7fe 0%, #66a6ff 100%)">
                                <div class="preset-preview" style="background: linear-gradient(120deg, #89f7fe 0%, #66a6ff 100%)"></div>
                                <span>Ocean</span>
                            </div>
                            <div class="preset" data-gradient="linear-gradient(45deg, #ff9a56 0%, #ff6a88 100%)">
                                <div class="preset-preview" style="background: linear-gradient(45deg, #ff9a56 0%, #ff6a88 100%)"></div>
                                <span>Sunset</span>
                            </div>
                            <div class="preset" data-gradient="linear-gradient(135deg, #667eea 0%, #52e5a7 100%)">
                                <div class="preset-preview" style="background: linear-gradient(135deg, #667eea 0%, #52e5a7 100%)"></div>
                                <span>Forest</span>
                            </div>
                            <div class="preset" data-gradient="linear-gradient(90deg, #fc5c7d 0%, #6a82fb 100%)">
                                <div class="preset-preview" style="background: linear-gradient(90deg, #fc5c7d 0%, #6a82fb 100%)"></div>
                                <span>Berry</span>
                            </div>
                        </div>
                    </div>

                    <!-- Image Panel -->
                    <div class="content-panel" data-panel="image">
                        <div class="image-selector">
                            <div class="image-preview ${this.background.image.url ? '' : 'empty'}">
                                ${this.background.image.url ?
                                    `<img src="${this.background.image.url}" alt="Background">` :
                                    `<div class="empty-state">
                                        <i class="fas fa-image"></i>
                                        <span>No image selected</span>
                                    </div>`
                                }
                            </div>
                            <div class="image-controls">
                                <button class="btn btn-browse-image">
                                    <i class="fas fa-images"></i>
                                    Browse Media Library
                                </button>
                            </div>
                        </div>

                        <!-- Image Settings -->
                        <div class="image-settings">
                            <div class="setting-row">
                                <label>Size</label>
                                <select class="image-size">
                                    <option value="cover">Cover</option>
                                    <option value="contain">Contain</option>
                                    <option value="auto">Auto</option>
                                    <option value="100% 100%">Stretch</option>
                                </select>
                            </div>
                            <div class="setting-row">
                                <label>Position</label>
                                <div class="position-grid">
                                    <button class="pos-btn" data-position="left top"><i class="fas fa-arrow-up-left"></i></button>
                                    <button class="pos-btn" data-position="center top"><i class="fas fa-arrow-up"></i></button>
                                    <button class="pos-btn" data-position="right top"><i class="fas fa-arrow-up-right"></i></button>
                                    <button class="pos-btn" data-position="left center"><i class="fas fa-arrow-left"></i></button>
                                    <button class="pos-btn active" data-position="center center"><i class="fas fa-crosshairs"></i></button>
                                    <button class="pos-btn" data-position="right center"><i class="fas fa-arrow-right"></i></button>
                                    <button class="pos-btn" data-position="left bottom"><i class="fas fa-arrow-down-left"></i></button>
                                    <button class="pos-btn" data-position="center bottom"><i class="fas fa-arrow-down"></i></button>
                                    <button class="pos-btn" data-position="right bottom"><i class="fas fa-arrow-down-right"></i></button>
                                </div>
                            </div>
                            <div class="setting-row">
                                <label>Repeat</label>
                                <select class="image-repeat">
                                    <option value="no-repeat">No Repeat</option>
                                    <option value="repeat">Repeat</option>
                                    <option value="repeat-x">Repeat X</option>
                                    <option value="repeat-y">Repeat Y</option>
                                </select>
                            </div>
                            <div class="setting-row">
                                <label>Attachment</label>
                                <select class="image-attachment">
                                    <option value="scroll">Scroll</option>
                                    <option value="fixed">Fixed</option>
                                    <option value="local">Local</option>
                                </select>
                            </div>
                        </div>
                    </div>

                    <!-- Video Panel -->
                    <div class="content-panel" data-panel="video">
                        <div class="video-selector">
                            <div class="video-preview ${this.background.video.url ? '' : 'empty'}">
                                ${this.background.video.url ?
                                    `<video src="${this.background.video.url}" poster="${this.background.video.poster}" muted></video>` :
                                    `<div class="empty-state">
                                        <i class="fas fa-video"></i>
                                        <span>No video selected</span>
                                    </div>`
                                }
                            </div>
                            <div class="video-controls">
                                <button class="btn btn-browse-video">
                                    <i class="fas fa-video"></i>
                                    Browse Media Library
                                </button>
                            </div>
                        </div>

                        <!-- Video Settings -->
                        <div class="video-settings">
                            <div class="setting-row">
                                <label>Poster Image</label>
                                <div class="poster-controls">
                                    <input type="text" class="poster-input" placeholder="Poster URL" value="${this.background.video.poster}">
                                    <button class="btn-select-poster">
                                        <i class="fas fa-image"></i>
                                    </button>
                                </div>
                            </div>
                            <div class="setting-row">
                                <label>Options</label>
                                <div class="video-options">
                                    <label class="checkbox-label">
                                        <input type="checkbox" class="video-autoplay" ${this.background.video.autoplay ? 'checked' : ''}>
                                        <span>Autoplay</span>
                                    </label>
                                    <label class="checkbox-label">
                                        <input type="checkbox" class="video-loop" ${this.background.video.loop ? 'checked' : ''}>
                                        <span>Loop</span>
                                    </label>
                                    <label class="checkbox-label">
                                        <input type="checkbox" class="video-muted" ${this.background.video.muted ? 'checked' : ''}>
                                        <span>Muted</span>
                                    </label>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Overlay Settings (for image/video) -->
                <div class="overlay-section" style="display: none;">
                    <h4>Overlay <span class="overlay-state-label">(Normal)</span></h4>
                    <div class="overlay-controls">
                        <label class="switch">
                            <input type="checkbox" class="overlay-enabled">
                            <span class="switch-slider"></span>
                        </label>
                        <div class="overlay-settings" style="display: none;">
                            <div class="overlay-color-control">
                                <div class="overlay-color-display" style="background: #000000"></div>
                                <input type="text" class="overlay-color-input" value="#000000">
                            </div>
                            <div class="overlay-opacity-control">
                                <label>Opacity</label>
                                <input type="range" class="overlay-opacity" min="0" max="100" value="50">
                                <span class="opacity-value">50%</span>
                            </div>
                        </div>
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

        // State selector buttons
        this.popup.querySelectorAll('.state-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.currentState = btn.dataset.state;
                this.background = this.backgrounds[this.currentState];
                this.updateStateSelection();
                this.updateUI();

                // Update specific panel previews for current background type
                if (this.background.type === 'image') {
                    this.updateImagePreview();
                } else if (this.background.type === 'video') {
                    this.updateVideoPreview();
                }
            });
        });

        // Hover enabled toggle
        const hoverEnabled = this.popup.querySelector('.hover-enabled');
        if (hoverEnabled) {
            hoverEnabled.addEventListener('change', (e) => {
                this.backgrounds.hover.enabled = e.target.checked;
                this.updatePreview();
            });
        }

        // Type selector buttons
        this.popup.querySelectorAll('.type-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.background.type = btn.dataset.type;
                this.updateTypeSelection();
                this.updatePreview();

                // Update specific panel previews
                if (btn.dataset.type === 'image') {
                    this.updateImagePreview();
                } else if (btn.dataset.type === 'video') {
                    this.updateVideoPreview();
                }
            });
        });

        // Color panel
        this.setupColorPanel();

        // Gradient panel
        this.setupGradientPanel();

        // Image panel
        this.setupImagePanel();

        // Video panel
        this.setupVideoPanel();

        // Overlay settings
        this.setupOverlaySettings();

        // Footer buttons
        this.popup.querySelector('.btn-clear').addEventListener('click', () => {
            // Clear current state
            this.backgrounds[this.currentState] = {
                type: 'color',
                color: 'transparent',
                gradient: 'linear-gradient(90deg, #3b82f6 0%, #8b5cf6 100%)',
                image: { url: '', size: 'cover', position: 'center center', repeat: 'no-repeat', attachment: 'scroll' },
                video: { url: '', poster: '', autoplay: true, loop: true, muted: true },
                overlay: { enabled: false, color: '#000000', opacity: 0.5 }
            };

            // If clearing hover state, also disable it
            if (this.currentState === 'hover') {
                this.backgrounds.hover.enabled = false;
                this.popup.querySelector('.hover-enabled').checked = false;
            }

            this.background = this.backgrounds[this.currentState];
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
                // Check if clicking on any sub-utility popup or media library
                // This includes color picker opened from gradient creator
                const clickedUtility = e.target.closest('.utility-popup');
                const isMediaLibrary = e.target.closest('.media-modal');
                const isSubUtility = (clickedUtility && clickedUtility !== this.popup) || isMediaLibrary;

                if (!isSubUtility) {
                    this.close();
                }
            }
        };

        setTimeout(() => {
            document.addEventListener('mousedown', this.handleOutsideClick);
        }, 100);
    }

    setupColorPanel() {
        const panel = this.popup.querySelector('[data-panel="color"]');

        // Color picker button
        const pickColorBtn = panel.querySelector('.pick-color-btn');
        const colorDisplay = panel.querySelector('.color-display');
        const colorInput = panel.querySelector('.color-input');

        pickColorBtn.addEventListener('click', () => {
            this.openColorPicker(colorDisplay);
        });

        colorDisplay.addEventListener('click', () => {
            this.openColorPicker(colorDisplay);
        });

        colorInput.addEventListener('input', (e) => {
            this.background.color = e.target.value;
            colorDisplay.style.background = e.target.value;
            this.updatePreview();
        });

        // Color swatches
        panel.querySelectorAll('.swatch').forEach(swatch => {
            swatch.addEventListener('click', () => {
                this.background.color = swatch.dataset.color;
                colorDisplay.style.background = swatch.dataset.color;
                colorInput.value = swatch.dataset.color;
                this.updatePreview();
            });
        });
    }

    setupGradientPanel() {
        const panel = this.popup.querySelector('[data-panel="gradient"]');

        // Gradient editor button
        const editGradientBtn = panel.querySelector('.edit-gradient-btn');
        const gradientDisplay = panel.querySelector('.gradient-display');
        const gradientInput = panel.querySelector('.gradient-input');

        editGradientBtn.addEventListener('click', () => {
            this.openGradientCreator(gradientDisplay);
        });

        gradientDisplay.addEventListener('click', () => {
            this.openGradientCreator(gradientDisplay);
        });

        gradientInput.addEventListener('input', (e) => {
            this.background.gradient = e.target.value;
            gradientDisplay.style.background = e.target.value;
            this.updatePreview();
        });

        // Gradient presets
        panel.querySelectorAll('.preset').forEach(preset => {
            preset.addEventListener('click', () => {
                this.background.gradient = preset.dataset.gradient;
                gradientDisplay.style.background = preset.dataset.gradient;
                gradientInput.value = preset.dataset.gradient;
                this.updatePreview();
            });
        });
    }

    setupImagePanel() {
        const panel = this.popup.querySelector('[data-panel="image"]');

        // Image selection button
        panel.querySelector('.btn-browse-image').addEventListener('click', () => {
            this.browseImage();
        });

        // Image settings
        const sizeSelect = panel.querySelector('.image-size');
        sizeSelect.value = this.background.image.size;
        sizeSelect.addEventListener('change', (e) => {
            this.background.image.size = e.target.value;
            this.updatePreview();
        });

        // Position grid
        panel.querySelectorAll('.pos-btn').forEach(btn => {
            if (btn.dataset.position === this.background.image.position) {
                btn.classList.add('active');
            }
            btn.addEventListener('click', () => {
                panel.querySelectorAll('.pos-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.background.image.position = btn.dataset.position;
                this.updatePreview();
            });
        });

        // Repeat
        const repeatSelect = panel.querySelector('.image-repeat');
        repeatSelect.value = this.background.image.repeat;
        repeatSelect.addEventListener('change', (e) => {
            this.background.image.repeat = e.target.value;
            this.updatePreview();
        });

        // Attachment
        const attachmentSelect = panel.querySelector('.image-attachment');
        attachmentSelect.value = this.background.image.attachment;
        attachmentSelect.addEventListener('change', (e) => {
            this.background.image.attachment = e.target.value;
            this.updatePreview();
        });
    }

    setupVideoPanel() {
        const panel = this.popup.querySelector('[data-panel="video"]');

        // Video selection button
        panel.querySelector('.btn-browse-video').addEventListener('click', () => {
            this.browseVideo();
        });

        // Poster image
        panel.querySelector('.btn-select-poster').addEventListener('click', () => {
            this.browsePosterImage();
        });

        panel.querySelector('.poster-input').addEventListener('input', (e) => {
            this.background.video.poster = e.target.value;
            this.updateVideoPreview();
        });

        // Video options
        panel.querySelector('.video-autoplay').addEventListener('change', (e) => {
            this.background.video.autoplay = e.target.checked;
            this.updatePreview();
        });

        panel.querySelector('.video-loop').addEventListener('change', (e) => {
            this.background.video.loop = e.target.checked;
            this.updatePreview();
        });

        panel.querySelector('.video-muted').addEventListener('change', (e) => {
            this.background.video.muted = e.target.checked;
            this.updatePreview();
        });
    }

    setupOverlaySettings() {
        const overlaySection = this.popup.querySelector('.overlay-section');
        const overlayEnabled = overlaySection.querySelector('.overlay-enabled');
        const overlaySettings = overlaySection.querySelector('.overlay-settings');

        // Update overlay UI when state changes
        this.updateOverlayUI = () => {
            const currentOverlay = this.background.overlay;
            overlayEnabled.checked = currentOverlay.enabled;
            overlaySettings.style.display = currentOverlay.enabled ? '' : 'none';

            overlaySection.querySelector('.overlay-color-display').style.background = currentOverlay.color;
            overlaySection.querySelector('.overlay-color-input').value = currentOverlay.color;
            overlaySection.querySelector('.overlay-opacity').value = currentOverlay.opacity * 100;
            overlaySection.querySelector('.opacity-value').textContent = Math.round(currentOverlay.opacity * 100) + '%';

            // Update label to show current state
            overlaySection.querySelector('.overlay-state-label').textContent =
                `(${this.currentState === 'hover' ? 'Hover' : 'Normal'})`;
        };

        overlayEnabled.addEventListener('change', (e) => {
            this.background.overlay.enabled = e.target.checked;
            overlaySettings.style.display = e.target.checked ? '' : 'none';
            console.log('Overlay toggled:', {
                enabled: e.target.checked,
                currentState: this.currentState,
                backgroundType: this.background.type,
                normalType: this.backgrounds.normal.type,
                hoverType: this.backgrounds.hover.type
            });
            this.updatePreview();
        });

        // Overlay color
        const overlayColorDisplay = overlaySection.querySelector('.overlay-color-display');
        const overlayColorInput = overlaySection.querySelector('.overlay-color-input');

        overlayColorDisplay.addEventListener('click', () => {
            this.openColorPicker(overlayColorDisplay, (color) => {
                // Extract base color without alpha for storage
                let baseColor = color;
                if (color.includes('rgba')) {
                    // Convert rgba to hex
                    const match = color.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
                    if (match) {
                        const r = parseInt(match[1]);
                        const g = parseInt(match[2]);
                        const b = parseInt(match[3]);
                        baseColor = `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
                    }
                }
                this.background.overlay.color = baseColor;
                overlayColorInput.value = baseColor;
                overlayColorDisplay.style.background = baseColor;
                this.updatePreview();
            });
        });

        overlayColorInput.addEventListener('input', (e) => {
            this.background.overlay.color = e.target.value;
            overlayColorDisplay.style.background = e.target.value;
            this.updatePreview();
        });

        // Overlay opacity
        const overlayOpacity = overlaySection.querySelector('.overlay-opacity');
        const opacityValue = overlaySection.querySelector('.opacity-value');

        overlayOpacity.addEventListener('input', (e) => {
            this.background.overlay.opacity = e.target.value / 100;
            opacityValue.textContent = e.target.value + '%';

            // If overlay color picker is open, update its opacity
            if (this.overlayColorPicker && this.overlayColorPicker.isOpen) {
                // Update the color picker's current alpha
                if (this.overlayColorPicker.currentColor) {
                    this.overlayColorPicker.currentColor.alpha = e.target.value / 100;
                    if (this.overlayColorPicker.updateUI) {
                        this.overlayColorPicker.updateUI();
                    }
                }
            }

            this.updatePreview();
        });
    }

    openColorPicker(triggerElement, callbackOrInitialColor) {
        if (window.ColorPickerUtility) {
            let initialColor = this.background.color;  // Default to background color
            let callback = null;
            let isOverlay = false;

            // Check if callbackOrInitialColor is a function (callback) or string (color)
            if (typeof callbackOrInitialColor === 'function') {
                callback = callbackOrInitialColor;
                // For overlay color picker, use the overlay color as initial
                if (triggerElement && triggerElement.classList.contains('overlay-color-display')) {
                    isOverlay = true;
                    // Convert overlay color to rgba with current opacity
                    const overlayColor = this.background.overlay.color || '#000000';
                    const overlayOpacity = this.background.overlay.opacity || 0.5;
                    initialColor = this.addAlphaToColor(overlayColor, overlayOpacity);
                }
            } else if (typeof callbackOrInitialColor === 'string') {
                initialColor = callbackOrInitialColor;
            }

            // Create appropriate color picker based on context
            const pickerKey = isOverlay ? 'overlayColorPicker' : 'colorPicker';

            if (!this[pickerKey]) {
                this[pickerKey] = new window.ColorPickerUtility({
                    showOpacity: isOverlay,  // Show opacity slider for overlay colors
                    onChange: (color) => {
                        if (callback) {
                            // For overlay, always extract and sync opacity
                            if (isOverlay) {
                                let opacity = 1;

                                // Extract opacity from rgba color
                                if (color.includes('rgba')) {
                                    const match = color.match(/rgba?\([^,]+,[^,]+,[^,]+,\s*([\d.]+)\)/);
                                    if (match) {
                                        opacity = parseFloat(match[1]);
                                    }
                                } else if (color.includes('#') && color.length === 9) {
                                    // Handle 8-digit hex with alpha
                                    const alpha = parseInt(color.slice(7, 9), 16);
                                    opacity = alpha / 255;
                                }

                                // Update the background overlay opacity
                                this.background.overlay.opacity = opacity;

                                // Update the overlay opacity slider in background editor
                                const overlaySection = this.popup.querySelector('.overlay-section');
                                if (overlaySection) {
                                    const opacitySlider = overlaySection.querySelector('.overlay-opacity');
                                    const opacityValue = overlaySection.querySelector('.opacity-value');
                                    if (opacitySlider) {
                                        opacitySlider.value = opacity * 100;
                                    }
                                    if (opacityValue) {
                                        opacityValue.textContent = Math.round(opacity * 100) + '%';
                                    }
                                }
                            }
                            callback(color);
                        } else {
                            this.background.color = color;
                            this.popup.querySelector('.color-input').value = color;
                            this.popup.querySelector('.color-display').style.background = color;
                            this.updatePreview();
                        }
                    }
                });
            }
            this[pickerKey].open(triggerElement, initialColor);
        }
    }

    openGradientCreator(triggerElement) {
        if (window.GradientCreator) {
            if (!this.gradientCreator) {
                this.gradientCreator = new window.GradientCreator({
                    createTrigger: false,  // Don't create a trigger button since we're opening programmatically
                    onChange: (gradient) => {
                        this.background.gradient = gradient;
                        this.popup.querySelector('.gradient-input').value = gradient;
                        this.popup.querySelector('.gradient-display').style.background = gradient;
                        this.updatePreview();
                    }
                });
            }
            this.gradientCreator.attach(triggerElement, this.background.gradient);
            this.gradientCreator.open();
        }
    }

    browseImage() {
        if (!window.selectImageFromLibrary) {
            AdminModal.alert({message: 'Media library is not available.', type: 'error'});
            return;
        }

        window.selectImageFromLibrary((media) => {
            if (!media) return;

            const url = media.webp_url || media.url || media.original_url || '';
            if (!url) return;

            this.background.image.url = url;
            this.updateImagePreview();
            this.updatePreview();
        });
    }

    browseVideo() {
        if (!window.selectMediaFromLibrary) {
            AdminModal.alert({message: 'Media library is not available.', type: 'error'});
            return;
        }

        window.selectMediaFromLibrary((media) => {
            if (!media) return;

            const url = media.url || media.original_url || '';
            if (!url) return;

            this.background.video.url = url;

            // Auto-set poster from video thumbnail if available
            const posterUrl = media.thumbnail_url || '';
            if (posterUrl) {
                this.background.video.poster = posterUrl;
                const posterInput = this.popup.querySelector('.poster-input');
                if (posterInput) {
                    posterInput.value = posterUrl;
                }
            }

            this.updateVideoPreview();
            this.updatePreview();
        }, { fileTypeFilter: 'video' });
    }

    browsePosterImage() {
        if (!window.selectImageFromLibrary) {
            AdminModal.alert({message: 'Media library is not available.', type: 'error'});
            return;
        }

        window.selectImageFromLibrary((media) => {
            if (!media) return;

            const url = media.webp_url || media.url || media.original_url || '';
            if (!url) return;

            this.background.video.poster = url;
            const posterInput = this.popup.querySelector('.poster-input');
            if (posterInput) {
                posterInput.value = url;
            }
            this.updateVideoPreview();
            this.updatePreview();
        });
    }

    updateUI() {
        this.updateStateSelection();
        this.updateTypeSelection();
        this.updatePreview();
    }

    updateStateSelection() {
        // Update state buttons
        this.popup.querySelectorAll('.state-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.state === this.currentState);
        });

        // Show/hide hover enable section
        const hoverEnableSection = this.popup.querySelector('.hover-enable-section');
        hoverEnableSection.style.display = this.currentState === 'hover' ? 'block' : 'none';

        // Sync hover enable checkbox with current state
        const hoverEnabled = this.popup.querySelector('.hover-enabled');
        if (hoverEnabled) {
            hoverEnabled.checked = this.backgrounds.hover.enabled;
        }

        // Update current background reference
        this.background = this.backgrounds[this.currentState];

        // Update overlay UI for current state
        if (this.updateOverlayUI) {
            this.updateOverlayUI();
        }
    }

    updateTypeSelection() {
        // Update type buttons
        this.popup.querySelectorAll('.type-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.type === this.background.type);
        });

        // Update content panels
        this.popup.querySelectorAll('.content-panel').forEach(panel => {
            panel.classList.toggle('active', panel.dataset.panel === this.background.type);
        });

        // Show/hide overlay section for image/video
        const overlaySection = this.popup.querySelector('.overlay-section');
        overlaySection.style.display = (this.background.type === 'image' || this.background.type === 'video') ? '' : 'none';

        // Update overlay UI when type changes
        if (this.updateOverlayUI && (this.background.type === 'image' || this.background.type === 'video')) {
            this.updateOverlayUI();
        }
    }

    updatePreview() {
        // Update both normal and hover previews
        const normalCSS = this.generateCSS('normal');
        const hoverCSS = this.backgrounds.hover.enabled ? this.generateCSS('hover') : normalCSS;

        const normalPreview = this.popup.querySelector('.preview-normal');
        const hoverPreview = this.popup.querySelector('.preview-hover');

        normalPreview.style.background = normalCSS;
        hoverPreview.style.background = hoverCSS;

        // Highlight current state preview
        normalPreview.classList.toggle('active', this.currentState === 'normal');
        hoverPreview.classList.toggle('active', this.currentState === 'hover');

        // Note: In v1.0.1, trigger button only shows icon (no preview swatch to update)

        // Update live preview immediately for instant feedback
        if (this.elementId) {
            if (window.livePreview) {
                // Use propertyKey so LivePreviewManager can route to correct nested element
                const updates = {};
                updates[this.options.propertyKey] = normalCSS;

                // For video backgrounds, include data attributes
                if (this.backgrounds.normal.type === 'video') {
                    updates['data-video-url'] = this.backgrounds.normal.video.url || '';
                    updates['data-video-poster'] = this.backgrounds.normal.video.poster || '';
                    updates['data-video-autoplay'] = this.backgrounds.normal.video.autoplay ? 'true' : 'false';
                    updates['data-video-loop'] = this.backgrounds.normal.video.loop ? 'true' : 'false';
                    updates['data-video-muted'] = this.backgrounds.normal.video.muted ? 'true' : 'false';

                    // Add overlay settings if enabled
                    if (this.backgrounds.normal.overlay.enabled) {
                        updates['data-video-overlay-enabled'] = 'true';
                        updates['data-video-overlay-color'] = this.backgrounds.normal.overlay.color || '#000000';
                        updates['data-video-overlay-opacity'] = this.backgrounds.normal.overlay.opacity || 0.5;
                    } else {
                        updates['data-video-overlay-enabled'] = 'false';
                    }
                } else {
                    // Clear video attributes if not video type
                    updates['data-video-url'] = '';
                }

                window.livePreview.updateElement(this.elementId, updates, { sync: false }); // Visual only, don't sync to server yet
            }
        }

        // Notify change - this will trigger the property renderer's update flow
        // which handles both saving and live preview
        if (this.options.onChange) {
            this.options.onChange(normalCSS);
        }

        // Store hover state in data attribute for future use
        if (this.targetElement) {
            if (this.backgrounds.hover.enabled) {
                this.targetElement.dataset.hoverBackground = hoverCSS;
            } else {
                delete this.targetElement.dataset.hoverBackground;
            }
        }
    }

    updateImagePreview() {
        const panel = this.popup.querySelector('[data-panel="image"]');
        const preview = panel.querySelector('.image-preview');

        if (this.background.image.url) {
            preview.classList.remove('empty');
            preview.innerHTML = `<img src="${this.background.image.url}" alt="Background">`;
        } else {
            preview.classList.add('empty');
            preview.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-image"></i>
                    <span>No image selected</span>
                </div>
            `;
        }
    }

    updateVideoPreview() {
        const panel = this.popup.querySelector('[data-panel="video"]');
        if (!panel) return;

        const preview = panel.querySelector('.video-preview');

        if (this.background.video.url) {
            preview.classList.remove('empty');
            preview.innerHTML = `<video src="${this.background.video.url}"
                                         ${this.background.video.poster ? `poster="${this.background.video.poster}"` : ''}
                                         muted></video>`;
        } else {
            preview.classList.add('empty');
            preview.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-video"></i>
                    <span>No video selected</span>
                </div>
            `;
        }
    }

    generateCSS(state = null) {
        const bg = state ? this.backgrounds[state] : this.background;

        switch (bg.type) {
            case 'color':
                return bg.color;

            case 'gradient':
                return bg.gradient;

            case 'image':
                if (!bg.image.url) return 'transparent';
                let css = `url("${bg.image.url}")`;
                css += ` ${bg.image.position}`;
                css += ` / ${bg.image.size}`;
                css += ` ${bg.image.repeat}`;
                css += ` ${bg.image.attachment}`;

                if (bg.overlay.enabled) {
                    const overlayColor = this.addAlphaToColor(
                        bg.overlay.color,
                        bg.overlay.opacity
                    );
                    css = `linear-gradient(${overlayColor}, ${overlayColor}), ${css}`;
                }
                return css;

            case 'video':
                // Video backgrounds need HTML elements, but for CSS fallback use poster
                // The actual video rendering is handled separately via data attributes
                if (!bg.video.poster) return 'transparent';

                let videoCss = `url("${bg.video.poster}") center center / cover no-repeat`;

                if (bg.overlay.enabled) {
                    const overlayColor = this.addAlphaToColor(
                        bg.overlay.color,
                        bg.overlay.opacity
                    );
                    videoCss = `linear-gradient(${overlayColor}, ${overlayColor}), ${videoCss}`;
                }

                return videoCss;

            default:
                return 'transparent';
        }
    }

    getPreviewStyle() {
        // Simplified preview for trigger button
        switch (this.background.type) {
            case 'color':
                return this.background.color;
            case 'gradient':
                return this.background.gradient;
            case 'image':
                return this.background.image.url ?
                    `url("${this.background.image.url}") center/cover` :
                    'transparent';
            case 'video':
                return this.background.video.poster ?
                    `url("${this.background.video.poster}") center/cover` :
                    'transparent';
            default:
                return 'transparent';
        }
    }

    addAlphaToColor(color, alpha) {
        if (color.startsWith('#')) {
            const r = parseInt(color.slice(1, 3), 16);
            const g = parseInt(color.slice(3, 5), 16);
            const b = parseInt(color.slice(5, 7), 16);
            return `rgba(${r}, ${g}, ${b}, ${alpha})`;
        }
        return color;
    }

    parseBackground(css) {
        // Check if we have stored data FIRST - this preserves the exact background type and settings
        // First, check for hidden input field (persisted to server)
        const inputName = this.targetElement.name;
        const dataInputName = inputName + '_data';
        const dataInput = this.targetElement.parentElement?.querySelector(`input[name="${dataInputName}"]`);
        if (dataInput && dataInput.value) {
            try {
                const storedData = JSON.parse(dataInput.value);
                this.backgrounds = storedData;
                console.log('[BackgroundEditor] Restored from hidden input field:', storedData);
                // Also update the data attribute for consistency
                this.targetElement.dataset.backgroundData = dataInput.value;
                return;
            } catch (e) {
                console.warn('Could not parse stored background data from hidden input, trying data attribute');
            }
        }

        // Second, check data attribute (DOM only, not persisted)
        if (this.targetElement.dataset.backgroundData) {
            try {
                const storedData = JSON.parse(this.targetElement.dataset.backgroundData);
                this.backgrounds = storedData;
                console.log('[BackgroundEditor] Restored from data attribute:', storedData);
                return;
            } catch (e) {
                console.warn('Could not parse stored background data from attribute, falling back to CSS parsing');
            }
        }

        // Fallback: Parse background CSS or JSON if no stored data
        if (typeof css === 'string' && css.startsWith('{')) {
            // It's JSON with both states
            try {
                const data = JSON.parse(css);
                if (data.normal) {
                    this.parseBackgroundState(data.normal, 'normal');
                }
                if (data.hover) {
                    this.parseBackgroundState(data.hover, 'hover');
                    this.backgrounds.hover.enabled = true;
                }
            } catch (e) {
                // Fallback to parsing as normal state
                this.parseBackgroundState(css, 'normal');
            }
        } else {
            // Parse as normal state only
            this.parseBackgroundState(css, 'normal');
        }
    }

    parseBackgroundState(css, state) {
        const bg = this.backgrounds[state];

        // Check for overlay (linear-gradient overlay pattern)
        if (css.includes('linear-gradient(') && css.includes('url(')) {
            // This is an image with overlay
            const parts = css.split('),');
            if (parts.length > 1) {
                // First part is the overlay
                const overlayPart = parts[0] + ')';
                const overlayMatch = overlayPart.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?\)/);
                if (overlayMatch) {
                    const [, r, g, b, a] = overlayMatch;
                    bg.overlay.enabled = true;
                    bg.overlay.color = `#${parseInt(r).toString(16).padStart(2, '0')}${parseInt(g).toString(16).padStart(2, '0')}${parseInt(b).toString(16).padStart(2, '0')}`;
                    bg.overlay.opacity = a ? parseFloat(a) : 0.5;
                }

                // Second part is the background
                const bgPart = parts.slice(1).join('),');
                if (bgPart.includes('url(')) {
                    bg.type = 'image';
                    const urlMatch = bgPart.match(/url\(["']?([^"')]+)["']?\)/);
                    if (urlMatch) {
                        bg.image.url = urlMatch[1];
                    }
                }
            }
        } else if (css.includes('url(')) {
            bg.type = 'image';
            // Extract URL
            const urlMatch = css.match(/url\(["']?([^"')]+)["']?\)/);
            if (urlMatch) {
                bg.image.url = urlMatch[1];
            }
        } else if (css.includes('gradient')) {
            bg.type = 'gradient';
            bg.gradient = css;
        } else if (css) {
            bg.type = 'color';
            bg.color = css;
        }
    }

    applyValue() {
        const normalCSS = this.generateCSS('normal');
        const hoverCSS = this.backgrounds.hover.enabled ? this.generateCSS('hover') : '';

        // Store complete background data as JSON
        const backgroundData = JSON.stringify(this.backgrounds);

        // Store in data attribute for immediate access
        this.targetElement.dataset.backgroundData = backgroundData;

        // Also store in a hidden input field so it gets saved to the server
        // Find or create a hidden input for background_data
        const inputName = this.targetElement.name;
        const dataInputName = inputName + '_data';
        let dataInput = this.targetElement.parentElement?.querySelector(`input[name="${dataInputName}"]`);
        if (!dataInput) {
            dataInput = document.createElement('input');
            dataInput.type = 'hidden';
            dataInput.name = dataInputName;
            this.targetElement.parentElement?.appendChild(dataInput);
        }
        dataInput.value = backgroundData;

        // Update input value with normal CSS
        // Always save the normal CSS as the main value
        this.targetElement.value = normalCSS;

        // Store hover CSS in a data attribute if enabled
        if (this.backgrounds.hover.enabled && hoverCSS) {
            this.targetElement.dataset.hoverBackground = hoverCSS;
        } else {
            delete this.targetElement.dataset.hoverBackground;
        }

        // Trigger events
        this.targetElement.dispatchEvent(new Event('input', { bubbles: true }));
        this.targetElement.dispatchEvent(new Event('change', { bubbles: true }));

        // Update live preview - Use LivePreviewManager for instant updates
        if (this.elementId) {
            // Use propertyKey for correct routing (e.g., 'button_background' routes to button element)
            const updates = { [this.options.propertyKey]: normalCSS };

            // For video backgrounds, also update data attributes so frontend can render video element
            if (this.backgrounds.normal.type === 'video') {
                updates['data-video-url'] = this.backgrounds.normal.video.url || '';
                updates['data-video-poster'] = this.backgrounds.normal.video.poster || '';
                updates['data-video-autoplay'] = this.backgrounds.normal.video.autoplay ? 'true' : 'false';
                updates['data-video-loop'] = this.backgrounds.normal.video.loop ? 'true' : 'false';
                updates['data-video-muted'] = this.backgrounds.normal.video.muted ? 'true' : 'false';

                // Add overlay settings if enabled
                if (this.backgrounds.normal.overlay.enabled) {
                    updates['data-video-overlay-enabled'] = 'true';
                    updates['data-video-overlay-color'] = this.backgrounds.normal.overlay.color || '#000000';
                    updates['data-video-overlay-opacity'] = this.backgrounds.normal.overlay.opacity || 0.5;
                } else {
                    updates['data-video-overlay-enabled'] = 'false';
                    updates['data-video-overlay-color'] = '';
                    updates['data-video-overlay-opacity'] = '';
                }
            } else {
                // Clear video attributes if not video type
                updates['data-video-url'] = '';
                updates['data-video-overlay-enabled'] = '';
            }

            // Add hover background to updates
            // 'hover_background' is used by both:
            // - Templates for CSS-based hover effects (rendered in <style> blocks)
            // - LivePreviewManager for instant visual preview (CSS injection)
            if (this.backgrounds.hover.enabled && hoverCSS) {
                updates['hover_background'] = hoverCSS;
            } else {
                updates['hover_background'] = '';
            }

            // Add full background data to updates for server persistence
            // The key should match the hidden input name pattern
            const inputName = this.targetElement.name;
            updates[inputName + '_data'] = backgroundData;

            if (window.livePreview) {
                // Use LivePreviewManager for instant visual updates AND sync to server
                // LivePreviewManager handles hover background via hover_background property (CSS injection)
                console.log('[BackgroundEditor] Using LivePreviewManager for updates:', {
                    elementId: this.elementId,
                    hoverEnabled: this.backgrounds.hover.enabled,
                    hoverCSS: hoverCSS ? hoverCSS.substring(0, 80) + '...' : null,
                    updateKeys: Object.keys(updates)
                });
                window.livePreview.updateElement(this.elementId, updates, { sync: true, debounce: true });
            } else if (window.updateElementPreview) {
                // Fallback to old method
                window.updateElementPreview(this.elementId, updates);

                // When LivePreviewManager is not available, we need to manually apply hover styles
                const elementWrapper = document.querySelector(`.element-wrapper[data-element-id="${this.elementId}"]`);
                console.log('[BackgroundEditor] No LivePreviewManager - manual hover styles. Wrapper found:', !!elementWrapper);

                if (elementWrapper) {
                    const elementContent = elementWrapper.querySelector('.element-content');
                    const targetElement = elementContent ? (elementContent.firstElementChild || elementContent) : elementWrapper;

                    if (this.backgrounds.hover.enabled && hoverCSS) {
                        this.applyHoverStyles(targetElement, hoverCSS);
                    } else {
                        this.removeHoverStyles(targetElement);
                    }
                }
            } else {
                // Neither LivePreviewManager nor updateElementPreview available - apply hover directly
                console.log('[BackgroundEditor] No preview system available, applying hover styles directly');
                const elementWrapper = document.querySelector(`.element-wrapper[data-element-id="${this.elementId}"]`);
                if (elementWrapper) {
                    const elementContent = elementWrapper.querySelector('.element-content');
                    const targetElement = elementContent ? (elementContent.firstElementChild || elementContent) : elementWrapper;

                    if (this.backgrounds.hover.enabled && hoverCSS) {
                        this.applyHoverStyles(targetElement, hoverCSS);
                    } else {
                        this.removeHoverStyles(targetElement);
                    }
                }
            }
        }

        // Callback - property renderer expects single value
        if (this.options.onApply) {
            this.options.onApply(normalCSS);
        }

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

    /**
     * Apply hover styles by injecting a CSS rule with :hover selector
     * @param {HTMLElement} element - The element to apply hover styles to
     * @param {string} hoverCSS - The CSS background value for hover state
     */
    applyHoverStyles(element, hoverCSS) {
        console.log('[BackgroundEditor] applyHoverStyles called with:', { element, hoverCSS: hoverCSS?.substring(0, 100) + '...' });

        if (!element) {
            console.warn('[BackgroundEditor] applyHoverStyles: No element provided');
            return;
        }
        if (!hoverCSS) {
            console.warn('[BackgroundEditor] applyHoverStyles: No hoverCSS provided');
            return;
        }

        // Ensure element has an ID for CSS targeting
        if (!element.id) {
            element.id = 'bg-' + Math.random().toString(36).substr(2, 9);
            console.log('[BackgroundEditor] Assigned new ID to element:', element.id);
        }

        // Find or create the hover styles container
        let styleEl = document.getElementById('bg-editor-hover-styles');
        if (!styleEl) {
            styleEl = document.createElement('style');
            styleEl.id = 'bg-editor-hover-styles';
            document.head.appendChild(styleEl);
            console.log('[BackgroundEditor] Created new style element for hover styles');
        }

        // Remove existing rule for this element (if any)
        const selector = `#${element.id}`;
        const existingRules = styleEl.textContent || '';
        const ruleRegex = new RegExp(`\\s*${selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}:hover\\s*\\{[^}]*\\}`, 'g');
        styleEl.textContent = existingRules.replace(ruleRegex, '');

        // Add new hover rule
        const rule = `\n${selector}:hover { background: ${hoverCSS} !important; transition: background 0.3s ease; }`;
        styleEl.textContent += rule;

        console.log('[BackgroundEditor] Applied hover styles for', selector, '- Current style content:', styleEl.textContent.substring(0, 200) + '...');
    }

    /**
     * Remove hover styles for an element
     * @param {HTMLElement} element - The element to remove hover styles from
     */
    removeHoverStyles(element) {
        if (!element || !element.id) return;

        const styleEl = document.getElementById('bg-editor-hover-styles');
        if (!styleEl) return;

        const selector = `#${element.id}`;
        const existingRules = styleEl.textContent || '';
        const ruleRegex = new RegExp(`\\s*${selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}:hover\\s*\\{[^}]*\\}`, 'g');
        styleEl.textContent = existingRules.replace(ruleRegex, '');

        console.log('[BackgroundEditor] Removed hover styles for', selector);
    }
}

// Make globally available
window.BackgroundEditor = BackgroundEditor;