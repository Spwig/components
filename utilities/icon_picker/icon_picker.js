/* Copyright (c) 2025-2026 Spwig. Licensed under AGPL-3.0. */

/**
 * Icon Picker Utility for Page Builder
 *
 * Provides a rich icon selection interface within the page builder
 * properties panel. Renders an inline preview + browse button that
 * opens a full modal with ~550 categorized Font Awesome icons.
 *
 * Follows the standard utility interface:
 *   constructor(options) → attach(input, value)
 *
 * Registry data loaded from <script#icon-picker-registry> embedded
 * in visual_builder.html by the Django view.
 *
 * Ports modal UI from core/static/core/admin/js/icon_picker.js.
 */

class IconPickerUtility {
    constructor(options = {}) {
        this.options = {
            propertyKey: options.propertyKey,
            elementId: options.elementId,
            elementType: options.elementType,
            onChange: options.onChange || (() => {}),
            onApply: options.onApply || (() => {}),
            composeFullClass: options.composeFullClass || false,
        };

        this.registry = null;
        this.targetInput = null;
        this.selectedValue = '';
        this._storedPrefix = 'fas';
        this.modal = null;
        this.modalSearch = null;
        this.modalGrid = null;
        this.modalCount = null;
        this.activeCategory = 'all';

        // Inline widget DOM refs
        this.previewIcon = null;
        this.previewLabel = null;
        this.clearBtn = null;

        // Style map: FA prefix → icon_style select value
        this.styleMap = {
            fas: 'solid',
            far: 'regular',
            fal: 'light',
            fad: 'duotone',
            fab: 'brands',
        };
        this.reverseStyleMap = {
            solid: 'fas',
            regular: 'far',
            light: 'fal',
            duotone: 'fad',
            brands: 'fab',
        };
    }

    /**
     * Attach the utility to an input element.
     * Called by PropertyRenderer.initializeUtilities().
     */
    attach(inputElement, initialValue = '') {
        this.targetInput = inputElement;

        var rawValue = initialValue || inputElement.value || '';

        // In composeFullClass mode, parse "fas fa-lock" → prefix + bare class
        if (this.options.composeFullClass && rawValue) {
            var parsed = this._parseComposedClass(rawValue);
            this._storedPrefix = parsed.prefix;
            this.selectedValue = parsed.bareClass;
        } else {
            this.selectedValue = rawValue;
        }

        // Load icon registry from embedded JSON
        this._loadRegistry();

        // Build the inline widget
        this._buildInlineWidget(inputElement);
    }

    // ── Registry ──

    _loadRegistry() {
        var scriptTag = document.getElementById('icon-picker-registry');
        if (scriptTag) {
            try {
                this.registry = JSON.parse(scriptTag.textContent);
            } catch (e) {
                console.warn('[IconPickerUtility] Failed to parse registry:', e);
            }
        }
        if (!this.registry) {
            this.registry = { categories: {}, icons: [] };
        }
    }

    // ── Inline Widget ──

    _buildInlineWidget(inputElement) {
        // Hide the text input
        inputElement.type = 'hidden';

        var wrapper = inputElement.parentNode;

        // Build inline preview container
        var container = document.createElement('div');
        container.className = 'pb-icon-picker-inline';

        // Preview area: icon + label
        var preview = document.createElement('div');
        preview.className = 'pb-icon-picker-preview';

        var previewIcon = document.createElement('div');
        previewIcon.className = 'pb-icon-picker-preview-icon';
        this.previewIcon = previewIcon;

        var previewLabel = document.createElement('span');
        previewLabel.className = 'pb-icon-picker-preview-label';
        this.previewLabel = previewLabel;

        preview.appendChild(previewIcon);
        preview.appendChild(previewLabel);

        // Action buttons
        var actions = document.createElement('div');
        actions.className = 'pb-icon-picker-actions';

        // Browse button
        var browseBtn = document.createElement('button');
        browseBtn.type = 'button';
        browseBtn.className = 'pb-icon-picker-browse';
        browseBtn.innerHTML = '<i class="fas fa-icons"></i> Browse';
        browseBtn.addEventListener('click', () => this._openModal());
        actions.appendChild(browseBtn);

        // Clear button
        var clearBtn = document.createElement('button');
        clearBtn.type = 'button';
        clearBtn.className = 'pb-icon-picker-clear';
        clearBtn.innerHTML = '<i class="fas fa-times"></i>';
        clearBtn.title = 'Clear';
        clearBtn.addEventListener('click', () => this._clearSelection());
        this.clearBtn = clearBtn;
        actions.appendChild(clearBtn);

        container.appendChild(preview);
        container.appendChild(actions);
        wrapper.appendChild(container);

        // Set initial state
        if (this.selectedValue) {
            this._updatePreview(this.selectedValue);
        } else {
            this._showEmptyState();
        }
    }

    _updatePreview(iconClass) {
        if (!iconClass) {
            this._showEmptyState();
            return;
        }

        // Determine the FA style and build full class for display
        var iconStyle = this._getCurrentIconStyle();
        var displayClass = iconClass;
        var fullClass = iconStyle + ' ' + iconClass;

        // In composeFullClass mode, selectedValue is bare class but we display it nicely
        if (this.options.composeFullClass && this.styleMap[iconClass.split(/\s+/)[0]]) {
            // Value passed might be composed — parse it
            var parsed = this._parseComposedClass(iconClass);
            fullClass = parsed.prefix + ' ' + parsed.bareClass;
            displayClass = parsed.bareClass;
        }

        this.previewIcon.innerHTML = '<i class="' + fullClass + '"></i>';
        this.previewLabel.textContent = displayClass;
        this.clearBtn.hidden = false;
    }

    _showEmptyState() {
        this.previewIcon.innerHTML = '<i class="fas fa-icons" style="opacity:0.3"></i>';
        this.previewLabel.textContent = 'No icon selected';
        this.previewLabel.style.opacity = '0.5';
        this.clearBtn.hidden = true;
    }

    _getCompanionStyleSelector() {
        // Derive companion style field name from propertyKey:
        //   "icon"         → "icon_style"
        //   "icon_before"  → "icon_before_style"
        //   "dropdown_icon" → "dropdown_icon_style"
        var key = this.options.propertyKey || 'icon';
        var styleKey = key + '_style';
        return '#prop-' + styleKey + ', [name="' + styleKey + '"]';
    }

    _getCurrentIconStyle() {
        // In composeFullClass mode, use the stored prefix (no companion select)
        if (this.options.composeFullClass) {
            return this._storedPrefix || 'fas';
        }
        // Read the current style from the companion select
        var form = this.targetInput.closest('.property-fields, .element-properties-form, [data-element-id]');
        if (form) {
            var styleSelect = form.querySelector(this._getCompanionStyleSelector());
            if (styleSelect && styleSelect.value) {
                return this.reverseStyleMap[styleSelect.value] || 'fas';
            }
        }
        return 'fas';
    }

    /**
     * Parse a composed FA class string into prefix and bare class.
     * "fas fa-lock" → { prefix: 'fas', bareClass: 'fa-lock' }
     * "fa-lock"     → { prefix: 'fas', bareClass: 'fa-lock' }
     */
    _parseComposedClass(value) {
        var parts = (value || '').trim().split(/\s+/);
        if (parts.length >= 2 && this.styleMap[parts[0]]) {
            return { prefix: parts[0], bareClass: parts.slice(1).join(' ') };
        }
        // Single class or no known prefix — assume fas
        return { prefix: 'fas', bareClass: value };
    }

    // ── Selection ──

    _selectIcon(iconClass, iconStyle, iconLabel) {
        this.selectedValue = iconClass;

        // Update inline preview
        this.previewIcon.innerHTML = '<i class="' + iconStyle + ' ' + iconClass + '"></i>';
        this.previewLabel.textContent = iconLabel || iconClass;
        this.previewLabel.style.opacity = '1';
        this.clearBtn.hidden = false;

        if (this.options.composeFullClass) {
            // Store composed class (e.g., "fas fa-lock") in a single field
            this._storedPrefix = iconStyle;
            var composed = iconStyle + ' ' + iconClass;
            this.targetInput.value = composed;
            this.options.onChange(composed);
            this.options.onApply(composed);
        } else {
            // Standard mode: store bare class, update companion style select
            this.targetInput.value = iconClass;
            this._updateIconStyleField(iconStyle);
            this.options.onChange(iconClass);
            this.options.onApply(iconClass);
        }

        // Dispatch standard change event
        this.targetInput.dispatchEvent(new Event('change', { bubbles: true }));
    }

    _clearSelection() {
        this.selectedValue = '';
        this.targetInput.value = '';
        if (this.options.composeFullClass) {
            this._storedPrefix = 'fas';
        }

        this._showEmptyState();

        this.options.onChange('');
        this.options.onApply('');
        this.targetInput.dispatchEvent(new Event('change', { bubbles: true }));
    }

    _updateIconStyleField(faPrefix) {
        var styleValue = this.styleMap[faPrefix] || 'solid';

        var form = this.targetInput.closest('.property-fields, .element-properties-form, [data-element-id]');
        if (!form) return;

        var styleSelect = form.querySelector(this._getCompanionStyleSelector());
        if (styleSelect && styleSelect.value !== styleValue) {
            styleSelect.value = styleValue;
            styleSelect.dispatchEvent(new Event('change', { bubbles: true }));
        }
    }

    // ── Modal ──

    _openModal() {
        if (!this.modal) {
            this._buildModal();
        }

        // Mark current selection
        this._updateModalSelection();

        this.modal.classList.add('active');
        document.body.classList.add('admin-modal-body-locked');

        // Focus search
        var searchInput = this.modalSearch;
        setTimeout(function() {
            if (searchInput) searchInput.focus();
        }, 100);

        // Scroll to selected
        this._scrollToSelected();
    }

    _closeModal() {
        if (!this.modal) return;
        this.modal.classList.remove('active');
        document.body.classList.remove('admin-modal-body-locked');

        // Reset search and category
        if (this.modalSearch) this.modalSearch.value = '';
        this.activeCategory = 'all';

        // Reset category buttons
        var catBtns = this.modal.querySelectorAll('.icon-picker-category-btn');
        for (var i = 0; i < catBtns.length; i++) {
            catBtns[i].classList.toggle('active', catBtns[i].dataset.category === 'all');
        }

        // Re-render with no filter
        this._renderModalIcons('', 'all');
    }

    _buildModal() {
        var self = this;

        // Overlay
        var overlay = document.createElement('div');
        overlay.className = 'admin-modal-overlay pb-icon-picker-modal';

        // Modal container
        var modal = document.createElement('div');
        modal.className = 'admin-modal admin-modal--lg';

        // Header
        var header = document.createElement('div');
        header.className = 'admin-modal-header';

        var title = document.createElement('h3');
        title.className = 'admin-modal-title';
        title.innerHTML = '<i class="fas fa-icons"></i> Choose an Icon';
        header.appendChild(title);

        var closeBtn = document.createElement('button');
        closeBtn.type = 'button';
        closeBtn.className = 'admin-modal-close';
        closeBtn.innerHTML = '<i class="fas fa-times"></i>';
        closeBtn.addEventListener('click', function() { self._closeModal(); });
        header.appendChild(closeBtn);

        modal.appendChild(header);

        // Body
        var body = document.createElement('div');
        body.className = 'admin-modal-body';

        // Toolbar
        var toolbar = document.createElement('div');
        toolbar.className = 'icon-picker-modal-toolbar';

        // Search
        var searchWrap = document.createElement('div');
        searchWrap.className = 'icon-picker-modal-search';
        searchWrap.innerHTML = '<i class="fas fa-search"></i>';

        var searchInput = document.createElement('input');
        searchInput.type = 'text';
        searchInput.placeholder = 'Search icons...';
        searchInput.autocomplete = 'off';
        searchWrap.appendChild(searchInput);
        toolbar.appendChild(searchWrap);
        this.modalSearch = searchInput;

        // Category pills
        var catContainer = document.createElement('div');
        catContainer.className = 'icon-picker-modal-categories';

        // "All" button
        var allBtn = document.createElement('button');
        allBtn.type = 'button';
        allBtn.className = 'icon-picker-category-btn active';
        allBtn.dataset.category = 'all';
        allBtn.textContent = 'All';
        catContainer.appendChild(allBtn);

        // Category buttons from registry
        var categories = this.registry.categories || {};
        var catKeys = Object.keys(categories);
        for (var i = 0; i < catKeys.length; i++) {
            var btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'icon-picker-category-btn';
            btn.dataset.category = catKeys[i];
            btn.textContent = categories[catKeys[i]];
            catContainer.appendChild(btn);
        }
        toolbar.appendChild(catContainer);
        body.appendChild(toolbar);

        // Count
        var countEl = document.createElement('div');
        countEl.className = 'icon-picker-modal-count';
        body.appendChild(countEl);
        this.modalCount = countEl;

        // Grid container
        var grid = document.createElement('div');
        grid.className = 'icon-picker-modal-grid';
        body.appendChild(grid);
        this.modalGrid = grid;

        modal.appendChild(body);
        overlay.appendChild(modal);
        document.body.appendChild(overlay);
        this.modal = overlay;

        // Initial render
        this._renderModalIcons('', 'all');

        // ── Bind modal events ──

        // Overlay click to close
        overlay.addEventListener('click', function(e) {
            if (e.target === overlay) self._closeModal();
        });

        // Escape key
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape' && self.modal && self.modal.classList.contains('active')) {
                self._closeModal();
            }
        });

        // Search with debounce
        var searchTimeout;
        searchInput.addEventListener('input', function() {
            var val = searchInput.value;
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(function() {
                self._renderModalIcons(val, self.activeCategory);
            }, 200);
        });

        // Category filter (event delegation)
        catContainer.addEventListener('click', function(e) {
            var catBtn = e.target.closest('.icon-picker-category-btn');
            if (!catBtn) return;

            var btns = catContainer.querySelectorAll('.icon-picker-category-btn');
            for (var j = 0; j < btns.length; j++) {
                btns[j].classList.remove('active');
            }
            catBtn.classList.add('active');

            self.activeCategory = catBtn.dataset.category;
            self._renderModalIcons(searchInput.value, self.activeCategory);
        });

        // Icon selection in grid (event delegation)
        grid.addEventListener('click', function(e) {
            var item = e.target.closest('.icon-picker-modal-item');
            if (!item) return;

            self._selectIcon(
                item.dataset.iconClass,
                item.dataset.iconStyle,
                item.dataset.iconLabel
            );
            self._closeModal();
        });
    }

    _renderModalIcons(searchTerm, category) {
        var icons = this.registry.icons || [];
        var term = (searchTerm || '').toLowerCase().trim();

        // Filter icons
        var filtered = [];
        for (var i = 0; i < icons.length; i++) {
            var icon = icons[i];
            // Category filter
            if (category !== 'all' && icon.category !== category) continue;
            // Search filter
            if (term) {
                var searchable = icon['class'] + ' ' + icon.label + ' ' +
                    (icon.keywords || []).join(' ');
                if (searchable.toLowerCase().indexOf(term) === -1) continue;
            }
            filtered.push(icon);
        }

        // Build DOM with DocumentFragment for performance
        var fragment = document.createDocumentFragment();

        if (filtered.length === 0) {
            var empty = document.createElement('div');
            empty.className = 'icon-picker-modal-empty';
            empty.textContent = 'No icons found';
            fragment.appendChild(empty);
        } else if (category === 'all' && !term) {
            // Group by category
            var grouped = {};
            var groupOrder = [];
            for (var j = 0; j < filtered.length; j++) {
                var cat = filtered[j].category;
                if (!grouped[cat]) {
                    grouped[cat] = [];
                    groupOrder.push(cat);
                }
                grouped[cat].push(filtered[j]);
            }

            var categories = this.registry.categories || {};
            for (var k = 0; k < groupOrder.length; k++) {
                var catSlug = groupOrder[k];
                var catIcons = grouped[catSlug];

                var heading = document.createElement('div');
                heading.className = 'icon-picker-modal-category-heading';
                heading.textContent = categories[catSlug] || catSlug;
                fragment.appendChild(heading);

                var catGrid = document.createElement('div');
                catGrid.className = 'icon-picker-modal-category-grid';
                for (var m = 0; m < catIcons.length; m++) {
                    catGrid.appendChild(this._createModalIconBtn(catIcons[m]));
                }
                fragment.appendChild(catGrid);
            }
        } else {
            // Flat grid (filtered by category or search)
            var flatGrid = document.createElement('div');
            flatGrid.className = 'icon-picker-modal-category-grid';
            for (var n = 0; n < filtered.length; n++) {
                flatGrid.appendChild(this._createModalIconBtn(filtered[n]));
            }
            fragment.appendChild(flatGrid);
        }

        // Replace grid content
        this.modalGrid.innerHTML = '';
        this.modalGrid.appendChild(fragment);

        // Scroll to top
        this.modalGrid.scrollTop = 0;

        // Update count
        this.modalCount.textContent = filtered.length + ' icons';
    }

    _createModalIconBtn(icon) {
        var btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'icon-picker-modal-item';
        btn.dataset.iconClass = icon['class'];
        btn.dataset.iconStyle = icon.style;
        btn.dataset.iconLabel = icon.label;
        btn.title = icon.label;

        // Check if selected
        var bareValue = icon['class'];
        if (this.selectedValue === bareValue) {
            btn.classList.add('selected');
        }

        var iconEl = document.createElement('i');
        iconEl.className = icon.style + ' ' + icon['class'];
        btn.appendChild(iconEl);

        var label = document.createElement('span');
        label.className = 'icon-picker-modal-item-label';
        label.textContent = icon.label;
        btn.appendChild(label);

        return btn;
    }

    _updateModalSelection() {
        if (!this.modalGrid) return;
        var items = this.modalGrid.querySelectorAll('.icon-picker-modal-item');
        for (var i = 0; i < items.length; i++) {
            var bareVal = items[i].dataset.iconClass;
            items[i].classList.toggle('selected', this.selectedValue === bareVal);
        }
    }

    _scrollToSelected() {
        if (!this.selectedValue || !this.modalGrid) return;
        var selectedEl = this.modalGrid.querySelector('.icon-picker-modal-item.selected');
        if (selectedEl) {
            setTimeout(function() {
                selectedEl.scrollIntoView({ block: 'center', behavior: 'smooth' });
            }, 200);
        }
    }
}

// Expose globally for PropertyRenderer utility discovery
window.IconPickerUtility = IconPickerUtility;
