/* Copyright (c) 2025-2026 Spwig. Licensed under AGPL-3.0. */

/**
 * Typography Editor Utility v1.1.0
 * Comprehensive typography control for page builder elements
 *
 * Features:
 * - Font family, size, weight, style
 * - Line height, letter spacing, word spacing
 * - Text decoration and transform
 * - Text alignment and direction
 * - Live preview with comparison
 * - Enhanced font library with proper CSS fallback chains
 */

class TypographyEditor {
    constructor(options = {}) {
        this.options = {
            propertyKey: options.propertyKey,  // Property key for live preview routing (e.g., 'button_typography')
            elementId: options.elementId,
            elementType: options.elementType,
            onChange: options.onChange || (() => {}),
            onApply: options.onApply || (() => {}),
            translations: options.translations || {},
            showEffects: options.showEffects !== false,
            googleFontsApiKey: options.googleFontsApiKey || null
        };

        // Current typography settings
        this.currentSettings = {
            // Font
            fontFamily: 'inherit',
            fontSize: '16px',
            fontWeight: '400',
            fontStyle: 'normal',

            // Spacing
            lineHeight: 'normal',
            letterSpacing: 'normal',
            wordSpacing: 'normal',
            textIndent: '0',

            // Decoration
            textDecoration: 'none',
            textDecorationStyle: 'solid',
            textDecorationColor: 'currentColor',

            // Transform
            textTransform: 'none',
            textAlign: 'left',
            verticalAlign: 'baseline',
            direction: 'ltr',

            // Effects (optional)
            textShadow: 'none',
            color: 'inherit'
        };

        // Store initial settings for reset
        this.initialSettings = {};

        // UI elements
        this.editorElement = null;
        this.targetInput = null;
        this.triggerBtn = null;
        this.isOpen = false;
        this.activeTab = 'font';

        // Web fonts cache
        this.webFonts = this.getDefaultFonts();
        this.loadedFonts = new Set(['Arial', 'Helvetica', 'Times New Roman', 'Georgia', 'Courier New', 'system-ui']);
    }

    getDefaultFonts() {
        return [
            // === SYSTEM FONTS ===

            // System Default Stack
            {
                family: 'system-ui',
                displayName: 'System Default',
                category: 'sans-serif',
                subcategory: 'system',
                source: 'system',
                fallbacks: ['-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'Helvetica Neue', 'Arial', 'sans-serif'],
                weights: [100, 200, 300, 400, 500, 600, 700, 800, 900],
                popularity: 100
            },

            // Sans-Serif System Fonts
            {
                family: 'Arial',
                displayName: 'Arial',
                category: 'sans-serif',
                subcategory: 'neo-grotesque',
                source: 'system',
                fallbacks: ['Helvetica Neue', 'Helvetica', 'sans-serif'],
                weights: [400, 700],
                popularity: 98
            },
            {
                family: 'Helvetica Neue',
                displayName: 'Helvetica Neue',
                category: 'sans-serif',
                subcategory: 'neo-grotesque',
                source: 'system',
                fallbacks: ['Helvetica', 'Arial', 'sans-serif'],
                weights: [100, 200, 300, 400, 500, 600, 700, 800, 900],
                popularity: 95
            },
            {
                family: 'Helvetica',
                displayName: 'Helvetica',
                category: 'sans-serif',
                subcategory: 'neo-grotesque',
                source: 'system',
                fallbacks: ['Arial', 'sans-serif'],
                weights: [300, 400, 700],
                popularity: 94
            },
            {
                family: 'Segoe UI',
                displayName: 'Segoe UI',
                category: 'sans-serif',
                subcategory: 'humanist',
                source: 'system',
                fallbacks: ['Roboto', 'Helvetica Neue', 'Arial', 'sans-serif'],
                weights: [300, 400, 600, 700],
                popularity: 90
            },
            {
                family: 'Roboto',
                displayName: 'Roboto',
                category: 'sans-serif',
                subcategory: 'neo-grotesque',
                source: 'system',
                fallbacks: ['Helvetica Neue', 'Arial', 'sans-serif'],
                weights: [100, 300, 400, 500, 700, 900],
                popularity: 88
            },
            {
                family: 'Ubuntu',
                displayName: 'Ubuntu',
                category: 'sans-serif',
                subcategory: 'humanist',
                source: 'system',
                fallbacks: ['Segoe UI', 'Roboto', 'sans-serif'],
                weights: [300, 400, 500, 700],
                popularity: 75
            },
            {
                family: 'Verdana',
                displayName: 'Verdana',
                category: 'sans-serif',
                subcategory: 'humanist',
                source: 'system',
                fallbacks: ['Geneva', 'Arial', 'sans-serif'],
                weights: [400, 700],
                popularity: 80
            },
            {
                family: 'Tahoma',
                displayName: 'Tahoma',
                category: 'sans-serif',
                subcategory: 'humanist',
                source: 'system',
                fallbacks: ['Verdana', 'Arial', 'sans-serif'],
                weights: [400, 700],
                popularity: 70
            },
            {
                family: 'Trebuchet MS',
                displayName: 'Trebuchet MS',
                category: 'sans-serif',
                subcategory: 'humanist',
                source: 'system',
                fallbacks: ['Verdana', 'Arial', 'sans-serif'],
                weights: [400, 700],
                popularity: 65
            },

            // Serif System Fonts
            {
                family: 'Georgia',
                displayName: 'Georgia',
                category: 'serif',
                subcategory: 'transitional',
                source: 'system',
                fallbacks: ['Times New Roman', 'Times', 'serif'],
                weights: [400, 700],
                popularity: 90
            },
            {
                family: 'Times New Roman',
                displayName: 'Times New Roman',
                category: 'serif',
                subcategory: 'transitional',
                source: 'system',
                fallbacks: ['Times', 'Georgia', 'serif'],
                weights: [400, 700],
                popularity: 85
            },
            {
                family: 'Palatino',
                displayName: 'Palatino',
                category: 'serif',
                subcategory: 'old-style',
                source: 'system',
                fallbacks: ['Palatino Linotype', 'Book Antiqua', 'Georgia', 'serif'],
                weights: [400, 700],
                popularity: 75
            },
            {
                family: 'Book Antiqua',
                displayName: 'Book Antiqua',
                category: 'serif',
                subcategory: 'old-style',
                source: 'system',
                fallbacks: ['Palatino', 'Georgia', 'serif'],
                weights: [400, 700],
                popularity: 70
            },
            {
                family: 'Garamond',
                displayName: 'Garamond',
                category: 'serif',
                subcategory: 'old-style',
                source: 'system',
                fallbacks: ['Georgia', 'Times New Roman', 'serif'],
                weights: [400, 700],
                popularity: 72
            },
            {
                family: 'Cambria',
                displayName: 'Cambria',
                category: 'serif',
                subcategory: 'transitional',
                source: 'system',
                fallbacks: ['Georgia', 'Times New Roman', 'serif'],
                weights: [400, 700],
                popularity: 68
            },

            // Monospace System Fonts
            {
                family: 'Consolas',
                displayName: 'Consolas',
                category: 'monospace',
                subcategory: 'programming',
                source: 'system',
                fallbacks: ['Monaco', 'Menlo', 'Courier New', 'monospace'],
                weights: [400, 700],
                popularity: 90
            },
            {
                family: 'Monaco',
                displayName: 'Monaco',
                category: 'monospace',
                subcategory: 'programming',
                source: 'system',
                fallbacks: ['Consolas', 'Menlo', 'Courier New', 'monospace'],
                weights: [400],
                popularity: 88
            },
            {
                family: 'Menlo',
                displayName: 'Menlo',
                category: 'monospace',
                subcategory: 'programming',
                source: 'system',
                fallbacks: ['Monaco', 'Consolas', 'Courier New', 'monospace'],
                weights: [400, 700],
                popularity: 85
            },
            {
                family: 'Courier New',
                displayName: 'Courier New',
                category: 'monospace',
                subcategory: 'typewriter',
                source: 'system',
                fallbacks: ['Courier', 'monospace'],
                weights: [400, 700],
                popularity: 80
            },
            {
                family: 'SF Mono',
                displayName: 'SF Mono',
                category: 'monospace',
                subcategory: 'programming',
                source: 'system',
                fallbacks: ['Menlo', 'Monaco', 'Consolas', 'monospace'],
                weights: [300, 400, 500, 600, 700],
                popularity: 75
            },

            // Display System Fonts
            {
                family: 'Impact',
                displayName: 'Impact',
                category: 'display',
                subcategory: 'heavy',
                source: 'system',
                fallbacks: ['Haettenschweiler', 'Arial Black', 'sans-serif'],
                weights: [400],
                popularity: 60
            },
            {
                family: 'Arial Black',
                displayName: 'Arial Black',
                category: 'display',
                subcategory: 'heavy',
                source: 'system',
                fallbacks: ['Impact', 'sans-serif'],
                weights: [900],
                popularity: 55
            },

            // === GOOGLE FONTS ===

            // Geometric Sans-Serif Google Fonts
            {
                family: 'Inter',
                displayName: 'Inter',
                category: 'sans-serif',
                subcategory: 'geometric',
                source: 'google',
                fallbacks: ['system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'sans-serif'],
                weights: [100, 200, 300, 400, 500, 600, 700, 800, 900],
                isVariable: true,
                popularity: 99
            },
            {
                family: 'Montserrat',
                displayName: 'Montserrat',
                category: 'sans-serif',
                subcategory: 'geometric',
                source: 'google',
                fallbacks: ['Helvetica Neue', 'Helvetica', 'Arial', 'sans-serif'],
                weights: [100, 200, 300, 400, 500, 600, 700, 800, 900],
                popularity: 97
            },
            {
                family: 'Poppins',
                displayName: 'Poppins',
                category: 'sans-serif',
                subcategory: 'geometric',
                source: 'google',
                fallbacks: ['Montserrat', 'Helvetica Neue', 'sans-serif'],
                weights: [100, 200, 300, 400, 500, 600, 700, 800, 900],
                popularity: 96
            },
            {
                family: 'DM Sans',
                displayName: 'DM Sans',
                category: 'sans-serif',
                subcategory: 'geometric',
                source: 'google',
                fallbacks: ['Inter', 'Helvetica Neue', 'sans-serif'],
                weights: [400, 500, 700],
                popularity: 88
            },
            {
                family: 'Space Grotesk',
                displayName: 'Space Grotesk',
                category: 'sans-serif',
                subcategory: 'geometric',
                source: 'google',
                fallbacks: ['Inter', 'Arial', 'sans-serif'],
                weights: [300, 400, 500, 600, 700],
                popularity: 82
            },
            {
                family: 'Plus Jakarta Sans',
                displayName: 'Plus Jakarta Sans',
                category: 'sans-serif',
                subcategory: 'geometric',
                source: 'google',
                fallbacks: ['Inter', 'Poppins', 'sans-serif'],
                weights: [200, 300, 400, 500, 600, 700, 800],
                popularity: 80
            },
            {
                family: 'Outfit',
                displayName: 'Outfit',
                category: 'sans-serif',
                subcategory: 'geometric',
                source: 'google',
                fallbacks: ['Poppins', 'Montserrat', 'sans-serif'],
                weights: [100, 200, 300, 400, 500, 600, 700, 800, 900],
                popularity: 78
            },
            {
                family: 'Manrope',
                displayName: 'Manrope',
                category: 'sans-serif',
                subcategory: 'geometric',
                source: 'google',
                fallbacks: ['Inter', 'Helvetica Neue', 'sans-serif'],
                weights: [200, 300, 400, 500, 600, 700, 800],
                popularity: 76
            },
            {
                family: 'Figtree',
                displayName: 'Figtree',
                category: 'sans-serif',
                subcategory: 'geometric',
                source: 'google',
                fallbacks: ['Inter', 'Poppins', 'sans-serif'],
                weights: [300, 400, 500, 600, 700, 800, 900],
                popularity: 74
            },
            {
                family: 'Josefin Sans',
                displayName: 'Josefin Sans',
                category: 'sans-serif',
                subcategory: 'geometric',
                source: 'google',
                fallbacks: ['Raleway', 'Montserrat', 'sans-serif'],
                weights: [100, 200, 300, 400, 500, 600, 700],
                popularity: 80
            },

            // Humanist Sans-Serif Google Fonts
            {
                family: 'Open Sans',
                displayName: 'Open Sans',
                category: 'sans-serif',
                subcategory: 'humanist',
                source: 'google',
                fallbacks: ['Segoe UI', 'Helvetica Neue', 'Arial', 'sans-serif'],
                weights: [300, 400, 500, 600, 700, 800],
                popularity: 95
            },
            {
                family: 'Lato',
                displayName: 'Lato',
                category: 'sans-serif',
                subcategory: 'humanist',
                source: 'google',
                fallbacks: ['Helvetica Neue', 'Helvetica', 'Arial', 'sans-serif'],
                weights: [100, 300, 400, 700, 900],
                popularity: 94
            },
            {
                family: 'Nunito',
                displayName: 'Nunito',
                category: 'sans-serif',
                subcategory: 'humanist',
                source: 'google',
                fallbacks: ['Lato', 'Segoe UI', 'sans-serif'],
                weights: [200, 300, 400, 500, 600, 700, 800, 900],
                popularity: 90
            },
            {
                family: 'Nunito Sans',
                displayName: 'Nunito Sans',
                category: 'sans-serif',
                subcategory: 'humanist',
                source: 'google',
                fallbacks: ['Nunito', 'Lato', 'sans-serif'],
                weights: [200, 300, 400, 500, 600, 700, 800, 900],
                popularity: 88
            },
            {
                family: 'Source Sans 3',
                displayName: 'Source Sans 3',
                category: 'sans-serif',
                subcategory: 'humanist',
                source: 'google',
                fallbacks: ['Open Sans', 'Helvetica', 'sans-serif'],
                weights: [200, 300, 400, 500, 600, 700, 800, 900],
                popularity: 85
            },
            {
                family: 'Raleway',
                displayName: 'Raleway',
                category: 'sans-serif',
                subcategory: 'elegant',
                source: 'google',
                fallbacks: ['Montserrat', 'Helvetica Neue', 'sans-serif'],
                weights: [100, 200, 300, 400, 500, 600, 700, 800, 900],
                popularity: 92
            },
            {
                family: 'Rubik',
                displayName: 'Rubik',
                category: 'sans-serif',
                subcategory: 'rounded',
                source: 'google',
                fallbacks: ['Nunito', 'Arial Rounded MT', 'sans-serif'],
                weights: [300, 400, 500, 600, 700, 800, 900],
                popularity: 86
            },
            {
                family: 'Work Sans',
                displayName: 'Work Sans',
                category: 'sans-serif',
                subcategory: 'grotesque',
                source: 'google',
                fallbacks: ['Inter', 'Helvetica Neue', 'sans-serif'],
                weights: [100, 200, 300, 400, 500, 600, 700, 800, 900],
                popularity: 84
            },
            {
                family: 'Mulish',
                displayName: 'Mulish',
                category: 'sans-serif',
                subcategory: 'humanist',
                source: 'google',
                fallbacks: ['Nunito', 'Open Sans', 'sans-serif'],
                weights: [200, 300, 400, 500, 600, 700, 800, 900],
                popularity: 82
            },
            {
                family: 'Cabin',
                displayName: 'Cabin',
                category: 'sans-serif',
                subcategory: 'humanist',
                source: 'google',
                fallbacks: ['Open Sans', 'Lato', 'sans-serif'],
                weights: [400, 500, 600, 700],
                popularity: 75
            },
            {
                family: 'Karla',
                displayName: 'Karla',
                category: 'sans-serif',
                subcategory: 'grotesque',
                source: 'google',
                fallbacks: ['Work Sans', 'Inter', 'sans-serif'],
                weights: [200, 300, 400, 500, 600, 700, 800],
                popularity: 72
            },
            {
                family: 'Barlow',
                displayName: 'Barlow',
                category: 'sans-serif',
                subcategory: 'grotesque',
                source: 'google',
                fallbacks: ['Roboto', 'Helvetica', 'sans-serif'],
                weights: [100, 200, 300, 400, 500, 600, 700, 800, 900],
                popularity: 78
            },
            {
                family: 'Lexend',
                displayName: 'Lexend',
                category: 'sans-serif',
                subcategory: 'readable',
                source: 'google',
                fallbacks: ['Open Sans', 'Helvetica', 'sans-serif'],
                weights: [100, 200, 300, 400, 500, 600, 700, 800, 900],
                popularity: 70
            },

            // Serif Google Fonts
            {
                family: 'Playfair Display',
                displayName: 'Playfair Display',
                category: 'serif',
                subcategory: 'didone',
                source: 'google',
                fallbacks: ['Georgia', 'Times New Roman', 'serif'],
                weights: [400, 500, 600, 700, 800, 900],
                popularity: 95
            },
            {
                family: 'Merriweather',
                displayName: 'Merriweather',
                category: 'serif',
                subcategory: 'transitional',
                source: 'google',
                fallbacks: ['Georgia', 'Times New Roman', 'serif'],
                weights: [300, 400, 700, 900],
                popularity: 93
            },
            {
                family: 'Lora',
                displayName: 'Lora',
                category: 'serif',
                subcategory: 'transitional',
                source: 'google',
                fallbacks: ['Georgia', 'Times New Roman', 'serif'],
                weights: [400, 500, 600, 700],
                popularity: 90
            },
            {
                family: 'Libre Baskerville',
                displayName: 'Libre Baskerville',
                category: 'serif',
                subcategory: 'transitional',
                source: 'google',
                fallbacks: ['Baskerville', 'Georgia', 'serif'],
                weights: [400, 700],
                popularity: 85
            },
            {
                family: 'Cormorant Garamond',
                displayName: 'Cormorant Garamond',
                category: 'serif',
                subcategory: 'old-style',
                source: 'google',
                fallbacks: ['Garamond', 'Georgia', 'serif'],
                weights: [300, 400, 500, 600, 700],
                popularity: 82
            },
            {
                family: 'Source Serif 4',
                displayName: 'Source Serif 4',
                category: 'serif',
                subcategory: 'transitional',
                source: 'google',
                fallbacks: ['Georgia', 'Times New Roman', 'serif'],
                weights: [200, 300, 400, 500, 600, 700, 800, 900],
                popularity: 80
            },
            {
                family: 'EB Garamond',
                displayName: 'EB Garamond',
                category: 'serif',
                subcategory: 'old-style',
                source: 'google',
                fallbacks: ['Garamond', 'Georgia', 'serif'],
                weights: [400, 500, 600, 700, 800],
                popularity: 78
            },
            {
                family: 'Crimson Pro',
                displayName: 'Crimson Pro',
                category: 'serif',
                subcategory: 'old-style',
                source: 'google',
                fallbacks: ['Crimson Text', 'Georgia', 'serif'],
                weights: [200, 300, 400, 500, 600, 700, 800, 900],
                popularity: 75
            },
            {
                family: 'Bitter',
                displayName: 'Bitter',
                category: 'serif',
                subcategory: 'slab',
                source: 'google',
                fallbacks: ['Georgia', 'Times New Roman', 'serif'],
                weights: [100, 200, 300, 400, 500, 600, 700, 800, 900],
                popularity: 76
            },
            {
                family: 'Fraunces',
                displayName: 'Fraunces',
                category: 'serif',
                subcategory: 'old-style',
                source: 'google',
                fallbacks: ['Playfair Display', 'Georgia', 'serif'],
                weights: [100, 200, 300, 400, 500, 600, 700, 800, 900],
                isVariable: true,
                popularity: 72
            },
            {
                family: 'Spectral',
                displayName: 'Spectral',
                category: 'serif',
                subcategory: 'transitional',
                source: 'google',
                fallbacks: ['Georgia', 'Times New Roman', 'serif'],
                weights: [200, 300, 400, 500, 600, 700, 800],
                popularity: 70
            },
            {
                family: 'Cardo',
                displayName: 'Cardo',
                category: 'serif',
                subcategory: 'old-style',
                source: 'google',
                fallbacks: ['EB Garamond', 'Garamond', 'serif'],
                weights: [400, 700],
                popularity: 68
            },
            {
                family: 'Alegreya',
                displayName: 'Alegreya',
                category: 'serif',
                subcategory: 'old-style',
                source: 'google',
                fallbacks: ['Georgia', 'Times New Roman', 'serif'],
                weights: [400, 500, 600, 700, 800, 900],
                popularity: 74
            },

            // Monospace Google Fonts
            {
                family: 'Source Code Pro',
                displayName: 'Source Code Pro',
                category: 'monospace',
                subcategory: 'programming',
                source: 'google',
                fallbacks: ['Consolas', 'Monaco', 'Courier New', 'monospace'],
                weights: [200, 300, 400, 500, 600, 700, 800, 900],
                popularity: 95
            },
            {
                family: 'Fira Code',
                displayName: 'Fira Code',
                category: 'monospace',
                subcategory: 'programming',
                source: 'google',
                fallbacks: ['Source Code Pro', 'Consolas', 'monospace'],
                weights: [300, 400, 500, 600, 700],
                popularity: 92
            },
            {
                family: 'JetBrains Mono',
                displayName: 'JetBrains Mono',
                category: 'monospace',
                subcategory: 'programming',
                source: 'google',
                fallbacks: ['Fira Code', 'Source Code Pro', 'monospace'],
                weights: [100, 200, 300, 400, 500, 600, 700, 800],
                popularity: 88
            },
            {
                family: 'Roboto Mono',
                displayName: 'Roboto Mono',
                category: 'monospace',
                subcategory: 'programming',
                source: 'google',
                fallbacks: ['Source Code Pro', 'Consolas', 'monospace'],
                weights: [100, 200, 300, 400, 500, 600, 700],
                popularity: 85
            },
            {
                family: 'IBM Plex Mono',
                displayName: 'IBM Plex Mono',
                category: 'monospace',
                subcategory: 'programming',
                source: 'google',
                fallbacks: ['Consolas', 'Monaco', 'monospace'],
                weights: [100, 200, 300, 400, 500, 600, 700],
                popularity: 80
            },
            {
                family: 'Space Mono',
                displayName: 'Space Mono',
                category: 'monospace',
                subcategory: 'display',
                source: 'google',
                fallbacks: ['Courier New', 'Courier', 'monospace'],
                weights: [400, 700],
                popularity: 75
            },
            {
                family: 'Inconsolata',
                displayName: 'Inconsolata',
                category: 'monospace',
                subcategory: 'programming',
                source: 'google',
                fallbacks: ['Consolas', 'Monaco', 'monospace'],
                weights: [200, 300, 400, 500, 600, 700, 800, 900],
                popularity: 82
            },

            // Display Google Fonts
            {
                family: 'Oswald',
                displayName: 'Oswald',
                category: 'display',
                subcategory: 'condensed',
                source: 'google',
                fallbacks: ['Impact', 'Arial Black', 'sans-serif'],
                weights: [200, 300, 400, 500, 600, 700],
                popularity: 90
            },
            {
                family: 'Bebas Neue',
                displayName: 'Bebas Neue',
                category: 'display',
                subcategory: 'condensed',
                source: 'google',
                fallbacks: ['Oswald', 'Impact', 'sans-serif'],
                weights: [400],
                popularity: 88
            },
            {
                family: 'Anton',
                displayName: 'Anton',
                category: 'display',
                subcategory: 'heavy',
                source: 'google',
                fallbacks: ['Oswald', 'Impact', 'sans-serif'],
                weights: [400],
                popularity: 85
            },
            {
                family: 'Archivo Black',
                displayName: 'Archivo Black',
                category: 'display',
                subcategory: 'heavy',
                source: 'google',
                fallbacks: ['Arial Black', 'Impact', 'sans-serif'],
                weights: [400],
                popularity: 78
            },
            {
                family: 'Rajdhani',
                displayName: 'Rajdhani',
                category: 'display',
                subcategory: 'tech',
                source: 'google',
                fallbacks: ['Barlow Condensed', 'Arial', 'sans-serif'],
                weights: [300, 400, 500, 600, 700],
                popularity: 75
            },
            {
                family: 'Righteous',
                displayName: 'Righteous',
                category: 'display',
                subcategory: 'retro',
                source: 'google',
                fallbacks: ['Bebas Neue', 'Impact', 'sans-serif'],
                weights: [400],
                popularity: 72
            },
            {
                family: 'Abril Fatface',
                displayName: 'Abril Fatface',
                category: 'display',
                subcategory: 'didone',
                source: 'google',
                fallbacks: ['Playfair Display', 'Georgia', 'serif'],
                weights: [400],
                popularity: 80
            },
            {
                family: 'Archivo',
                displayName: 'Archivo',
                category: 'display',
                subcategory: 'grotesque',
                source: 'google',
                fallbacks: ['Roboto', 'Helvetica', 'sans-serif'],
                weights: [100, 200, 300, 400, 500, 600, 700, 800, 900],
                popularity: 76
            }
        ];
    }

    /**
     * Get the full fallback stack for a font family
     * @param {string} fontFamily - The primary font family name
     * @returns {string} - CSS font-family value with fallbacks
     */
    getFontFallbackStack(fontFamily) {
        const font = this.webFonts.find(f => f.family === fontFamily);

        if (!font) {
            // Unknown font - return with generic fallback
            return `'${fontFamily}', sans-serif`;
        }

        // Build the fallback chain
        const stack = [];

        // Add primary font (quote if has spaces or special chars)
        if (fontFamily.includes(' ') || fontFamily.includes('-')) {
            stack.push(`'${fontFamily}'`);
        } else {
            stack.push(fontFamily);
        }

        // Generic font families that shouldn't be quoted
        const genericFamilies = ['serif', 'sans-serif', 'monospace', 'cursive', 'fantasy', 'system-ui'];

        if (font.fallbacks && font.fallbacks.length > 0) {
            font.fallbacks.forEach(fallback => {
                if (genericFamilies.includes(fallback)) {
                    stack.push(fallback);
                } else if (fallback.includes(' ') || fallback.includes('-')) {
                    stack.push(`'${fallback}'`);
                } else {
                    stack.push(fallback);
                }
            });
        } else {
            // Add generic fallback based on category
            stack.push(font.category || 'sans-serif');
        }

        return stack.join(', ');
    }

    attach(element, currentValue) {
        this.targetInput = element.querySelector('input[type="text"], input[type="hidden"]') || element;

        // Parse initial value if provided - this should take priority
        const hasSavedValue = currentValue || this.targetInput.value;
        if (hasSavedValue) {
            this.parseInitialValue(currentValue || this.targetInput.value);
        }

        // Get the element ID from the form if available
        const form = this.targetInput.closest('form');
        if (form && form.dataset.elementId) {
            this.elementId = form.dataset.elementId;
            // Only load element styles if we don't have saved values
            if (!hasSavedValue) {
                this.loadElementStyles();
            }
        }

        // Only create trigger button if not in standalone mode
        if (!this.options.standalone) {
            // Check if a trigger button already exists (avoid duplicates)
            const existingTrigger = this.targetInput.parentNode ?
                this.targetInput.parentNode.querySelector('.typography-editor-trigger') : null;

            if (existingTrigger) {
                // Use existing trigger button
                this.triggerBtn = existingTrigger;
                // Update its content
                this.triggerBtn.innerHTML = `<i class="fas fa-font"></i>`;
            } else {
                // Create trigger button using util-btn styling
                this.triggerBtn = document.createElement('button');
                this.triggerBtn.className = 'util-btn util-btn-primary typography-editor-trigger';
                this.triggerBtn.type = 'button';
                this.triggerBtn.title = 'Typography Settings';
                this.triggerBtn.innerHTML = `<i class="fas fa-font"></i>`;

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

    async open() {
        if (this.isOpen) return;

        this.isOpen = true;

        // Only reload element styles if we don't have saved values
        // Check if the input has a value (saved typography CSS)
        const hasSavedValue = this.targetInput && this.targetInput.value && this.targetInput.value !== 'inherit';
        if (this.elementId && !hasSavedValue) {
            this.loadElementStyles();
        }

        this.initialSettings = { ...this.currentSettings };

        // Create editor popup
        await this.createEditor();
        this.setupEventListeners();
        this.updateAllControls();
        this.updatePreview();
        this.position();

        // Add outside click handler
        setTimeout(() => {
            document.addEventListener('click', this.handleOutsideClick);
        }, 100);
    }

    close() {
        if (!this.isOpen) return;

        this.isOpen = false;

        if (this.editorElement) {
            this.editorElement.remove();
            this.editorElement = null;
        }

        // Clean up drag event listeners
        if (this.dragCleanup) {
            this.dragCleanup();
            this.dragCleanup = null;
        }

        document.removeEventListener('click', this.handleOutsideClick);
    }

    handleOutsideClick = (e) => {
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

    /**
     * Build the font dropdown HTML with organized categories
     */
    buildFontDropdownHTML() {
        const t = (key) => this.options.translations[key] || key;

        // Group fonts by source
        const systemFonts = this.webFonts.filter(f => f.source === 'system');
        const googleFonts = this.webFonts.filter(f => f.source === 'google');

        // Sort by popularity within each group
        const sortByPopularity = (a, b) => (b.popularity || 0) - (a.popularity || 0);

        // Group by category
        const groupByCategory = (fonts) => ({
            'sans-serif': fonts.filter(f => f.category === 'sans-serif').sort(sortByPopularity),
            'serif': fonts.filter(f => f.category === 'serif').sort(sortByPopularity),
            'monospace': fonts.filter(f => f.category === 'monospace').sort(sortByPopularity),
            'display': fonts.filter(f => f.category === 'display' || f.category === 'cursive').sort(sortByPopularity)
        });

        const systemByCategory = groupByCategory(systemFonts);
        const googleByCategory = groupByCategory(googleFonts);

        const categoryLabels = {
            'sans-serif': t('Sans-Serif'),
            'serif': t('Serif'),
            'monospace': t('Monospace'),
            'display': t('Display')
        };

        let html = '';

        // System Fonts Section
        html += `<div class="font-section-header">${t('System Fonts')}</div>`;

        for (const [category, fonts] of Object.entries(systemByCategory)) {
            if (fonts.length === 0) continue;

            html += `<div class="font-group-label">${categoryLabels[category]}</div>`;

            fonts.forEach(font => {
                const fallbackPreview = font.fallbacks ? font.fallbacks.slice(0, 2).join(', ') : font.category;
                html += `
                    <div class="font-option"
                         data-value="${font.family}"
                         data-source="system"
                         data-category="${font.category}"
                         style="font-family: '${font.family}', ${fallbackPreview}">
                        <span class="font-option-name">${font.displayName || font.family}</span>
                    </div>
                `;
            });
        }

        // Google Fonts Section
        html += `<div class="font-section-header">${t('Google Fonts')}</div>`;

        for (const [category, fonts] of Object.entries(googleByCategory)) {
            if (fonts.length === 0) continue;

            html += `<div class="font-group-label">${categoryLabels[category]}</div>`;

            fonts.forEach(font => {
                const fallbackPreview = font.fallbacks ? font.fallbacks.slice(0, 2).join(', ') : font.category;
                html += `
                    <div class="font-option"
                         data-value="${font.family}"
                         data-source="google"
                         data-category="${font.category}"
                         style="font-family: '${font.family}', ${fallbackPreview}">
                        <span class="font-option-name">${font.displayName || font.family}</span>
                        ${font.isVariable ? '<span class="font-badge variable">Var</span>' : ''}
                    </div>
                `;
            });
        }

        return html;
    }

    async createEditor() {
        const t = (key) => this.options.translations[key] || key;

        this.editorElement = document.createElement('div');
        this.editorElement.className = 'typography-editor-popup utility-popup';
        this.editorElement.innerHTML = `
            <div class="utility-header">
                <h3 class="utility-title">${t('Typography Settings')}</h3>
                <button class="utility-close" type="button" title="${t('Close')}">
                    <i class="fas fa-times"></i>
                </button>
            </div>

            <div class="utility-body">
                <!-- Preview Section -->
                <div class="typography-preview-section">
                    <div class="preview-box">
                        <span class="preview-label">${t('CURRENT')}</span>
                        <div class="preview-text preview-current">
                            The quick brown fox jumps over the lazy dog
                        </div>
                    </div>
                    <i class="fas fa-arrow-right preview-arrow"></i>
                    <div class="preview-box">
                        <span class="preview-label">${t('NEW')}</span>
                        <div class="preview-text preview-new">
                            The quick brown fox jumps over the lazy dog
                        </div>
                    </div>
                </div>

                <!-- Tab Navigation -->
                <div class="admin-tabs">
                    <button class="admin-tab-btn active" data-tab="font">
                        <i class="fas fa-font"></i>
                        ${t('Font')}
                    </button>
                    <button class="admin-tab-btn" data-tab="spacing">
                        <i class="fas fa-text-width"></i>
                        ${t('Spacing')}
                    </button>
                    <button class="admin-tab-btn" data-tab="style">
                        <i class="fas fa-italic"></i>
                        ${t('Style')}
                    </button>
                    <button class="admin-tab-btn" data-tab="transform">
                        <i class="fas fa-align-left"></i>
                        ${t('Transform')}
                    </button>
                </div>

                <!-- Tab Content -->
                <div class="typography-tab-content">
                    <!-- Font Tab -->
                    <div class="tab-pane active" data-tab="font">
                        <div class="control-group">
                            <label>${t('Font Family')}</label>
                            <div class="custom-font-select">
                                <div class="font-select-display" style="font-family: '${this.currentSettings.fontFamily}'">
                                    <span class="font-select-value">${this.currentSettings.fontFamily}</span>
                                    <i class="fas fa-chevron-down font-select-arrow"></i>
                                </div>
                                <select class="font-family-select" style="position: absolute; opacity: 0; pointer-events: none;">
                                    <optgroup label="${t('System Fonts')}">
                                        ${this.webFonts.filter(f => f.source === 'system').map(font =>
                                            `<option value="${font.family}">${font.displayName || font.family}</option>`
                                        ).join('')}
                                    </optgroup>
                                    <optgroup label="${t('Google Fonts')}">
                                        ${this.webFonts.filter(f => f.source === 'google').map(font =>
                                            `<option value="${font.family}">${font.displayName || font.family}</option>`
                                        ).join('')}
                                    </optgroup>
                                </select>
                                <div class="font-dropdown-list" style="display: none;">
                                    <div class="font-search">
                                        <input type="text" class="font-search-input" placeholder="${t('Search fonts...')}">
                                    </div>
                                    ${this.buildFontDropdownHTML()}
                                </div>
                            </div>
                        </div>

                        <div class="control-group">
                            <label>${t('Font Size')}</label>
                            <div class="input-with-unit">
                                <input type="number" class="font-size-input" value="16" min="8" max="120">
                                <select class="font-size-unit">
                                    <option value="px">px</option>
                                    <option value="em">em</option>
                                    <option value="rem">rem</option>
                                    <option value="%">%</option>
                                </select>
                            </div>
                            <input type="range" class="font-size-slider" min="8" max="72" value="16">
                        </div>

                        <div class="control-group">
                            <label>${t('Font Weight')}</label>
                            <select class="font-weight-select">
                                <option value="100">100 - Thin</option>
                                <option value="200">200 - Extra Light</option>
                                <option value="300">300 - Light</option>
                                <option value="400">400 - Normal</option>
                                <option value="500">500 - Medium</option>
                                <option value="600">600 - Semi Bold</option>
                                <option value="700">700 - Bold</option>
                                <option value="800">800 - Extra Bold</option>
                                <option value="900">900 - Black</option>
                            </select>
                            <input type="range" class="font-weight-slider" min="100" max="900" step="100" value="400">
                        </div>

                        <div class="control-group">
                            <label>${t('Font Style')}</label>
                            <div class="button-group">
                                <button class="util-btn style-btn" data-style="normal" title="${t('Normal')}">
                                    <span>Aa</span>
                                </button>
                                <button class="util-btn style-btn" data-style="italic" title="${t('Italic')}">
                                    <span style="font-style: italic">Aa</span>
                                </button>
                                <button class="util-btn style-btn" data-style="oblique" title="${t('Oblique')}">
                                    <span style="font-style: oblique">Aa</span>
                                </button>
                            </div>
                        </div>
                    </div>

                    <!-- Spacing Tab -->
                    <div class="tab-pane" data-tab="spacing">
                        <div class="control-group">
                            <label>${t('Line Height')}</label>
                            <div class="input-with-unit">
                                <input type="number" class="line-height-input" value="1.5" min="0.5" max="5" step="0.1">
                                <select class="line-height-unit">
                                    <option value="">unitless</option>
                                    <option value="px">px</option>
                                    <option value="em">em</option>
                                    <option value="%">%</option>
                                </select>
                            </div>
                            <input type="range" class="line-height-slider" min="0.5" max="3" step="0.1" value="1.5">
                        </div>

                        <div class="control-group">
                            <label>${t('Letter Spacing')}</label>
                            <div class="input-with-unit">
                                <input type="number" class="letter-spacing-input" value="0" min="-5" max="20" step="0.1">
                                <select class="letter-spacing-unit">
                                    <option value="px">px</option>
                                    <option value="em">em</option>
                                </select>
                            </div>
                            <input type="range" class="letter-spacing-slider" min="-2" max="10" step="0.1" value="0">
                        </div>

                        <div class="control-group">
                            <label>${t('Word Spacing')}</label>
                            <div class="input-with-unit">
                                <input type="number" class="word-spacing-input" value="0" min="-10" max="50" step="1">
                                <select class="word-spacing-unit">
                                    <option value="px">px</option>
                                    <option value="em">em</option>
                                </select>
                            </div>
                        </div>

                        <div class="control-group">
                            <label>${t('Text Indent')}</label>
                            <div class="input-with-unit">
                                <input type="number" class="text-indent-input" value="0" min="0" max="100" step="1">
                                <select class="text-indent-unit">
                                    <option value="px">px</option>
                                    <option value="em">em</option>
                                    <option value="%">%</option>
                                </select>
                            </div>
                        </div>
                    </div>

                    <!-- Style Tab -->
                    <div class="tab-pane" data-tab="style">
                        <div class="control-group">
                            <label>${t('Text Decoration')}</label>
                            <div class="button-group decoration-group">
                                <button class="util-btn decoration-btn" data-decoration="none" title="${t('None')}">
                                    <span>Aa</span>
                                </button>
                                <button class="util-btn decoration-btn" data-decoration="underline" title="${t('Underline')}">
                                    <span style="text-decoration: underline">Aa</span>
                                </button>
                                <button class="util-btn decoration-btn" data-decoration="overline" title="${t('Overline')}">
                                    <span style="text-decoration: overline">Aa</span>
                                </button>
                                <button class="util-btn decoration-btn" data-decoration="line-through" title="${t('Strikethrough')}">
                                    <span style="text-decoration: line-through">Aa</span>
                                </button>
                            </div>
                        </div>

                        <div class="control-group decoration-options" style="display: none;">
                            <label>${t('Decoration Style')}</label>
                            <select class="decoration-style-select">
                                <option value="solid">${t('Solid')}</option>
                                <option value="double">${t('Double')}</option>
                                <option value="dotted">${t('Dotted')}</option>
                                <option value="dashed">${t('Dashed')}</option>
                                <option value="wavy">${t('Wavy')}</option>
                            </select>
                        </div>

                        <div class="control-group">
                            <label>${t('Font Variant')}</label>
                            <div class="button-group variant-group">
                                <button class="util-btn variant-btn" data-variant="normal" title="${t('Normal')}">
                                    <span>Aa</span>
                                </button>
                                <button class="util-btn variant-btn" data-variant="small-caps" title="${t('Small Caps')}">
                                    <span style="font-variant: small-caps">Aa</span>
                                </button>
                                <button class="util-btn variant-btn" data-variant="all-small-caps" title="${t('All Small Caps')}">
                                    <span style="font-variant: all-small-caps">AA</span>
                                </button>
                            </div>
                        </div>

                        <div class="control-group">
                            <label>${t('Quick Styles')}</label>
                            <div class="button-group quick-styles">
                                <button class="util-btn quick-style-btn" data-style="bold" title="${t('Bold')}">
                                    <i class="fas fa-bold"></i>
                                </button>
                                <button class="util-btn quick-style-btn" data-style="italic" title="${t('Italic')}">
                                    <i class="fas fa-italic"></i>
                                </button>
                                <button class="util-btn quick-style-btn" data-style="underline" title="${t('Underline')}">
                                    <i class="fas fa-underline"></i>
                                </button>
                                <button class="util-btn quick-style-btn" data-style="strikethrough" title="${t('Strikethrough')}">
                                    <i class="fas fa-strikethrough"></i>
                                </button>
                            </div>
                        </div>
                    </div>

                    <!-- Transform Tab -->
                    <div class="tab-pane" data-tab="transform">
                        <div class="control-group">
                            <label>${t('Text Transform')}</label>
                            <div class="button-group transform-group">
                                <button class="util-btn transform-btn" data-transform="none" title="${t('None')}">
                                    <span>Aa</span>
                                </button>
                                <button class="util-btn transform-btn" data-transform="uppercase" title="${t('Uppercase')}">
                                    <span>AA</span>
                                </button>
                                <button class="util-btn transform-btn" data-transform="lowercase" title="${t('Lowercase')}">
                                    <span>aa</span>
                                </button>
                                <button class="util-btn transform-btn" data-transform="capitalize" title="${t('Capitalize')}">
                                    <span>Aa Bb</span>
                                </button>
                            </div>
                        </div>

                        <div class="control-group">
                            <label>${t('Text Align')}</label>
                            <div class="button-group align-group">
                                <button class="util-btn align-btn" data-align="left" title="${t('Left')}">
                                    <i class="fas fa-align-left"></i>
                                </button>
                                <button class="util-btn align-btn" data-align="center" title="${t('Center')}">
                                    <i class="fas fa-align-center"></i>
                                </button>
                                <button class="util-btn align-btn" data-align="right" title="${t('Right')}">
                                    <i class="fas fa-align-right"></i>
                                </button>
                                <button class="util-btn align-btn" data-align="justify" title="${t('Justify')}">
                                    <i class="fas fa-align-justify"></i>
                                </button>
                            </div>
                        </div>

                        <div class="control-group">
                            <label>${t('Vertical Align')}</label>
                            <select class="vertical-align-select">
                                <option value="baseline">${t('Baseline')}</option>
                                <option value="top">${t('Top')}</option>
                                <option value="middle">${t('Middle')}</option>
                                <option value="bottom">${t('Bottom')}</option>
                                <option value="sub">${t('Subscript')}</option>
                                <option value="super">${t('Superscript')}</option>
                                <option value="text-top">${t('Text Top')}</option>
                                <option value="text-bottom">${t('Text Bottom')}</option>
                            </select>
                        </div>

                        <div class="control-group">
                            <label>${t('Writing Direction')}</label>
                            <div class="button-group direction-group">
                                <button class="util-btn direction-btn" data-direction="ltr" title="${t('Left to Right')}">
                                    <i class="fas fa-arrow-right"></i> LTR
                                </button>
                                <button class="util-btn direction-btn" data-direction="rtl" title="${t('Right to Left')}">
                                    <i class="fas fa-arrow-left"></i> RTL
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="utility-footer">
                <button class="typography-btn typography-btn-clear" type="button">${t('Clear')}</button>
                <button class="typography-btn typography-btn-primary" type="button">${t('Apply')}</button>
            </div>
        `;

        document.body.appendChild(this.editorElement);

        // Make the editor draggable by its header
        const header = this.editorElement.querySelector('.utility-header');
        if (header) {
            this.makeDraggable(this.editorElement, header);
        }
    }

    setupEventListeners() {
        // Header close button
        this.editorElement.querySelector('.utility-close').addEventListener('click', () => {
            this.close();
        });

        // Tab navigation
        this.editorElement.querySelectorAll('.admin-tab-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.switchTab(btn.dataset.tab);
            });
        });

        // Font controls
        this.setupFontControls();

        // Spacing controls
        this.setupSpacingControls();

        // Style controls
        this.setupStyleControls();

        // Transform controls
        this.setupTransformControls();

        // Footer buttons
        const clearBtn = this.editorElement.querySelector('.typography-btn-clear');
        const applyBtn = this.editorElement.querySelector('.typography-btn-primary');

        clearBtn.addEventListener('click', () => {
            this.clearSettings();
        });

        applyBtn.addEventListener('click', () => {
            this.applySettings();
        });
    }

    setupFontControls() {
        const fontSelect = this.editorElement.querySelector('.font-family-select');
        const customFontSelect = this.editorElement.querySelector('.custom-font-select');
        const fontDisplay = this.editorElement.querySelector('.font-select-display');
        const fontDropdown = this.editorElement.querySelector('.font-dropdown-list');
        const fontOptions = this.editorElement.querySelectorAll('.font-option');
        const fontSearchInput = this.editorElement.querySelector('.font-search-input');
        const sizeInput = this.editorElement.querySelector('.font-size-input');
        const sizeUnit = this.editorElement.querySelector('.font-size-unit');
        const sizeSlider = this.editorElement.querySelector('.font-size-slider');
        const weightSelect = this.editorElement.querySelector('.font-weight-select');
        const weightSlider = this.editorElement.querySelector('.font-weight-slider');

        // Custom font dropdown handling
        fontDisplay.addEventListener('click', (e) => {
            e.stopPropagation();
            fontDropdown.style.display = fontDropdown.style.display === 'none' ? 'block' : 'none';
            if (fontDropdown.style.display === 'block') {
                fontSearchInput.focus();
            }
        });

        // Font option selection
        fontOptions.forEach(option => {
            option.addEventListener('click', (e) => {
                e.stopPropagation();
                const value = option.dataset.value;
                this.currentSettings.fontFamily = value;
                fontSelect.value = value; // Update hidden select
                fontDisplay.style.fontFamily = this.getFontFallbackStack(value);
                fontDisplay.querySelector('.font-select-value').textContent = value;
                fontDropdown.style.display = 'none';
                this.loadFontIfNeeded(value);
                this.updatePreview();
                this.notifyChange();
            });
        });

        // Font search
        if (fontSearchInput) {
            fontSearchInput.addEventListener('input', (e) => {
                const searchTerm = e.target.value.toLowerCase();
                // Show/hide font options based on search
                fontOptions.forEach(option => {
                    const fontName = option.textContent.toLowerCase();
                    option.style.display = fontName.includes(searchTerm) ? 'flex' : 'none';
                });
                // Show/hide section headers and group labels
                this.editorElement.querySelectorAll('.font-section-header, .font-group-label').forEach(header => {
                    if (searchTerm) {
                        header.style.display = 'none';
                    } else {
                        header.style.display = 'block';
                    }
                });
            });
        }

        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (!customFontSelect.contains(e.target)) {
                fontDropdown.style.display = 'none';
            }
        });

        // Font size controls
        sizeInput.addEventListener('input', (e) => {
            const unit = sizeUnit.value;
            this.currentSettings.fontSize = e.target.value + unit;
            sizeSlider.value = e.target.value;
            this.updatePreview();
            this.notifyChange();
        });

        sizeSlider.addEventListener('input', (e) => {
            const unit = sizeUnit.value;
            this.currentSettings.fontSize = e.target.value + unit;
            sizeInput.value = e.target.value;
            this.updatePreview();
            this.notifyChange();
        });

        sizeUnit.addEventListener('change', (e) => {
            const value = sizeInput.value;
            this.currentSettings.fontSize = value + e.target.value;
            this.updatePreview();
            this.notifyChange();
        });

        // Font weight controls
        weightSelect.addEventListener('change', (e) => {
            this.currentSettings.fontWeight = e.target.value;
            weightSlider.value = e.target.value;
            this.updatePreview();
            this.notifyChange();
        });

        weightSlider.addEventListener('input', (e) => {
            this.currentSettings.fontWeight = e.target.value;
            weightSelect.value = e.target.value;
            this.updatePreview();
            this.notifyChange();
        });

        // Font style buttons
        this.editorElement.querySelectorAll('.style-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.editorElement.querySelectorAll('.style-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.currentSettings.fontStyle = btn.dataset.style;
                this.updatePreview();
                this.notifyChange();
            });
        });
    }

    setupSpacingControls() {
        // Line height
        const lineHeightInput = this.editorElement.querySelector('.line-height-input');
        const lineHeightUnit = this.editorElement.querySelector('.line-height-unit');
        const lineHeightSlider = this.editorElement.querySelector('.line-height-slider');

        lineHeightInput.addEventListener('input', (e) => {
            const unit = lineHeightUnit.value;
            this.currentSettings.lineHeight = e.target.value + unit;
            lineHeightSlider.value = e.target.value;
            this.updatePreview();
            this.notifyChange();
        });

        lineHeightSlider.addEventListener('input', (e) => {
            const unit = lineHeightUnit.value;
            this.currentSettings.lineHeight = e.target.value + unit;
            lineHeightInput.value = e.target.value;
            this.updatePreview();
            this.notifyChange();
        });

        // Letter spacing
        const letterSpacingInput = this.editorElement.querySelector('.letter-spacing-input');
        const letterSpacingUnit = this.editorElement.querySelector('.letter-spacing-unit');
        const letterSpacingSlider = this.editorElement.querySelector('.letter-spacing-slider');

        letterSpacingInput.addEventListener('input', (e) => {
            const unit = letterSpacingUnit.value;
            this.currentSettings.letterSpacing = e.target.value + unit;
            letterSpacingSlider.value = e.target.value;
            this.updatePreview();
            this.notifyChange();
        });

        letterSpacingSlider.addEventListener('input', (e) => {
            const unit = letterSpacingUnit.value;
            this.currentSettings.letterSpacing = e.target.value + unit;
            letterSpacingInput.value = e.target.value;
            this.updatePreview();
            this.notifyChange();
        });

        // Word spacing
        const wordSpacingInput = this.editorElement.querySelector('.word-spacing-input');
        const wordSpacingUnit = this.editorElement.querySelector('.word-spacing-unit');

        wordSpacingInput.addEventListener('input', (e) => {
            const unit = wordSpacingUnit.value;
            this.currentSettings.wordSpacing = e.target.value + unit;
            this.updatePreview();
            this.notifyChange();
        });

        // Text indent
        const textIndentInput = this.editorElement.querySelector('.text-indent-input');
        const textIndentUnit = this.editorElement.querySelector('.text-indent-unit');

        textIndentInput.addEventListener('input', (e) => {
            const unit = textIndentUnit.value;
            this.currentSettings.textIndent = e.target.value + unit;
            this.updatePreview();
            this.notifyChange();
        });
    }

    setupStyleControls() {
        // Text decoration buttons
        this.editorElement.querySelectorAll('.decoration-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.editorElement.querySelectorAll('.decoration-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.currentSettings.textDecoration = btn.dataset.decoration;

                // Show/hide decoration options
                const decorationOptions = this.editorElement.querySelector('.decoration-options');
                if (btn.dataset.decoration !== 'none') {
                    decorationOptions.style.display = 'block';
                } else {
                    decorationOptions.style.display = 'none';
                }

                this.updatePreview();
                this.notifyChange();
            });
        });

        // Decoration style
        const decorationStyleSelect = this.editorElement.querySelector('.decoration-style-select');
        decorationStyleSelect.addEventListener('change', (e) => {
            this.currentSettings.textDecorationStyle = e.target.value;
            this.updatePreview();
            this.notifyChange();
        });

        // Font variant buttons
        this.editorElement.querySelectorAll('.variant-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.editorElement.querySelectorAll('.variant-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.currentSettings.fontVariant = btn.dataset.variant;
                this.updatePreview();
                this.notifyChange();
            });
        });

        // Quick style toggles
        this.editorElement.querySelectorAll('.quick-style-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                btn.classList.toggle('active');
                const style = btn.dataset.style;

                switch(style) {
                    case 'bold':
                        this.currentSettings.fontWeight = btn.classList.contains('active') ? '700' : '400';
                        this.updateAllControls();
                        break;
                    case 'italic':
                        this.currentSettings.fontStyle = btn.classList.contains('active') ? 'italic' : 'normal';
                        this.updateAllControls();
                        break;
                    case 'underline':
                        this.currentSettings.textDecoration = btn.classList.contains('active') ? 'underline' : 'none';
                        this.updateAllControls();
                        break;
                    case 'strikethrough':
                        this.currentSettings.textDecoration = btn.classList.contains('active') ? 'line-through' : 'none';
                        this.updateAllControls();
                        break;
                }

                this.updatePreview();
                this.notifyChange();
            });
        });
    }

    setupTransformControls() {
        // Text transform buttons
        this.editorElement.querySelectorAll('.transform-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.editorElement.querySelectorAll('.transform-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.currentSettings.textTransform = btn.dataset.transform;
                this.updatePreview();
                this.notifyChange();
            });
        });

        // Text align buttons
        this.editorElement.querySelectorAll('.align-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.editorElement.querySelectorAll('.align-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.currentSettings.textAlign = btn.dataset.align;
                this.updatePreview();
                this.notifyChange();
            });
        });

        // Vertical align
        const verticalAlignSelect = this.editorElement.querySelector('.vertical-align-select');
        verticalAlignSelect.addEventListener('change', (e) => {
            this.currentSettings.verticalAlign = e.target.value;
            this.updatePreview();
            this.notifyChange();
        });

        // Writing direction buttons
        this.editorElement.querySelectorAll('.direction-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.editorElement.querySelectorAll('.direction-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.currentSettings.direction = btn.dataset.direction;
                this.updatePreview();
                this.notifyChange();
            });
        });
    }

    switchTab(tabName) {
        this.activeTab = tabName;

        // Update tab buttons
        this.editorElement.querySelectorAll('.admin-tab-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tabName);
        });

        // Update tab panes
        this.editorElement.querySelectorAll('.tab-pane').forEach(pane => {
            pane.classList.toggle('active', pane.dataset.tab === tabName);
        });
    }

    updateAllControls() {
        // Update all control values based on current settings
        const fontSelect = this.editorElement.querySelector('.font-family-select');
        fontSelect.value = this.currentSettings.fontFamily;

        // Update custom font display
        const fontDisplay = this.editorElement.querySelector('.font-select-display');
        if (fontDisplay) {
            fontDisplay.style.fontFamily = this.getFontFallbackStack(this.currentSettings.fontFamily);
            const fontValueSpan = fontDisplay.querySelector('.font-select-value');
            if (fontValueSpan) {
                fontValueSpan.textContent = this.currentSettings.fontFamily;
            }
        }

        // Parse font size
        const fontSize = parseFloat(this.currentSettings.fontSize);
        const fontSizeUnit = this.currentSettings.fontSize.replace(fontSize, '');
        this.editorElement.querySelector('.font-size-input').value = fontSize;
        this.editorElement.querySelector('.font-size-unit').value = fontSizeUnit || 'px';
        this.editorElement.querySelector('.font-size-slider').value = fontSize;

        // Font weight
        this.editorElement.querySelector('.font-weight-select').value = this.currentSettings.fontWeight;
        this.editorElement.querySelector('.font-weight-slider').value = this.currentSettings.fontWeight;

        // Update button states
        this.updateButtonStates();
    }

    updateButtonStates() {
        // Font style
        this.editorElement.querySelectorAll('.style-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.style === this.currentSettings.fontStyle);
        });

        // Text decoration
        this.editorElement.querySelectorAll('.decoration-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.decoration === this.currentSettings.textDecoration);
        });

        // Font variant
        this.editorElement.querySelectorAll('.variant-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.variant === this.currentSettings.fontVariant);
        });

        // Text transform
        this.editorElement.querySelectorAll('.transform-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.transform === this.currentSettings.textTransform);
        });

        // Text align
        this.editorElement.querySelectorAll('.align-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.align === this.currentSettings.textAlign);
        });

        // Direction
        this.editorElement.querySelectorAll('.direction-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.direction === this.currentSettings.direction);
        });

        // Quick styles
        const quickBold = this.editorElement.querySelector('.quick-style-btn[data-style="bold"]');
        if (quickBold) quickBold.classList.toggle('active', parseInt(this.currentSettings.fontWeight) >= 600);

        const quickItalic = this.editorElement.querySelector('.quick-style-btn[data-style="italic"]');
        if (quickItalic) quickItalic.classList.toggle('active', this.currentSettings.fontStyle === 'italic');

        const quickUnderline = this.editorElement.querySelector('.quick-style-btn[data-style="underline"]');
        if (quickUnderline) quickUnderline.classList.toggle('active', this.currentSettings.textDecoration === 'underline');

        const quickStrike = this.editorElement.querySelector('.quick-style-btn[data-style="strikethrough"]');
        if (quickStrike) quickStrike.classList.toggle('active', this.currentSettings.textDecoration === 'line-through');
    }

    updatePreview() {
        if (!this.editorElement) return;

        const currentPreview = this.editorElement.querySelector('.preview-current');
        const newPreview = this.editorElement.querySelector('.preview-new');

        // Apply background styles if available
        if (this.elementBackground) {
            if (currentPreview) {
                if (this.elementBackground.backgroundColor && this.elementBackground.backgroundColor !== 'rgba(0, 0, 0, 0)') {
                    currentPreview.style.backgroundColor = this.elementBackground.backgroundColor;
                }
                if (this.elementBackground.backgroundImage && this.elementBackground.backgroundImage !== 'none') {
                    currentPreview.style.backgroundImage = this.elementBackground.backgroundImage;
                }
            }
            if (newPreview) {
                if (this.elementBackground.backgroundColor && this.elementBackground.backgroundColor !== 'rgba(0, 0, 0, 0)') {
                    newPreview.style.backgroundColor = this.elementBackground.backgroundColor;
                }
                if (this.elementBackground.backgroundImage && this.elementBackground.backgroundImage !== 'none') {
                    newPreview.style.backgroundImage = this.elementBackground.backgroundImage;
                }
            }
        }

        // Apply initial styles to current preview
        if (currentPreview) {
            Object.assign(currentPreview.style, this.parseCSS(this.initialSettings));
        }

        // Apply new styles to new preview
        if (newPreview) {
            Object.assign(newPreview.style, this.parseCSS(this.currentSettings));
        }

        // Update trigger preview
        if (this.triggerBtn) {
            const triggerPreview = this.triggerBtn.querySelector('.trigger-preview');
            if (triggerPreview) {
                triggerPreview.style.fontFamily = this.getFontFallbackStack(this.currentSettings.fontFamily);
                triggerPreview.style.fontWeight = this.currentSettings.fontWeight;
                triggerPreview.style.fontStyle = this.currentSettings.fontStyle;
            }
        }
    }

    parseCSS(settings) {
        // Convert settings to CSS properties
        return {
            fontFamily: this.getFontFallbackStack(settings.fontFamily),
            fontSize: settings.fontSize,
            fontWeight: settings.fontWeight,
            fontStyle: settings.fontStyle,
            lineHeight: settings.lineHeight,
            letterSpacing: settings.letterSpacing,
            wordSpacing: settings.wordSpacing,
            textIndent: settings.textIndent,
            textDecoration: settings.textDecoration,
            textDecorationStyle: settings.textDecorationStyle,
            textTransform: settings.textTransform,
            textAlign: settings.textAlign,
            verticalAlign: settings.verticalAlign,
            direction: settings.direction,
            fontVariant: settings.fontVariant || 'normal'
        };
    }

    generateCSS() {
        const css = [];

        if (this.currentSettings.fontFamily !== 'inherit') {
            // Use full fallback stack instead of just the font name
            const fontStack = this.getFontFallbackStack(this.currentSettings.fontFamily);
            css.push(`font-family: ${fontStack}`);
        }
        if (this.currentSettings.fontSize !== '16px') {
            css.push(`font-size: ${this.currentSettings.fontSize}`);
        }
        if (this.currentSettings.fontWeight !== '400') {
            css.push(`font-weight: ${this.currentSettings.fontWeight}`);
        }
        if (this.currentSettings.fontStyle !== 'normal') {
            css.push(`font-style: ${this.currentSettings.fontStyle}`);
        }
        if (this.currentSettings.lineHeight !== 'normal') {
            css.push(`line-height: ${this.currentSettings.lineHeight}`);
        }
        if (this.currentSettings.letterSpacing !== 'normal' && this.currentSettings.letterSpacing !== '0px') {
            css.push(`letter-spacing: ${this.currentSettings.letterSpacing}`);
        }
        if (this.currentSettings.wordSpacing !== 'normal' && this.currentSettings.wordSpacing !== '0px') {
            css.push(`word-spacing: ${this.currentSettings.wordSpacing}`);
        }
        if (this.currentSettings.textIndent !== '0' && this.currentSettings.textIndent !== '0px') {
            css.push(`text-indent: ${this.currentSettings.textIndent}`);
        }
        if (this.currentSettings.textDecoration !== 'none') {
            css.push(`text-decoration: ${this.currentSettings.textDecoration} ${this.currentSettings.textDecorationStyle}`);
        }
        if (this.currentSettings.textTransform !== 'none') {
            css.push(`text-transform: ${this.currentSettings.textTransform}`);
        }
        if (this.currentSettings.textAlign !== 'left') {
            css.push(`text-align: ${this.currentSettings.textAlign}`);
        }
        if (this.currentSettings.verticalAlign !== 'baseline') {
            css.push(`vertical-align: ${this.currentSettings.verticalAlign}`);
        }
        if (this.currentSettings.direction !== 'ltr') {
            css.push(`direction: ${this.currentSettings.direction}`);
        }
        if (this.currentSettings.fontVariant && this.currentSettings.fontVariant !== 'normal') {
            css.push(`font-variant: ${this.currentSettings.fontVariant}`);
        }

        return css.join('; ');
    }

    /**
     * Load a Google Font if it's not already loaded
     * Also loads any Google Fonts in the fallback chain
     * @param {string} fontFamily - The font family to load
     */
    loadFontIfNeeded(fontFamily) {
        // Check if font is already loaded
        if (this.loadedFonts.has(fontFamily)) return;

        // Find the font definition
        const font = this.webFonts.find(f => f.family === fontFamily);

        if (font && font.source === 'google') {
            this.loadGoogleFont(font);
        }

        // Also check if any fallback fonts are Google Fonts that need loading
        if (font && font.fallbacks) {
            font.fallbacks.forEach(fallbackName => {
                if (this.loadedFonts.has(fallbackName)) return;

                const fallbackFont = this.webFonts.find(f => f.family === fallbackName);
                if (fallbackFont && fallbackFont.source === 'google') {
                    this.loadGoogleFont(fallbackFont);
                }
            });
        }
    }

    /**
     * Load a single Google Font
     * @param {object} font - Font definition object
     */
    loadGoogleFont(font) {
        if (this.loadedFonts.has(font.family)) return;

        // Build weight parameter
        const weights = font.weights || [400, 700];
        const weightParam = weights.join(';');

        // Build the Google Fonts URL
        const familyParam = font.family.replace(/ /g, '+');

        let url;
        if (font.isVariable) {
            // Variable font loading
            url = `https://fonts.googleapis.com/css2?family=${familyParam}:wght@100..900&display=swap`;
        } else {
            // Regular font loading with specific weights
            url = `https://fonts.googleapis.com/css2?family=${familyParam}:wght@${weightParam}&display=swap`;
        }

        const link = document.createElement('link');
        link.href = url;
        link.rel = 'stylesheet';
        link.setAttribute('data-font', font.family);
        document.head.appendChild(link);

        this.loadedFonts.add(font.family);
    }

    parseInitialValue(value) {
        if (!value || value === 'inherit') return;

        // Try to parse CSS string
        try {
            const styles = value.split(';').map(s => s.trim()).filter(s => s);

            styles.forEach(style => {
                const colonIndex = style.indexOf(':');
                if (colonIndex === -1) return;

                const property = style.substring(0, colonIndex).trim();
                const val = style.substring(colonIndex + 1).trim();

                switch(property) {
                    case 'font-family':
                        // Extract primary font from fallback stack
                        // Split by comma, take first, remove quotes
                        const primaryFont = val.split(',')[0].trim().replace(/['"]/g, '');
                        this.currentSettings.fontFamily = primaryFont;
                        // Load the font if needed
                        this.loadFontIfNeeded(primaryFont);
                        break;
                    case 'font-size':
                        this.currentSettings.fontSize = val;
                        break;
                    case 'font-weight':
                        this.currentSettings.fontWeight = val;
                        break;
                    case 'font-style':
                        this.currentSettings.fontStyle = val;
                        break;
                    case 'line-height':
                        this.currentSettings.lineHeight = val;
                        break;
                    case 'letter-spacing':
                        this.currentSettings.letterSpacing = val;
                        break;
                    case 'word-spacing':
                        this.currentSettings.wordSpacing = val;
                        break;
                    case 'text-indent':
                        this.currentSettings.textIndent = val;
                        break;
                    case 'text-decoration':
                        this.currentSettings.textDecoration = val.split(' ')[0];
                        if (val.split(' ')[1]) {
                            this.currentSettings.textDecorationStyle = val.split(' ')[1];
                        }
                        break;
                    case 'text-transform':
                        this.currentSettings.textTransform = val;
                        break;
                    case 'text-align':
                        this.currentSettings.textAlign = val;
                        break;
                    case 'vertical-align':
                        this.currentSettings.verticalAlign = val;
                        break;
                    case 'direction':
                        this.currentSettings.direction = val;
                        break;
                    case 'font-variant':
                        this.currentSettings.fontVariant = val;
                        break;
                }
            });
        } catch (e) {
            console.warn('Could not parse typography value:', value);
        }
    }

    clearSettings() {
        // Reset to defaults
        this.currentSettings = {
            fontFamily: 'inherit',
            fontSize: '16px',
            fontWeight: '400',
            fontStyle: 'normal',
            lineHeight: 'normal',
            letterSpacing: 'normal',
            wordSpacing: 'normal',
            textIndent: '0',
            textDecoration: 'none',
            textDecorationStyle: 'solid',
            textDecorationColor: 'currentColor',
            textTransform: 'none',
            textAlign: 'left',
            verticalAlign: 'baseline',
            direction: 'ltr',
            textShadow: 'none',
            color: 'inherit'
        };

        this.updateAllControls();
        this.updatePreview();
        this.notifyChange();
    }

    setSettings(settings) {
        // Update current settings with provided settings
        Object.assign(this.currentSettings, settings);

        // Update initial settings to match
        this.initialSettings = { ...this.currentSettings };

        // If editor is open, update all controls
        if (this.editorElement) {
            this.updateAllControls();
            this.updatePreview();
        }
    }

    applySettings() {
        const css = this.generateCSS();

        if (this.targetInput) {
            this.targetInput.value = css;
            this.targetInput.dispatchEvent(new Event('input', { bubbles: true }));
            this.targetInput.dispatchEvent(new Event('change', { bubbles: true }));
        }

        this.options.onApply(css, this.currentSettings);
        this.close();
    }

    notifyChange() {
        const css = this.generateCSS();
        this.options.onChange(css, this.currentSettings);

        // Update the live preview in the builder - Use LivePreviewManager for instant updates
        if (this.elementId) {
            // Create properties object with individual CSS properties for instant updates
            const properties = {};

            // Map typography settings to CSS properties
            const directMappings = {
                fontFamily: 'fontFamily',
                fontSize: 'fontSize',
                fontWeight: 'fontWeight',
                fontStyle: 'fontStyle',
                lineHeight: 'lineHeight',
                letterSpacing: 'letterSpacing',
                wordSpacing: 'wordSpacing',
                textTransform: 'textTransform',
                textAlign: 'textAlign',
                textDecoration: 'textDecoration',
                textDecorationStyle: 'textDecorationStyle',
                textIndent: 'textIndent',
                verticalAlign: 'verticalAlign',
                direction: 'direction',
                color: 'color',
                textShadow: 'textShadow'
            };

            // Add properties that have values
            for (const [jsKey, cssKey] of Object.entries(directMappings)) {
                if (this.currentSettings[jsKey] &&
                    this.currentSettings[jsKey] !== 'inherit' &&
                    this.currentSettings[jsKey] !== 'normal') {
                    // Use fallback stack for fontFamily
                    if (jsKey === 'fontFamily') {
                        properties[cssKey] = this.getFontFallbackStack(this.currentSettings[jsKey]);
                    } else {
                        properties[cssKey] = this.currentSettings[jsKey];
                    }
                }
            }

            if (window.livePreview) {
                // Use propertyKey for element-specific routing (e.g., 'button_typography' routes to button element)
                // If propertyKey is set, send as single property; otherwise send individual CSS properties
                const updates = this.options.propertyKey
                    ? { [this.options.propertyKey]: css }
                    : properties;

                window.livePreview.updateElement(this.elementId, updates, {
                    sync: false  // Visual only, don't sync to server yet
                });
            } else if (window.updateElementPreview) {
                // Fallback to legacy method - map back to element property names
                const legacyProperties = {
                    typography: css  // Store the full CSS string
                };

                // Also include individual mapped properties for backward compatibility
                const legacyMappings = {
                    fontFamily: 'font_family',
                    fontSize: 'size',
                    fontWeight: 'weight',
                    fontStyle: 'font_style',
                    lineHeight: 'line_height',
                    letterSpacing: 'letter_spacing',
                    wordSpacing: 'word_spacing',
                    textTransform: 'text_transform',
                    textAlign: 'align',
                    textDecoration: 'text_decoration',
                    color: 'text_color',
                    textShadow: 'text_shadow'
                };

                for (const [jsKey, propKey] of Object.entries(legacyMappings)) {
                    if (this.currentSettings[jsKey] &&
                        this.currentSettings[jsKey] !== 'inherit' &&
                        this.currentSettings[jsKey] !== 'normal') {
                        legacyProperties[propKey] = this.currentSettings[jsKey];
                    }
                }

                window.updateElementPreview(this.elementId, legacyProperties);
            }
        }
    }

    loadElementStyles() {
        // Try to get the actual element from the builder canvas
        if (!this.elementId) return;

        // Try multiple possible iframe selectors
        const possibleSelectors = [
            '#builder-iframe',
            '.builder-canvas iframe',
            '.page-builder-canvas iframe',
            'iframe[name="builder-frame"]',
            '.builder-preview iframe'
        ];

        let builderFrame = null;
        for (const selector of possibleSelectors) {
            builderFrame = document.querySelector(selector);
            if (builderFrame) break;
        }

        if (builderFrame && builderFrame.contentDocument) {
            const element = builderFrame.contentDocument.querySelector(`[data-component-id="${this.elementId}"], #element-${this.elementId}`);
            if (element) {
                const styles = builderFrame.contentWindow.getComputedStyle(element);

                // Store background styles for preview
                this.elementBackground = {
                    backgroundColor: styles.backgroundColor,
                    backgroundImage: styles.backgroundImage
                };

                // Parse font family (remove quotes and fallbacks for display)
                const fontFamily = styles.fontFamily.split(',')[0].replace(/['"]/g, '').trim();

                // Get typography-related computed styles
                this.currentSettings.fontFamily = fontFamily;
                this.currentSettings.fontSize = styles.fontSize;
                this.currentSettings.fontWeight = styles.fontWeight;
                this.currentSettings.fontStyle = styles.fontStyle;
                this.currentSettings.lineHeight = styles.lineHeight;
                this.currentSettings.letterSpacing = styles.letterSpacing;
                this.currentSettings.wordSpacing = styles.wordSpacing;
                this.currentSettings.textIndent = styles.textIndent;
                this.currentSettings.textDecoration = styles.textDecorationLine || styles.textDecoration;
                this.currentSettings.textTransform = styles.textTransform;
                this.currentSettings.textAlign = styles.textAlign;
                this.currentSettings.verticalAlign = styles.verticalAlign;
                this.currentSettings.direction = styles.direction;
                this.currentSettings.color = styles.color;
                this.currentSettings.textShadow = styles.textShadow;
            }
        }
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

    position() {
        if (!this.editorElement || !this.triggerBtn) return;

        const triggerRect = this.triggerBtn.getBoundingClientRect();
        const editorRect = this.editorElement.getBoundingClientRect();

        let top = triggerRect.bottom + 8;
        let left = triggerRect.left;

        // Check if popup would go below viewport
        if (top + editorRect.height > window.innerHeight) {
            // Try to position above the input
            top = triggerRect.top - editorRect.height - 8;

            // If that would go above viewport, position at top of viewport with padding
            if (top < 0) {
                top = 10;
            }
        }

        // Check if popup would go off the right edge
        if (left + editorRect.width > window.innerWidth) {
            left = window.innerWidth - editorRect.width - 8;
        }

        // Ensure left doesn't go negative
        if (left < 0) {
            left = 10;
        }

        // Final check - ensure the popup is fully visible
        top = Math.max(10, Math.min(top, window.innerHeight - editorRect.height - 10));
        left = Math.max(10, Math.min(left, window.innerWidth - editorRect.width - 10));

        this.editorElement.style.position = 'fixed';
        this.editorElement.style.top = `${top}px`;
        this.editorElement.style.left = `${left}px`;
        this.editorElement.style.zIndex = '10000';
    }
}

// Make globally available
window.TypographyEditor = TypographyEditor;
