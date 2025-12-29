/**
 * Login Page Scripts
 * ==================
 * 
 * PIN-based authentication with visual feedback.
 * Features:
 * - Visual digit masking (● characters)
 * - Auto-submit on 4 digits
 * - Mobile keyboard handling
 */

(function () {
    'use strict';

    // ==========================================================================
    // DOM ELEMENTS
    // ==========================================================================

    const pinInput = document.getElementById('pinInput');
    const loginForm = document.getElementById('loginForm');
    const pinContainer = document.querySelector('.pin-container');
    const digits = [
        document.getElementById('pin1'),
        document.getElementById('pin2'),
        document.getElementById('pin3'),
        document.getElementById('pin4')
    ];

    // Colors from CSS variables
    const COLOR_PRIMARY = '#0A7A0A';
    const COLOR_NEUTRAL = '#333333';
    const COLOR_FOCUS_BG = '#F0FDF4';

    // ==========================================================================
    // PIN INPUT HANDLING
    // ==========================================================================

    /**
     * Update visual digit boxes based on input value.
     */
    function updateDigitDisplay(value) {
        digits.forEach((digit, index) => {
            if (value[index]) {
                digit.value = '●';
                digit.style.borderColor = COLOR_PRIMARY;
                digit.style.background = COLOR_FOCUS_BG;
            } else {
                digit.value = '';
                digit.style.borderColor = COLOR_NEUTRAL;
                digit.style.background = 'white';
            }
        });
    }

    /**
     * Auto-submit form when 4 digits are entered.
     */
    function checkAutoSubmit(value) {
        if (value.length === 4) {
            setTimeout(() => {
                loginForm.submit();
            }, 300);
        }
    }

    // Listen for PIN input changes
    pinInput.addEventListener('input', function () {
        const value = this.value;
        updateDigitDisplay(value);
        checkAutoSubmit(value);
    });

    // ==========================================================================
    // FOCUS HANDLING
    // ==========================================================================

    // Focus hidden input when clicking PIN container
    pinContainer.addEventListener('click', function () {
        pinInput.focus();
    });

    /**
     * Scroll PIN container into view (for mobile keyboards).
     */
    function scrollPinContainerIntoView() {
        setTimeout(() => {
            if (pinContainer) {
                pinContainer.scrollIntoView({
                    behavior: 'smooth',
                    block: 'center'
                });
            }
        }, 300);
    }

    // Scroll into view when input is focused
    pinInput.addEventListener('focus', scrollPinContainerIntoView);

    // Handle visual viewport resize (mobile keyboard appears)
    if (window.visualViewport) {
        window.visualViewport.addEventListener('resize', function () {
            if (document.activeElement === pinInput) {
                scrollPinContainerIntoView();
            }
        });
    }

    // ==========================================================================
    // INITIALIZATION
    // ==========================================================================

    // Focus PIN input on page load
    pinInput.focus();

})();
