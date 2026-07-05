/* Copyright (c) 2025-2026 Spwig. Licensed under AGPL-3.0. */

(function () {
    'use strict';

    var configEl = document.getElementById('utilities-translations');
    var translations = configEl ? JSON.parse(configEl.textContent) : {};
    window.UtilitiesTranslations = translations;

    var langEl = document.getElementById('utilities-language');
    window.currentLanguageCode = langEl ? langEl.textContent.trim() : 'en';

    document.addEventListener('DOMContentLoaded', function () {
        document.querySelectorAll('[data-utility="color-picker"]').forEach(function (element) {
            var input = element.querySelector('input');
            if (input && typeof ColorPickerUtility !== 'undefined') {
                var colorPicker = new ColorPickerUtility({
                    showOpacity: element.dataset.showOpacity !== 'false',
                    showSwatches: element.dataset.showSwatches !== 'false',
                    showRecent: element.dataset.showRecent !== 'false',
                    translations: window.UtilitiesTranslations.colorPicker
                });
                colorPicker.attach(input, input.value);
            }
        });

        document.querySelectorAll('[data-utility="unit-selector"]').forEach(function (element) {
            var input = element.querySelector('input');
            if (input && typeof UnitSelectorUtility !== 'undefined') {
                var unitSelector = new UnitSelectorUtility({
                    translations: window.UtilitiesTranslations.unitSelector
                });
                unitSelector.attach(input);
            }
        });
    });
})();
