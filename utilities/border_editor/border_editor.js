/* Copyright (c) 2025-2026 Spwig. Licensed under AGPL-3.0. */

/**
 * Border Editor Utility for Page Builder
 *
 * Comprehensive border editor with style, width, color, radius, and corner shape controls
 */

class BorderEditorUtility {
    constructor(options = {}) {
        this.options = {
            standalone: options.standalone || false,
            showPreview: options.showPreview !== false,
            showAdvanced: options.showAdvanced !== false,
            showCornerShape: options.showCornerShape !== false,
            showPresets: options.showPresets !== false,
            allowIndividualSides: options.allowIndividualSides !== false,
            allowIndividualCorners: options.allowIndividualCorners !== false,
            colorPickerIntegration: options.colorPickerIntegration !== false,
            unitSelectorIntegration: options.unitSelectorIntegration !== false,
            onChange: options.onChange || (() => {}),
            onApply: options.onApply || (() => {}),
            translations: options.translations || {}
        };

        this.currentBorder = {
            style: 'solid',
            width: '1',
            widthUnit: 'px',
            color: '#000000',
            radius: '0',
            radiusUnit: 'px',
            cornerShape: 'round',
            // Individual sides
            topWidth: null,
            rightWidth: null,
            bottomWidth: null,
            leftWidth: null,
            // Individual corners
            topLeftRadius: null,
            topRightRadius: null,
            bottomLeftRadius: null,
            bottomRightRadius: null,
            // Linked states
            sidesLinked: true,
            cornersLinked: true
        };

        this.editorElement = null;
        this.targetElement = null;
        this.isOpen = false;
        this.colorPicker = null;
        this.unitSelectors = {};
        this.cornerShapeSupported = this.checkCornerShapeSupport();
    }

    checkCornerShapeSupport() {
        // Check if browser supports corner-shape property
        const testEl = document.createElement('div');
        const supports = 'cornerShape' in testEl.style ||
                        (typeof CSS !== 'undefined' && CSS.supports && CSS.supports('corner-shape', 'round'));

        return supports;
    }

    parseFromLiveElement(wrapper) {
        // Find the target element for this element type
        const elementType = wrapper.dataset.elementType || 'default';
        const elementContent = wrapper.querySelector('.element-content');
        if (!elementContent) return;

        // Try to find the actual target element
        let targetElement = elementContent.firstElementChild || elementContent;

        const styles = window.getComputedStyle(targetElement);

        // Parse border width
        const borderWidth = styles.borderWidth;
        if (borderWidth && borderWidth !== 'medium' && borderWidth !== '0px') {
            const match = borderWidth.match(/^(\d+(?:\.\d+)?)(px|em|rem|%)?/);
            if (match) {
                this.currentBorder.width = match[1];
                this.currentBorder.widthUnit = match[2] || 'px';
            }
        }

        // Parse border style
        if (styles.borderStyle && styles.borderStyle !== 'none') {
            this.currentBorder.style = styles.borderStyle;
        }

        // Parse border color
        if (styles.borderColor) {
            this.currentBorder.color = styles.borderColor;
        }

        // Parse border radius
        const borderRadius = styles.borderRadius;
        if (borderRadius && borderRadius !== '0px') {
            const match = borderRadius.match(/^(\d+(?:\.\d+)?)(px|em|rem|%)?/);
            if (match) {
                this.currentBorder.radius = match[1];
                this.currentBorder.radiusUnit = match[2] || 'px';
            }
        }
    }

    attach(element, currentValue) {
        this.targetElement = element;
        this.targetInput = element.querySelector('input[type="text"], input[type="hidden"]') || element;

        // Get element ID from form if available (page builder context)
        const form = this.targetInput.closest('form');
        if (form && form.dataset.elementId) {
            this.elementId = form.dataset.elementId;

            // Try to get live element styles from canvas
            const liveElement = document.querySelector(`[data-element-id="${this.elementId}"]`);
            if (liveElement) {
                this.parseFromLiveElement(liveElement);
            }
        }

        // Parse initial value if provided (this will override live element styles if present)
        if (currentValue || this.targetInput.value) {
            this.parseInitialValue(currentValue || this.targetInput.value);
        }

        // Only create trigger button if not in standalone mode
        if (!this.options.standalone) {
            // Check if a trigger button already exists (avoid duplicates)
            const existingTrigger = this.targetInput.parentNode ?
                this.targetInput.parentNode.querySelector('.border-editor-trigger') : null;

            if (existingTrigger) {
                // Use existing trigger button
                this.triggerBtn = existingTrigger;
                // Update its content to ensure consistency
                this.triggerBtn.innerHTML = `<i class="fas fa-border-style"></i>`;
            } else {
                // Create trigger button using util-btn styling
                this.triggerBtn = document.createElement('button');
                this.triggerBtn.className = 'util-btn util-btn-primary border-editor-trigger';
                this.triggerBtn.type = 'button';
                this.triggerBtn.title = 'Border Settings';
                this.triggerBtn.innerHTML = `<i class="fas fa-border-style"></i>`;

                // Insert after input
                if (this.targetInput.parentNode) {
                    this.targetInput.parentNode.insertBefore(this.triggerBtn, this.targetInput.nextSibling);
                }
            }

            // Event listener - use arrow function to maintain context
            this.handleTriggerClick = (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.toggle();
            };

            // Remove any existing listener before adding new one
            this.triggerBtn.removeEventListener('click', this.handleTriggerClick);
            this.triggerBtn.addEventListener('click', this.handleTriggerClick);
        }
    }

    toggle() {
        if (this.isOpen) {
            this.close();
        } else {
            this.open();
        }
    }

    open() {
        if (this.isOpen) {
            this.close();
            return;
        }

        this.isOpen = true;
        this.createEditorUI();
        this.positionEditor();

        // Add close handler for clicking outside
        setTimeout(() => {
            document.addEventListener('click', this.handleOutsideClick);
        }, 0);
    }

    close() {
        if (this.editorElement) {
            this.editorElement.remove();
            this.editorElement = null;
        }

        this.isOpen = false;
        document.removeEventListener('click', this.handleOutsideClick);
    }

    handleOutsideClick = (e) => {
        // Don't close if clicking on color picker popup
        if (e.target.closest('.color-picker')) {
            return;
        }

        // Don't close if clicking on color picker trigger button
        if (e.target.closest('.color-picker-trigger')) {
            return;
        }

        // In standalone mode, only check editor element
        if (this.options.standalone) {
            if (this.editorElement && !this.editorElement.contains(e.target)) {
                this.close();
            }
        } else {
            // Normal mode - check both editor and trigger
            if (this.triggerBtn && this.editorElement &&
                !this.editorElement.contains(e.target) &&
                !this.triggerBtn.contains(e.target)) {
                this.close();
            }
        }
    }

    createEditorUI() {
        // Remove existing editor if any
        if (this.editorElement) {
            this.editorElement.remove();
        }

        const editor = document.createElement('div');
        editor.className = 'border-editor-popup utility-popup';
        editor.innerHTML = `
            <div class="utility-header">
                <h3 class="utility-title">${this.t('borderEditor')}</h3>
                <button class="utility-close" type="button" title="${this.t('close')}">
                    <i class="fas fa-times"></i>
                </button>
            </div>

            <div class="utility-body">
                ${this.options.showPreview ? `
                <!-- Preview -->
                <div class="border-preview-container">
                    <div class="border-preview-box" id="border-preview">
                        <span>${this.t('preview')}</span>
                    </div>
                </div>
                ` : ''}

                <!-- Tab Navigation -->
                <div class="admin-tabs">
                    <button class="admin-tab-btn active" data-tab="basic" type="button">
                        <i class="fas fa-th-large"></i>
                        <span>Basic</span>
                    </button>
                    <button class="admin-tab-btn" data-tab="advanced" type="button">
                        <i class="fas fa-sliders-h"></i>
                        <span>Advanced</span>
                    </button>
                </div>

                <!-- Basic Tab Content -->
                <div class="admin-tab-content active" id="tab-basic">

                    <!-- Border Style -->
                <div class="form-group">
                    <label class="form-label">Border Style</label>
                    <select class="form-control">
                        <option value="none">None</option>
                        <option value="solid" selected>Solid</option>
                        <option value="dashed">Dashed</option>
                        <option value="dotted">Dotted</option>
                        <option value="double">Double</option>
                        <option value="groove">Groove</option>
                        <option value="ridge">Ridge</option>
                        <option value="inset">Inset</option>
                        <option value="outset">Outset</option>
                    </select>
                </div>

                <!-- Border Color -->
                <div class="form-group">
                    <label class="form-label">Border Color</label>
                    <div class="border-color-controls">
                        <input type="text" class="form-control"
                               value="${this.currentBorder.color}" data-color-picker>
                        <!-- ColorPickerUtility will inject its trigger button here -->
                    </div>
                </div>

                <!-- Border Width -->
                <div class="form-group">
                    <label class="form-label">
                        Border Width
                        ${this.options.allowIndividualSides ? `
                        <button class="util-btn util-btn-sm link-toggle ${this.currentBorder.sidesLinked ? 'linked' : ''}"
                                data-link-type="sides" type="button" title="Link/Unlink Sides">
                            <i class="fas ${this.currentBorder.sidesLinked ? 'fa-link' : 'fa-unlink'}"></i>
                        </button>
                        ` : ''}
                    </label>
                    ${this.options.allowIndividualSides ? `
                    <div class="border-width-individual">
                        <div class="width-side">
                            <label>Top</label>
                            <input type="number" class="form-control border-width-top" min="0" value="${this.currentBorder.topWidth || this.currentBorder.width}">
                        </div>
                        <div class="width-side">
                            <label>Right</label>
                            <input type="number" class="form-control border-width-right" min="0" value="${this.currentBorder.rightWidth || this.currentBorder.width}">
                        </div>
                        <div class="width-side">
                            <label>Bottom</label>
                            <input type="number" class="form-control border-width-bottom" min="0" value="${this.currentBorder.bottomWidth || this.currentBorder.width}">
                        </div>
                        <div class="width-side">
                            <label>Left</label>
                            <input type="number" class="form-control border-width-left" min="0" value="${this.currentBorder.leftWidth || this.currentBorder.width}">
                        </div>
                    </div>
                    ` : ''}
                </div>



                <!-- Border Radius -->
                <div class="form-group">
                    <label class="form-label">
                        Border Radius
                        ${this.options.allowIndividualCorners ? `
                        <button class="util-btn util-btn-sm link-toggle ${this.currentBorder.cornersLinked ? 'linked' : ''}"
                                data-link-type="corners" type="button" title="Link/Unlink Corners">
                            <i class="fas ${this.currentBorder.cornersLinked ? 'fa-link' : 'fa-unlink'}"></i>
                        </button>
                        ` : ''}
                    </label>
                    ${this.options.allowIndividualCorners ? `
                    <div class="border-radius-individual">
                        <div class="radius-corner">
                            <label>TL</label>
                            <input type="number" class="form-control border-radius-tl" min="0" value="${this.currentBorder.topLeftRadius || this.currentBorder.radius}">
                        </div>
                        <div class="radius-corner">
                            <label>TR</label>
                            <input type="number" class="form-control border-radius-tr" min="0" value="${this.currentBorder.topRightRadius || this.currentBorder.radius}">
                        </div>
                        <div class="radius-corner">
                            <label>BL</label>
                            <input type="number" class="form-control border-radius-bl" min="0" value="${this.currentBorder.bottomLeftRadius || this.currentBorder.radius}">
                        </div>
                        <div class="radius-corner">
                            <label>BR</label>
                            <input type="number" class="form-control border-radius-br" min="0" value="${this.currentBorder.bottomRightRadius || this.currentBorder.radius}">
                        </div>
                    </div>
                    ` : ''}
                </div>

                </div>

                <!-- Advanced Tab Content -->
                <div class="admin-tab-content" id="tab-advanced">
                    ${this.options.allowIndividualCorners ? `
                    <!-- Individual Corner Radius -->
                    <div class="form-group">
                        <label class="form-label">Individual Corners</label>
                        <div class="border-radius-individual">
                            <div class="radius-corner">
                                <label>Top Left</label>
                                <input type="number" class="form-control border-radius-tl-adv" min="0" value="${this.currentBorder.topLeftRadius || this.currentBorder.radius}">
                            </div>
                            <div class="radius-corner">
                                <label>Top Right</label>
                                <input type="number" class="form-control border-radius-tr-adv" min="0" value="${this.currentBorder.topRightRadius || this.currentBorder.radius}">
                            </div>
                            <div class="radius-corner">
                                <label>Bottom Left</label>
                                <input type="number" class="form-control border-radius-bl-adv" min="0" value="${this.currentBorder.bottomLeftRadius || this.currentBorder.radius}">
                            </div>
                            <div class="radius-corner">
                                <label>Bottom Right</label>
                                <input type="number" class="form-control border-radius-br-adv" min="0" value="${this.currentBorder.bottomRightRadius || this.currentBorder.radius}">
                            </div>
                        </div>
                    </div>
                    ` : ''}

                    ${this.options.showCornerShape ? `
                    <!-- Corner Shape (Experimental) -->
                <div class="border-control-group">
                    <label class="border-control-label">
                        Corner Shape
                        <span class="warning-icon" title="Experimental Feature">⚠️</span>
                    </label>
                    ${!this.cornerShapeSupported ? `
                    <div class="compatibility-warning">
                        <i class="fas fa-exclamation-triangle"></i>
                        <span>${this.t('browserCompatibilityWarning')}</span>
                    </div>
                    ` : ''}
                    <div class="corner-shape-controls">
                        <button class="util-btn corner-shape-btn ${this.currentBorder.cornerShape === 'round' ? 'active' : ''}"
                                data-shape="round" type="button" title="Round Corners">
                            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
                                <rect x="2" y="2" width="12" height="12" rx="3" ry="3"/>
                            </svg>
                        </button>
                        <button class="util-btn corner-shape-btn ${this.currentBorder.cornerShape === 'bevel' ? 'active' : ''}"
                                data-shape="bevel" type="button" title="Bevel Corners">
                            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
                                <path d="M 5 2 L 11 2 L 14 5 L 14 11 L 11 14 L 5 14 L 2 11 L 2 5 Z"/>
                            </svg>
                        </button>
                        <button class="util-btn corner-shape-btn ${this.currentBorder.cornerShape === 'scoop' ? 'active' : ''}"
                                data-shape="scoop" type="button" title="Scoop Corners">
                            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
                                <path d="M 2 2 L 2 14 L 14 14 Q 2 14 2 2" stroke-linejoin="miter"/>
                            </svg>
                        </button>
                        <button class="util-btn corner-shape-btn ${this.currentBorder.cornerShape === 'notch' ? 'active' : ''}"
                                data-shape="notch" type="button" title="Notch Corners">
                            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
                                <path d="M 2 2 L 2 14 L 14 14 L 14 9 L 9 9 L 9 4 L 4 4 L 4 2 L 2 2" stroke-linejoin="miter"/>
                            </svg>
                        </button>
                    </div>
                </div>
                ` : ''}

                ${this.options.showPresets ? `
                <!-- Presets -->
                <div class="border-control-group">
                    <label class="border-control-label">${this.t('presets')}</label>
                    <div class="border-presets">
                        <button class="util-btn preset-btn" data-preset="small" type="button" title="Small Radius (4px)">
                            <svg width="20" height="12" viewBox="0 0 20 12" fill="none" stroke="currentColor" stroke-width="1.5">
                                <rect x="1" y="1" width="18" height="10" rx="1" ry="1"/>
                            </svg>
                        </button>
                        <button class="util-btn preset-btn" data-preset="medium" type="button" title="Medium Radius (8px)">
                            <svg width="20" height="12" viewBox="0 0 20 12" fill="none" stroke="currentColor" stroke-width="1.5">
                                <rect x="1" y="1" width="18" height="10" rx="2" ry="2"/>
                            </svg>
                        </button>
                        <button class="util-btn preset-btn" data-preset="large" type="button" title="Large Radius (16px)">
                            <svg width="20" height="12" viewBox="0 0 20 12" fill="none" stroke="currentColor" stroke-width="1.5">
                                <rect x="1" y="1" width="18" height="10" rx="3" ry="3"/>
                            </svg>
                        </button>
                        <button class="util-btn preset-btn" data-preset="rounded" type="button" title="Rounded (24px)">
                            <svg width="20" height="12" viewBox="0 0 20 12" fill="none" stroke="currentColor" stroke-width="1.5">
                                <rect x="1" y="1" width="18" height="10" rx="4" ry="4"/>
                            </svg>
                        </button>
                        <button class="util-btn preset-btn" data-preset="pill" type="button" title="Pill Shape (9999px)">
                            <svg width="20" height="12" viewBox="0 0 20 12" fill="none" stroke="currentColor" stroke-width="1.5">
                                <rect x="1" y="1" width="18" height="10" rx="5" ry="5"/>
                            </svg>
                        </button>
                        <button class="util-btn preset-btn" data-preset="fully-rounded" type="button" title="Fully Rounded (50%)">
                            <svg width="20" height="12" viewBox="0 0 20 12" fill="none" stroke="currentColor" stroke-width="1.5">
                                <ellipse cx="10" cy="6" rx="9" ry="5"/>
                            </svg>
                        </button>
                    </div>
                </div>
                ` : ''}

                <!-- CSS Output -->
                <div class="form-group">
                    <label class="form-label">CSS Output</label>
                    <textarea class="css-output form-control" readonly rows="6">${this.generateCSS()}</textarea>
                </div>
                </div>
            </div>

            <div class="utility-footer">
                <button class="btn btn-clear btn-reset" type="button" title="${this.t('reset')}">
                    <i class="fas fa-undo"></i>
                </button>
                <button class="btn btn-clear btn-cancel" type="button" title="${this.t('cancel')}">
                    <i class="fas fa-times"></i>
                </button>
                <button class="btn btn-apply" type="button" title="${this.t('apply')}">
                    <i class="fas fa-check"></i>
                </button>
            </div>
        `;

        document.body.appendChild(editor);
        this.editorElement = editor;

        // Make popup draggable
        const header = editor.querySelector('.utility-header');
        if (header) {
            this.makeDraggable(editor, header);
        }

        // Initialize event handlers
        this.initializeEventHandlers();

        // Initialize color picker if available
        if (this.options.colorPickerIntegration && window.ColorPickerUtility) {
            this.initializeColorPicker();
        }

        // Initialize unit selectors if available
        if (this.options.unitSelectorIntegration && window.UnitSelectorUtility) {
            this.initializeUnitSelectors();
        }

        // Update preview
        this.updatePreview();
    }

    initializeEventHandlers() {
        // Close button
        this.editorElement.querySelector('.utility-close').addEventListener('click', () => {
            this.close();
        });

        // Cancel button
        const cancelBtn = this.editorElement.querySelector('.btn-cancel');
        if (cancelBtn) cancelBtn.addEventListener('click', () => {
            this.close();
        });

        // Apply button
        const applyBtn = this.editorElement.querySelector('.btn-apply');
        if (applyBtn) applyBtn.addEventListener('click', () => {
            this.applyBorder();
        });

        // Reset button
        const resetBtn = this.editorElement.querySelector('.btn-reset');
        if (resetBtn) resetBtn.addEventListener('click', () => {
            this.resetBorder();
        });

        // Style selector
        const styleSelect = this.editorElement.querySelector('.form-group select');
        if (styleSelect) styleSelect.addEventListener('change', (e) => {
            this.currentBorder.style = e.target.value;
            this.updatePreview();
        });

        // Color input
        const colorInput = this.editorElement.querySelector('.border-color-controls input[type="text"]');
        if (colorInput) colorInput.addEventListener('input', (e) => {
            this.currentBorder.color = e.target.value;
            this.updateColorPreview();
            this.updatePreview();
        });

        // Link/unlink toggles
        this.editorElement.querySelectorAll('.link-toggle').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const linkType = e.currentTarget.dataset.linkType;
                this.toggleLink(linkType);
            });
        });

        // Individual side width inputs
        if (this.options.allowIndividualSides) {
            ['top', 'right', 'bottom', 'left'].forEach(side => {
                const input = this.editorElement.querySelector(`.border-width-${side}`);
                if (input) {
                    input.addEventListener('input', (e) => {
                        const value = e.target.value;
                        this.currentBorder[`${side}Width`] = value;
                        this.currentBorder.width = value; // Update main width

                        // If linked, sync all sides
                        if (this.currentBorder.sidesLinked) {
                            this.updateAllSides('width', value);
                        }
                        this.updatePreview();
                    });
                }
            });
        }

        // Individual corner radius inputs (both basic and advanced tabs)
        if (this.options.allowIndividualCorners) {
            const corners = {
                'tl': 'topLeft',
                'tr': 'topRight',
                'bl': 'bottomLeft',
                'br': 'bottomRight'
            };

            Object.entries(corners).forEach(([short, full]) => {
                // Basic tab corners
                const input = this.editorElement.querySelector(`.border-radius-${short}`);
                if (input) {
                    input.addEventListener('input', (e) => {
                        const value = e.target.value;
                        this.currentBorder[`${full}Radius`] = value;
                        this.currentBorder.radius = value; // Update main radius

                        // If linked, sync all corners
                        if (this.currentBorder.cornersLinked) {
                            this.updateAllCorners('radius', value);
                        }

                        // Sync advanced tab input
                        const advInput = this.editorElement.querySelector(`.border-radius-${short}-adv`);
                        if (advInput) advInput.value = value;

                        this.updatePreview();
                    });
                }

                // Advanced tab corners
                const advInput = this.editorElement.querySelector(`.border-radius-${short}-adv`);
                if (advInput) {
                    advInput.addEventListener('input', (e) => {
                        const value = e.target.value;
                        this.currentBorder[`${full}Radius`] = value;

                        // When editing individual corners, automatically unlink
                        if (this.currentBorder.cornersLinked) {
                            this.currentBorder.cornersLinked = false;
                            // Update the link button UI
                            const linkBtn = this.editorElement.querySelector('[data-link-type="corners"]');
                            if (linkBtn) {
                                linkBtn.classList.remove('linked');
                                const icon = linkBtn.querySelector('i');
                                if (icon) icon.className = 'fas fa-unlink';
                            }
                        }

                        // Sync basic tab input
                        const basicInput = this.editorElement.querySelector(`.border-radius-${short}`);
                        if (basicInput) basicInput.value = value;

                        this.updatePreview();
                    });
                }
            });
        }

        // Corner shape buttons
        if (this.options.showCornerShape) {
            this.editorElement.querySelectorAll('.corner-shape-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const shape = e.currentTarget.dataset.shape;
                    this.setCornerShape(shape);
                });
            });
        }

        // Preset buttons
        if (this.options.showPresets) {
            this.editorElement.querySelectorAll('.preset-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const preset = e.currentTarget.dataset.preset;
                    this.applyPreset(preset);
                });
            });
        }

        // Tab switching
        this.editorElement.querySelectorAll('.admin-tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const tabName = e.currentTarget.dataset.tab;
                this.switchTab(tabName);
            });
        });
    }

    initializeColorPicker() {
        const colorInput = this.editorElement.querySelector('[data-color-picker]');
        if (colorInput) {
            this.colorPicker = new ColorPickerUtility({
                showOpacity: true,
                onChange: (color) => {
                    this.currentBorder.color = color;
                    this.updateColorPreview();
                    this.updatePreview();
                },
                translations: this.options.translations.colorPicker || {}
            });
            this.colorPicker.attach(colorInput, this.currentBorder.color);
        }
    }

    initializeUnitSelectors() {
        // Unit selector integration removed - using simple selects instead
        // This method is kept for compatibility
    }

    switchTab(tabName) {
        if (!this.editorElement) return;

        // Update button states
        this.editorElement.querySelectorAll('.admin-tab-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tabName);
        });

        // Update content visibility
        this.editorElement.querySelectorAll('.admin-tab-content').forEach(content => {
            content.classList.toggle('active', content.id === `tab-${tabName}`);
        });
    }

        toggleLink(linkType) {
        const btn = this.editorElement.querySelector(`[data-link-type="${linkType}"]`);
        const icon = btn.querySelector('i');

        if (linkType === 'sides') {
            this.currentBorder.sidesLinked = !this.currentBorder.sidesLinked;
            btn.classList.toggle('linked');
            icon.className = this.currentBorder.sidesLinked ? 'fas fa-link' : 'fas fa-unlink';

            // Sync values if linking (all 4 inputs are always visible)
            if (this.currentBorder.sidesLinked) {
                this.updateAllSides('width', this.currentBorder.width);
            }
        } else if (linkType === 'corners') {
            this.currentBorder.cornersLinked = !this.currentBorder.cornersLinked;
            btn.classList.toggle('linked');
            icon.className = this.currentBorder.cornersLinked ? 'fas fa-link' : 'fas fa-unlink';

            // Sync values if linking (all 4 inputs are always visible)
            if (this.currentBorder.cornersLinked) {
                this.updateAllCorners('radius', this.currentBorder.radius);
            }
        }

        // No UI recreation needed - inputs are always visible
        this.updatePreview();
    }

    updateAllSides(property, value) {
        ['top', 'right', 'bottom', 'left'].forEach(side => {
            this.currentBorder[`${side}Width`] = value;
            const input = this.editorElement.querySelector(`.border-width-${side}`);
            if (input) {
                input.value = value;
            }
        });
    }

    updateAllCorners(property, value) {
        ['topLeft', 'topRight', 'bottomLeft', 'bottomRight'].forEach(corner => {
            this.currentBorder[`${corner}Radius`] = value;
        });

        // Update inputs if they exist (both basic and advanced tabs)
        const cornerMap = {
            'topLeft': 'tl',
            'topRight': 'tr',
            'bottomLeft': 'bl',
            'bottomRight': 'br'
        };

        Object.entries(cornerMap).forEach(([full, short]) => {
            const basicInput = this.editorElement.querySelector(`.border-radius-${short}`);
            if (basicInput) {
                basicInput.value = value;
            }

            const advInput = this.editorElement.querySelector(`.border-radius-${short}-adv`);
            if (advInput) {
                advInput.value = value;
            }
        });
    }

    setCornerShape(shape) {
        this.currentBorder.cornerShape = shape;

        // Update button states
        this.editorElement.querySelectorAll('.corner-shape-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.shape === shape);
        });

        // If switching to round, explicitly clear cornerShape from preview
        if (shape === 'round') {
            const preview = this.editorElement.querySelector('#border-preview');
            if (preview) {
                preview.style.cornerShape = '';
                preview.style.removeProperty('corner-shape');
            }
        }

        this.updatePreview();
    }

    applyPreset(preset) {
        const presets = {
            small: { radius: '4', radiusUnit: 'px', cornerShape: 'round' },
            medium: { radius: '8', radiusUnit: 'px', cornerShape: 'round' },
            large: { radius: '16', radiusUnit: 'px', cornerShape: 'round' },
            rounded: { radius: '24', radiusUnit: 'px', cornerShape: 'round' },
            pill: { radius: '9999', radiusUnit: 'px', cornerShape: 'round' },
            'fully-rounded': { radius: '50', radiusUnit: '%', cornerShape: 'round' }
        };

        if (presets[preset]) {
            Object.assign(this.currentBorder, presets[preset]);

            // Clear cornerShape from preview since all presets use 'round'
            const preview = this.editorElement.querySelector('#border-preview');
            if (preview) {
                preview.style.cornerShape = '';
                preview.style.removeProperty('corner-shape');
            }

            // Update all corner inputs (both basic and advanced tabs)
            this.updateAllCorners('radius', this.currentBorder.radius);

            // Update controls to reflect new values (including corner shape buttons)
            this.updateAllControls();

            this.updatePreview();
        }
    }

    updateColorPreview() {
        const preview = this.editorElement.querySelector('.border-color-preview .color-fill');
        if (preview) {
            preview.style.backgroundColor = this.currentBorder.color;
        }
    }

    updatePreview() {
        const preview = this.editorElement.querySelector('#border-preview');
        if (!preview) return;

        const css = this.generateCSS();
        const styles = this.generateStyleObject();

        // Clear previous corner-shape if switching to round
        if (this.currentBorder.cornerShape === 'round') {
            preview.style.cornerShape = '';
            preview.style.removeProperty('corner-shape');
        }

        // Apply styles to preview
        Object.entries(styles).forEach(([prop, value]) => {
            preview.style[prop] = value;
        });

        // Update CSS output if shown
        const cssOutput = this.editorElement.querySelector('.css-output');
        if (cssOutput) {
            cssOutput.value = css;
        }

        // Trigger onChange callback
        if (this.options.onChange) {
            this.options.onChange(this.currentBorder, css);
        }
    }

    generateStyleObject() {
        const styles = {};

        // Border style
        if (this.currentBorder.style === 'none') {
            styles.border = 'none';
        } else {
            // Border width
            if (this.currentBorder.sidesLinked) {
                styles.borderWidth = `${this.currentBorder.width}${this.currentBorder.widthUnit}`;
            } else {
                const top = this.currentBorder.topWidth || this.currentBorder.width;
                const right = this.currentBorder.rightWidth || this.currentBorder.width;
                const bottom = this.currentBorder.bottomWidth || this.currentBorder.width;
                const left = this.currentBorder.leftWidth || this.currentBorder.width;
                styles.borderWidth = `${top}${this.currentBorder.widthUnit} ${right}${this.currentBorder.widthUnit} ${bottom}${this.currentBorder.widthUnit} ${left}${this.currentBorder.widthUnit}`;
            }

            styles.borderStyle = this.currentBorder.style;
            styles.borderColor = this.currentBorder.color;
        }

        // Border radius
        if (this.currentBorder.cornersLinked) {
            const radius = `${this.currentBorder.radius}${this.currentBorder.radiusUnit}`;
            styles.borderRadius = radius;
        } else {
            const tl = this.currentBorder.topLeftRadius || this.currentBorder.radius;
            const tr = this.currentBorder.topRightRadius || this.currentBorder.radius;
            const br = this.currentBorder.bottomRightRadius || this.currentBorder.radius;
            const bl = this.currentBorder.bottomLeftRadius || this.currentBorder.radius;
            styles.borderRadius = `${tl}${this.currentBorder.radiusUnit} ${tr}${this.currentBorder.radiusUnit} ${br}${this.currentBorder.radiusUnit} ${bl}${this.currentBorder.radiusUnit}`;
        }

        // Corner shape (experimental)
        if (this.currentBorder.cornerShape !== 'round' && this.cornerShapeSupported) {
            styles.cornerShape = this.currentBorder.cornerShape;
        }

        return styles;
    }

    generateCSS() {
        const styles = this.generateStyleObject();
        let css = '';

        Object.entries(styles).forEach(([prop, value]) => {
            // Convert camelCase to kebab-case
            const cssProp = prop.replace(/([A-Z])/g, '-$1').toLowerCase();
            css += `${cssProp}: ${value};\n`;
        });

        // Add fallback comment for corner-shape
        if (this.currentBorder.cornerShape !== 'round') {
            css += `\n/* Note: corner-shape is experimental and has limited browser support */\n`;

            // Add clip-path fallback for cut corners
            if (this.currentBorder.cornerShape === 'bevel') {
                const radius = `${this.currentBorder.radius}${this.currentBorder.radiusUnit}`;
                css += `/* Fallback using clip-path for unsupported browsers */\n`;
                css += `clip-path: polygon(\n`;
                css += `  ${radius} 0, 100% 0, 100% calc(100% - ${radius}),\n`;
                css += `  calc(100% - ${radius}) 100%, 0 100%, 0 ${radius}\n`;
                css += `);\n`;
            }
        }

        return css.trim();
    }

    applyBorder() {
        const css = this.generateCSS();
        const value = this.formatValue();

        // Update target element
        if (this.targetElement) {
            const input = this.targetElement.querySelector('input') || this.targetElement;
            if (input) {
                input.value = value;
                input.dispatchEvent(new Event('input', { bubbles: true }));
                input.dispatchEvent(new Event('change', { bubbles: true }));
            }
        }

        // Trigger onApply callback
        if (this.options.onApply) {
            this.options.onApply(this.currentBorder, css);
        }

        this.close();
    }

    formatValue() {
        // Format as shorthand CSS value
        if (this.currentBorder.style === 'none') {
            return 'none';
        }

        const width = `${this.currentBorder.width}${this.currentBorder.widthUnit}`;
        const style = this.currentBorder.style;
        const color = this.currentBorder.color;

        return `${width} ${style} ${color}`;
    }

    resetBorder() {
        this.currentBorder = {
            style: 'solid',
            width: '1',
            widthUnit: 'px',
            color: '#000000',
            radius: '0',
            radiusUnit: 'px',
            cornerShape: 'round',
            topWidth: null,
            rightWidth: null,
            bottomWidth: null,
            leftWidth: null,
            topLeftRadius: null,
            topRightRadius: null,
            bottomLeftRadius: null,
            bottomRightRadius: null,
            sidesLinked: true,
            cornersLinked: true
        };

        // Recreate UI to reset all values
        this.createEditorUI();
    }

    parseInitialValue(value) {
        if (!value || typeof value !== 'string') return;

        // Check if it's CSS format (contains semicolons or colons)
        if (value.includes(';') || value.includes(':')) {
            this.parseCSSString(value);
        } else {
            // Parse shorthand: "1px solid #000"
            this.parseShorthand(value);
        }
    }

    parseCSSString(cssString) {
        const lines = cssString.split(';').map(l => l.trim()).filter(l => l);

        lines.forEach(line => {
            const colonIndex = line.indexOf(':');
            if (colonIndex === -1) return;

            const prop = line.substring(0, colonIndex).trim();
            const val = line.substring(colonIndex + 1).trim();

            switch(prop) {
                case 'border-width':
                    const widthMatch = val.match(/^(\d+(?:\.\d+)?)(px|em|rem|%)?/);
                    if (widthMatch) {
                        this.currentBorder.width = widthMatch[1];
                        this.currentBorder.widthUnit = widthMatch[2] || 'px';
                    }
                    break;
                case 'border-style':
                    this.currentBorder.style = val;
                    break;
                case 'border-color':
                    this.currentBorder.color = val;
                    break;
                case 'border-radius':
                    const radiusMatch = val.match(/^(\d+(?:\.\d+)?)(px|em|rem|%)?/);
                    if (radiusMatch) {
                        this.currentBorder.radius = radiusMatch[1];
                        this.currentBorder.radiusUnit = radiusMatch[2] || 'px';
                    }
                    break;
                case 'border':
                    // Handle shorthand border property
                    this.parseShorthand(val);
                    break;
            }
        });
    }

    parseShorthand(value) {
        // Parse CSS border shorthand
        // Format: width style color
        const parts = value.split(' ').filter(p => p);

        if (parts.length === 1 && parts[0] === 'none') {
            this.currentBorder.style = 'none';
            return;
        }

        // Try to parse width
        const widthMatch = parts[0]?.match(/^(\d+(?:\.\d+)?)(px|em|rem|%)?$/);
        if (widthMatch) {
            this.currentBorder.width = widthMatch[1];
            this.currentBorder.widthUnit = widthMatch[2] || 'px';
        }

        // Try to parse style
        const styles = ['solid', 'dashed', 'dotted', 'double', 'groove', 'ridge', 'inset', 'outset'];
        const styleIndex = parts.findIndex(p => styles.includes(p));
        if (styleIndex !== -1) {
            this.currentBorder.style = parts[styleIndex];
        }

        // Try to parse color (last part that looks like a color)
        const colorPart = parts[parts.length - 1];
        if (colorPart && (colorPart.startsWith('#') || colorPart.startsWith('rgb') || colorPart.startsWith('hsl'))) {
            this.currentBorder.color = colorPart;
        }
    }

    setSettings(settings) {
        // Update current border settings with provided settings
        Object.assign(this.currentBorder, settings);

        // If editor is open, update all controls
        if (this.editorElement) {
            this.updateAllControls();
            this.updatePreview();
        }
    }

    updateAllControls() {
        if (!this.editorElement) return;

        // Update style selector
        const styleSelect = this.editorElement.querySelector('.form-group select');
        if (styleSelect) styleSelect.value = this.currentBorder.style;

        // Update color input
        const colorInput = this.editorElement.querySelector('.border-color-controls input[type="text"]');
        if (colorInput) {
            colorInput.value = this.currentBorder.color;
        }

        // Update individual width inputs
        ['top', 'right', 'bottom', 'left'].forEach(side => {
            const input = this.editorElement.querySelector(`.border-width-${side}`);
            if (input) {
                input.value = this.currentBorder[`${side}Width`] || this.currentBorder.width;
            }
        });

        // Update individual corner radius inputs (both tabs)
        const corners = {
            'tl': 'topLeft',
            'tr': 'topRight',
            'bl': 'bottomLeft',
            'br': 'bottomRight'
        };

        Object.entries(corners).forEach(([short, full]) => {
            const value = this.currentBorder[`${full}Radius`] || this.currentBorder.radius;

            const basicInput = this.editorElement.querySelector(`.border-radius-${short}`);
            if (basicInput) basicInput.value = value;

            const advInput = this.editorElement.querySelector(`.border-radius-${short}-adv`);
            if (advInput) advInput.value = value;
        });

        // Update corner shape buttons
        this.editorElement.querySelectorAll('.corner-shape-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.shape === this.currentBorder.cornerShape);
        });

        // Update link buttons
        this.editorElement.querySelectorAll('.link-toggle').forEach(btn => {
            const linkType = btn.dataset.linkType;
            const isLinked = linkType === 'sides' ? this.currentBorder.sidesLinked : this.currentBorder.cornersLinked;
            btn.classList.toggle('active', isLinked);
            const icon = btn.querySelector('i');
            if (icon) {
                icon.className = `fas ${isLinked ? 'fa-link' : 'fa-unlink'}`;
            }
        });
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

    positionEditor() {
        if (!this.editorElement || !this.targetElement) return;

        const targetRect = this.targetElement.getBoundingClientRect();
        const editorRect = this.editorElement.getBoundingClientRect();

        let top = targetRect.bottom + 8;
        let left = targetRect.left;

        // Adjust if goes off screen
        if (top + editorRect.height > window.innerHeight) {
            top = targetRect.top - editorRect.height - 8;
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
    }

    // Note: Translation is handled by Django templates, not in JavaScript
    // This method is kept for compatibility but returns static strings
    t(key) {
        // These are fallback values only - actual translations come from Django templates
        const fallbacks = {
            borderEditor: 'Border Editor',
            editBorder: 'Edit Border',
            preview: 'Preview',
            browserCompatibilityWarning: 'Your browser does not support corner-shape. Using standard border-radius as fallback.',
            ...this.options.translations
        };

        return fallbacks[key] || key;
    }
}

// Make globally available
window.BorderEditorUtility = BorderEditorUtility;