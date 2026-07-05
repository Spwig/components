/* Copyright (c) 2025-2026 Spwig. Licensed under AGPL-3.0. */

/**
 * Unit Selector Utility for Page Builder
 *
 * CSS unit selector and converter with calc() support
 */

class UnitSelectorUtility {
    constructor(options = {}) {
        this.options = {
            units: options.units || ['px', '%', 'rem', 'em', 'vw', 'vh', 'auto'],
            calcSupport: options.calcSupport !== false,
            conversionHelper: options.conversionHelper !== false,
            defaultUnit: options.defaultUnit || 'px',
            allowNegative: options.allowNegative || false,
            min: options.min || null,
            max: options.max || null,
            step: options.step || 1,
            onChange: options.onChange || (() => {}),
            translations: options.translations || {}
        };

        this.currentValue = '';
        this.currentUnit = this.options.defaultUnit;
        this.targetInput = null;
        this.container = null;
    }

    attach(inputElement, unitSelectElement = null) {
        this.targetInput = inputElement;

        // Create container
        const container = document.createElement('div');
        container.className = 'unit-selector-container';

        // Move input into container
        inputElement.parentNode.insertBefore(container, inputElement);
        container.appendChild(inputElement);

        // Create or use existing unit selector
        let unitSelect;
        if (unitSelectElement) {
            unitSelect = unitSelectElement;
        } else {
            unitSelect = this.createUnitSelector();
            container.appendChild(unitSelect);
        }

        // Add calc button if supported
        if (this.options.calcSupport) {
            const calcBtn = this.createCalcButton();
            container.appendChild(calcBtn);
        }

        // Add conversion helper if supported
        if (this.options.conversionHelper) {
            const convertBtn = this.createConvertButton();
            container.appendChild(convertBtn);
        }

        this.container = container;
        this.parseInitialValue(inputElement.value);
        this.setupEventHandlers(inputElement, unitSelect);
    }

    createUnitSelector() {
        const select = document.createElement('select');
        select.className = 'unit-selector';

        this.options.units.forEach(unit => {
            const option = document.createElement('option');
            option.value = unit;
            option.textContent = unit === 'auto' ? 'Auto' : unit.toUpperCase();
            if (unit === this.currentUnit) {
                option.selected = true;
            }
            select.appendChild(option);
        });

        return select;
    }

    createCalcButton() {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'unit-calc-btn';
        btn.innerHTML = '<i class="fas fa-calculator"></i>';
        btn.title = this.t('calcExpression');

        btn.addEventListener('click', () => {
            this.openCalcEditor();
        });

        return btn;
    }

    createConvertButton() {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'unit-convert-btn';
        btn.innerHTML = '<i class="fas fa-exchange-alt"></i>';
        btn.title = this.t('convertUnit');

        btn.addEventListener('click', () => {
            this.openConversionHelper();
        });

        return btn;
    }

    setupEventHandlers(input, unitSelect) {
        // Handle input change
        input.addEventListener('input', (e) => {
            this.currentValue = e.target.value;
            this.updateValue();
        });

        // Handle unit change
        unitSelect.addEventListener('change', (e) => {
            this.currentUnit = e.target.value;

            // Handle special units
            if (this.currentUnit === 'auto') {
                input.value = 'auto';
                input.disabled = true;
            } else {
                input.disabled = false;
                if (input.value === 'auto') {
                    input.value = '';
                }
            }

            this.updateValue();
        });

        // Handle arrow keys for increment/decrement
        input.addEventListener('keydown', (e) => {
            if (this.currentUnit === 'auto') return;

            const step = e.shiftKey ? 10 : (e.altKey ? 0.1 : this.options.step);
            let value = parseFloat(input.value) || 0;

            if (e.key === 'ArrowUp') {
                e.preventDefault();
                value += step;
                if (this.options.max !== null && value > this.options.max) {
                    value = this.options.max;
                }
                input.value = this.formatNumber(value);
                this.currentValue = input.value;
                this.updateValue();
            } else if (e.key === 'ArrowDown') {
                e.preventDefault();
                value -= step;
                if (!this.options.allowNegative && value < 0) {
                    value = 0;
                }
                if (this.options.min !== null && value < this.options.min) {
                    value = this.options.min;
                }
                input.value = this.formatNumber(value);
                this.currentValue = input.value;
                this.updateValue();
            }
        });
    }

    parseInitialValue(value) {
        if (!value) {
            this.currentValue = '';
            this.currentUnit = this.options.defaultUnit;
            return;
        }

        // Check for calc() expression
        if (value.startsWith('calc(')) {
            this.currentValue = value;
            this.currentUnit = 'calc';
            return;
        }

        // Check for auto
        if (value === 'auto') {
            this.currentValue = 'auto';
            this.currentUnit = 'auto';
            return;
        }

        // Parse value and unit
        const match = value.match(/^(-?\d*\.?\d+)\s*([a-z%]+)?$/i);
        if (match) {
            this.currentValue = match[1];
            this.currentUnit = match[2] || this.options.defaultUnit;

            // Ensure unit is in our options
            if (!this.options.units.includes(this.currentUnit)) {
                this.currentUnit = this.options.defaultUnit;
            }
        } else {
            this.currentValue = value;
            this.currentUnit = this.options.defaultUnit;
        }
    }

    updateValue() {
        let finalValue = '';

        if (this.currentUnit === 'auto') {
            finalValue = 'auto';
        } else if (this.currentUnit === 'calc' || this.currentValue.startsWith('calc(')) {
            finalValue = this.currentValue;
        } else if (this.currentValue) {
            // Clean the numeric value
            let numValue = parseFloat(this.currentValue);
            if (!isNaN(numValue)) {
                // Apply constraints
                if (!this.options.allowNegative && numValue < 0) {
                    numValue = 0;
                }
                if (this.options.min !== null && numValue < this.options.min) {
                    numValue = this.options.min;
                }
                if (this.options.max !== null && numValue > this.options.max) {
                    numValue = this.options.max;
                }

                finalValue = this.formatNumber(numValue) + this.currentUnit;
            }
        }

        // Update the actual property input (may be hidden)
        if (this.targetInput.dataset.propertyInput) {
            const propertyInput = document.querySelector(this.targetInput.dataset.propertyInput);
            if (propertyInput) {
                propertyInput.value = finalValue;
                propertyInput.dispatchEvent(new Event('input', { bubbles: true }));
                propertyInput.dispatchEvent(new Event('change', { bubbles: true }));
            }
        }

        // Trigger change callback
        this.options.onChange(finalValue, this.currentValue, this.currentUnit);
    }

    formatNumber(value) {
        // Remove trailing zeros and decimal point if not needed
        return parseFloat(value.toFixed(4)).toString();
    }

    openCalcEditor() {
        const modal = document.createElement('div');
        modal.className = 'unit-calc-modal';
        modal.innerHTML = `
            <div class="unit-calc-content">
                <div class="unit-calc-header">
                    <h3>${this.t('calcEditor')}</h3>
                    <button class="unit-calc-close" type="button">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="unit-calc-body">
                    <div class="calc-help">
                        ${this.t('calcHelp')}
                    </div>
                    <textarea class="calc-expression"
                              rows="3"
                              placeholder="calc(100% - 40px)">${this.currentValue.startsWith('calc(') ? this.currentValue : 'calc()'}</textarea>
                    <div class="calc-examples">
                        <strong>${this.t('examples')}:</strong>
                        <ul>
                            <li><code>calc(100% - 40px)</code></li>
                            <li><code>calc(50% + 20px)</code></li>
                            <li><code>calc(100vh - 80px)</code></li>
                            <li><code>calc(2rem + 10px)</code></li>
                        </ul>
                    </div>
                </div>
                <div class="unit-calc-footer">
                    <button class="btn btn-cancel" type="button">${this.t('cancel')}</button>
                    <button class="btn btn-apply" type="button">${this.t('apply')}</button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // Focus textarea and select content
        const textarea = modal.querySelector('.calc-expression');
        textarea.focus();
        textarea.select();

        // Handle close
        modal.querySelector('.unit-calc-close').addEventListener('click', () => {
            modal.remove();
        });

        modal.querySelector('.btn-cancel').addEventListener('click', () => {
            modal.remove();
        });

        // Handle apply
        modal.querySelector('.btn-apply').addEventListener('click', () => {
            const expression = textarea.value.trim();
            if (expression) {
                this.currentValue = expression;
                this.currentUnit = 'calc';
                this.targetInput.value = expression;
                this.updateValue();
            }
            modal.remove();
        });

        // Close on outside click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.remove();
            }
        });
    }

    openConversionHelper() {
        const modal = document.createElement('div');
        modal.className = 'unit-convert-modal';

        // Get current numeric value
        let currentNumericValue = parseFloat(this.currentValue) || 0;
        if (this.currentUnit === 'auto' || this.currentUnit === 'calc') {
            currentNumericValue = 0;
        }

        modal.innerHTML = `
            <div class="unit-convert-content">
                <div class="unit-convert-header">
                    <h3>${this.t('unitConverter')}</h3>
                    <button class="unit-convert-close" type="button">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="unit-convert-body">
                    <div class="convert-current">
                        <label>${this.t('currentValue')}:</label>
                        <div class="convert-value">
                            <input type="number" value="${currentNumericValue}" class="convert-input">
                            <select class="convert-unit">
                                ${this.options.units
                                    .filter(u => u !== 'auto' && u !== 'calc')
                                    .map(unit =>
                                        `<option value="${unit}" ${unit === this.currentUnit ? 'selected' : ''}>${unit.toUpperCase()}</option>`
                                    ).join('')}
                            </select>
                        </div>
                    </div>
                    <div class="convert-arrow">
                        <i class="fas fa-arrow-down"></i>
                    </div>
                    <div class="convert-to">
                        <label>${this.t('convertTo')}:</label>
                        <div class="convert-results">
                            ${this.generateConversions(currentNumericValue, this.currentUnit)}
                        </div>
                    </div>
                    <div class="convert-reference">
                        <strong>${this.t('reference')}:</strong>
                        <ul>
                            <li>1rem = ${this.getRemSize()}px (${this.t('rootFontSize')})</li>
                            <li>1em = ${this.t('parentFontSize')}</li>
                            <li>100vw = ${window.innerWidth}px (${this.t('viewportWidth')})</li>
                            <li>100vh = ${window.innerHeight}px (${this.t('viewportHeight')})</li>
                        </ul>
                    </div>
                </div>
                <div class="unit-convert-footer">
                    <button class="btn btn-close" type="button">${this.t('close')}</button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // Handle value/unit change
        const input = modal.querySelector('.convert-input');
        const unitSelect = modal.querySelector('.convert-unit');
        const resultsDiv = modal.querySelector('.convert-results');

        const updateConversions = () => {
            const value = parseFloat(input.value) || 0;
            const unit = unitSelect.value;
            resultsDiv.innerHTML = this.generateConversions(value, unit);

            // Add click handlers to results
            resultsDiv.querySelectorAll('.conversion-item').forEach(item => {
                item.addEventListener('click', () => {
                    const newValue = item.dataset.value;
                    const newUnit = item.dataset.unit;
                    this.currentValue = newValue;
                    this.currentUnit = newUnit;
                    this.targetInput.value = newValue;

                    // Update unit selector
                    const unitSelector = this.container.querySelector('.unit-selector');
                    if (unitSelector) {
                        unitSelector.value = newUnit;
                    }

                    this.updateValue();
                    modal.remove();
                });
            });
        };

        input.addEventListener('input', updateConversions);
        unitSelect.addEventListener('change', updateConversions);

        // Add click handlers to initial results
        resultsDiv.querySelectorAll('.conversion-item').forEach(item => {
            item.addEventListener('click', () => {
                const newValue = item.dataset.value;
                const newUnit = item.dataset.unit;
                this.currentValue = newValue;
                this.currentUnit = newUnit;
                this.targetInput.value = newValue;

                // Update unit selector
                const unitSelector = this.container.querySelector('.unit-selector');
                if (unitSelector) {
                    unitSelector.value = newUnit;
                }

                this.updateValue();
                modal.remove();
            });
        });

        // Handle close
        modal.querySelector('.unit-convert-close').addEventListener('click', () => {
            modal.remove();
        });

        modal.querySelector('.btn-close').addEventListener('click', () => {
            modal.remove();
        });

        // Close on outside click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.remove();
            }
        });
    }

    generateConversions(value, fromUnit) {
        const conversions = [];
        const units = this.options.units.filter(u => u !== 'auto' && u !== 'calc' && u !== fromUnit);

        units.forEach(toUnit => {
            const converted = this.convert(value, fromUnit, toUnit);
            if (converted !== null) {
                conversions.push(`
                    <div class="conversion-item" data-value="${this.formatNumber(converted)}" data-unit="${toUnit}">
                        <span class="conversion-value">${this.formatNumber(converted)}</span>
                        <span class="conversion-unit">${toUnit.toUpperCase()}</span>
                    </div>
                `);
            }
        });

        return conversions.join('');
    }

    convert(value, fromUnit, toUnit) {
        // This is a simplified conversion - in production you'd want more accurate conversions
        // based on actual element context

        if (fromUnit === toUnit) return value;

        const remSize = this.getRemSize();
        const viewportWidth = window.innerWidth;
        const viewportHeight = window.innerHeight;

        // Convert to pixels first
        let pixels = value;
        switch (fromUnit) {
            case 'px':
                pixels = value;
                break;
            case 'rem':
                pixels = value * remSize;
                break;
            case 'em':
                // Approximate - would need actual parent font size
                pixels = value * 16;
                break;
            case 'vw':
                pixels = (value / 100) * viewportWidth;
                break;
            case 'vh':
                pixels = (value / 100) * viewportHeight;
                break;
            case '%':
                // Can't convert without parent size
                return null;
        }

        // Convert from pixels to target unit
        switch (toUnit) {
            case 'px':
                return pixels;
            case 'rem':
                return pixels / remSize;
            case 'em':
                // Approximate
                return pixels / 16;
            case 'vw':
                return (pixels / viewportWidth) * 100;
            case 'vh':
                return (pixels / viewportHeight) * 100;
            case '%':
                // Can't convert without parent size
                return null;
            default:
                return null;
        }
    }

    getRemSize() {
        return parseFloat(
            getComputedStyle(document.documentElement).fontSize
        ) || 16;
    }

    // Translation helper
    t(key) {
        const translations = {
            calcExpression: 'CSS calc() expression',
            convertUnit: 'Convert unit',
            calcEditor: 'Calc Expression Editor',
            calcHelp: 'Create complex CSS calculations using calc()',
            examples: 'Examples',
            cancel: 'Cancel',
            apply: 'Apply',
            unitConverter: 'Unit Converter',
            currentValue: 'Current Value',
            convertTo: 'Convert To',
            reference: 'Reference Values',
            rootFontSize: 'root font size',
            parentFontSize: 'parent font size',
            viewportWidth: 'viewport width',
            viewportHeight: 'viewport height',
            close: 'Close',
            ...this.options.translations
        };

        return translations[key] || key;
    }

    // Static method to attach to existing inputs
    static autoAttach(selector = '[data-unit-selector]', options = {}) {
        document.querySelectorAll(selector).forEach(input => {
            const unitSelector = new UnitSelectorUtility(options);
            unitSelector.attach(input);
        });
    }
}

// Make globally available
window.UnitSelectorUtility = UnitSelectorUtility;