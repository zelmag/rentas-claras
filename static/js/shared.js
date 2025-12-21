/**
 * VueloDigno Shared JavaScript - Single Source of Truth
 * Common functions used across all pages
 */

// ============================================
// LOCAL STORAGE FOR FORM PERSISTENCE
// ============================================

const FORM_STORAGE_KEY = 'vuelodigno_form_data';

/**
 * Save form data to localStorage
 * @param {Object} additionalData - Additional state data to save (e.g., currentPage, selectedAirline)
 */
function saveFormDataToStorage(additionalData = {}) {
    const formData = {
        origin: document.getElementById('origin')?.value || '',
        destination: document.getElementById('destination')?.value || '',
        delay_hours: document.getElementById('delay_hours')?.value || '',
        ticket_price: document.getElementById('ticket_price')?.value || '',
        airline: document.getElementById('airline')?.value || '',
        flight_number: document.getElementById('flight_number')?.value || '',
        reservation_code: document.getElementById('reservation_code')?.value || '',
        date: document.getElementById('date')?.value || '',
        passenger_count: document.getElementById('passenger_count')?.value || '1',
        compensation_choice: document.getElementById('compensation_choice')?.value || '',
        ...additionalData
    };
    localStorage.setItem(FORM_STORAGE_KEY, JSON.stringify(formData));
}

/**
 * Load form data from localStorage
 * @returns {Object|null} Stored form data or null if not found
 */
function loadFormDataFromStorage() {
    const storedData = localStorage.getItem(FORM_STORAGE_KEY);
    if (!storedData) return null;
    try {
        return JSON.parse(storedData);
    } catch (e) {
        console.error('Error parsing form data from storage:', e);
        return null;
    }
}

/**
 * Clear form data from localStorage
 */
function clearFormStorage() {
    localStorage.removeItem(FORM_STORAGE_KEY);
}

// ============================================
// MOBILE KEYBOARD SCROLL FIX
// ============================================

/**
 * Scroll input element into view
 * @param {HTMLElement} element - The input element to scroll into view
 */
function scrollInputIntoView(element) {
    const inputRect = element.getBoundingClientRect();
    const scrollOffset = inputRect.top + window.pageYOffset - 20;
    window.scrollTo({
        top: scrollOffset,
        behavior: 'smooth'
    });
}

/**
 * Initialize mobile keyboard scroll fix for all inputs
 */
function initMobileKeyboardFix() {
    const allInputs = document.querySelectorAll('input, select, textarea, [contenteditable="true"]');

    allInputs.forEach(input => {
        // Scroll on focus (when keyboard appears)
        input.addEventListener('focus', function() {
            setTimeout(() => {
                scrollInputIntoView(this);
            }, 400);
        });

        // Also scroll on input (as user types)
        input.addEventListener('input', function() {
            scrollInputIntoView(this);
        });
    });
}

// ============================================
// CURRENCY FORMATTER
// ============================================

const currencyFormatter = new Intl.NumberFormat('es-MX', {
    style: 'currency',
    currency: 'MXN',
    minimumFractionDigits: 2
});

/**
 * Format a number as Mexican Peso currency
 * @param {number} amount - The amount to format
 * @returns {string} Formatted currency string
 */
function formatCurrency(amount) {
    return currencyFormatter.format(amount);
}

// ============================================
// CONFETTI
// ============================================

/**
 * Shoot confetti animation
 * @param {Object} options - Confetti options (optional)
 */
function shootConfetti(options = {}) {
    // Check if confetti library is loaded
    if (typeof confetti === 'undefined') {
        console.error('Confetti library not loaded');
        return;
    }

    const defaultOptions = {
        particleCount: 100,
        spread: 70,
        origin: { y: 0.6 },
        colors: ['#10b981', '#3498db', '#f39c12']
    };

    confetti({ ...defaultOptions, ...options });
}

/**
 * Shoot money-themed confetti
 */
function shootMoneyConfetti() {
    if (typeof confetti === 'undefined') {
        console.error('Confetti library not loaded');
        return;
    }

    confetti({
        particleCount: 150,
        spread: 120,
        origin: { y: 0.6 },
        shapes: ['square'],
        colors: ['#228B22', '#FFD700', '#FFFFFF']
    });
}

// ============================================
// COPY TO CLIPBOARD
// ============================================

/**
 * Copy text to clipboard with fallback
 * @param {string} text - Text to copy
 * @returns {Promise<boolean>} Success status
 */
async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        return true;
    } catch (err) {
        console.error('Error copying to clipboard:', err);
        return false;
    }
}

/**
 * Copy HTML and plain text to clipboard
 * @param {string} htmlContent - HTML content
 * @param {string} plainText - Plain text content
 * @returns {Promise<boolean>} Success status
 */
async function copyRichText(htmlContent, plainText) {
    try {
        const htmlBlob = new Blob([htmlContent], { type: 'text/html' });
        const textBlob = new Blob([plainText], { type: 'text/plain' });

        const data = [new ClipboardItem({
            'text/html': htmlBlob,
            'text/plain': textBlob
        })];

        await navigator.clipboard.write(data);
        return true;
    } catch (err) {
        // Fallback to plain text copy
        return copyToClipboard(plainText);
    }
}

// ============================================
// ANALYTICS HELPERS
// ============================================

/**
 * Track an event with Google Analytics
 * @param {string} eventName - Name of the event
 * @param {Object} params - Event parameters
 */
function trackEvent(eventName, params = {}) {
    if (typeof gtag !== 'undefined') {
        gtag('event', eventName, params);
    }
}

// ============================================
// INITIALIZATION
// ============================================

// Auto-initialize mobile keyboard fix when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    initMobileKeyboardFix();
});
