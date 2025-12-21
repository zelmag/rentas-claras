/**
 * form.js - VueloDigno Multi-Step Form Logic
 * Handles form navigation, validation, compensation calculation, and UI updates
 */

// ==================== CONFIGURATION ====================
const max = (a, b) => (a > b ? a : b);
const LACM_URL = "https://www.profeco.gob.mx/politicasaviacion/pdf/DERECHOS%20Y%20OBLIGACIONES%20VIAJAR%20EN%20AVI%C3%93N%20QR%20(vf).pdf";

const airlinePolicyUrls = {
    'Volaris': 'https://cms.volaris.com/globalassets/pdfs/esp/politicas-de-compensacion.pdf',
    'VivaAerobus': 'https://www.vivaaerobus.com/es-mx/legal/politica-de-compensacion',
    'Aeromexico': 'https://www.profeco.gob.mx/politicasaviacion/pdf/Aerom%C3%A9xico.pdf'
};

const airlineEmojis = {
    'Volaris': '🟣',
    'VivaAerobus': '🟢',
    'Aeromexico': '🔵'
};

const delayMap = {
    '1': { value: 1.5, text: '1-2 horas' },
    '2': { value: 3.0, text: '2-4 horas' },
    '3': { value: 5.0, text: 'Más de 4 horas o Cancelación' }
};

// ==================== STATE ====================
let currentPage = 1;
const totalPages = 4;
let calculatedCompensation = 0;
let selectedAirline = '';
let isMexicanAirline = false;
let flightFromMexico = null;

const formatter = new Intl.NumberFormat('es-MX', {
    style: 'currency',
    currency: 'MXN',
    minimumFractionDigits: 2
});

// ==================== AIRLINE SELECTION ====================
function selectAirline(button) {
    // Remove selected state from all airline buttons
    document.querySelectorAll('.airline-btn').forEach(btn => {
        btn.style.borderColor = 'var(--border-strong)';
        btn.style.background = 'var(--bg-secondary)';
        btn.style.transform = 'none';
    });

    // Mark this button as selected
    button.style.borderColor = 'var(--accent-500)';
    button.style.background = 'linear-gradient(135deg, rgba(168, 85, 247, 0.2) 0%, rgba(147, 51, 234, 0.2) 100%)';
    button.style.transform = 'scale(1.02)';

    const airline = button.dataset.airline;
    isMexicanAirline = button.dataset.mexican === 'true';

    // Hide error message
    document.getElementById('airline_error').classList.remove('show');

    // Hide law not applicable message
    document.getElementById('law-not-applicable').style.display = 'none';

    if (isMexicanAirline) {
        // Mexican airline - law applies regardless of origin
        document.getElementById('airline').value = airline;
        selectedAirline = airline;
        flightFromMexico = null;

        // Hide the foreign airline question
        document.getElementById('foreign-airline-question').style.display = 'none';

        // Show origin/destination with ALL airports
        showOriginDestination(true);
    } else {
        // Foreign airline - need to ask if flight was from Mexico
        document.getElementById('airline').value = '';
        selectedAirline = '';

        // Show the "Did your flight leave from Mexico?" question
        document.getElementById('foreign-airline-question').style.display = 'block';

        // Hide origin/destination until they answer
        document.getElementById('origin-destination-section').style.display = 'none';

        // Reset origin buttons state
        document.querySelectorAll('.origin-btn').forEach(btn => {
            btn.style.borderColor = 'var(--border-strong)';
            btn.style.background = 'var(--bg-secondary)';
        });
    }
}

function selectOriginType(button) {
    // Remove selected state from origin buttons
    document.querySelectorAll('.origin-btn').forEach(btn => {
        btn.style.borderColor = 'var(--border-strong)';
        btn.style.background = 'var(--bg-secondary)';
    });

    // Mark this button as selected
    button.style.borderColor = 'var(--accent-500)';
    button.style.background = 'linear-gradient(135deg, rgba(168, 85, 247, 0.2) 0%, rgba(147, 51, 234, 0.2) 100%)';

    flightFromMexico = button.dataset.fromMexico === 'true';

    if (flightFromMexico) {
        // Foreign airline from Mexico - law applies
        document.getElementById('airline').value = 'Other';
        selectedAirline = 'Other';

        // Hide law not applicable message
        document.getElementById('law-not-applicable').style.display = 'none';

        // Show origin/destination with ONLY Mexican airports for origin
        showOriginDestination(false);
    } else {
        // Foreign airline from abroad - law does NOT apply
        document.getElementById('law-not-applicable').style.display = 'block';
        document.getElementById('origin-destination-section').style.display = 'none';
    }
}

function showOriginDestination(showAllOrigins) {
    const originSection = document.getElementById('origin-destination-section');
    originSection.style.display = 'block';

    // Show/hide non-Mexican origin airports based on airline type
    const usaGroup = document.getElementById('origin-usa-group');
    const centralGroup = document.getElementById('origin-central-group');
    const southGroup = document.getElementById('origin-south-group');
    const europeGroup = document.getElementById('origin-europe-group');

    if (showAllOrigins) {
        // Mexican airlines can fly from anywhere
        if (usaGroup) usaGroup.style.display = '';
        if (centralGroup) centralGroup.style.display = '';
        if (southGroup) southGroup.style.display = '';
        if (europeGroup) europeGroup.style.display = '';
    } else {
        // Foreign airlines must have departed from Mexico
        if (usaGroup) usaGroup.style.display = 'none';
        if (centralGroup) centralGroup.style.display = 'none';
        if (southGroup) southGroup.style.display = 'none';
        if (europeGroup) europeGroup.style.display = 'none';
    }

    // Reset origin selection
    document.getElementById('origin').value = '';
}

function resetAirlineSelection() {
    // Reset all selections
    document.querySelectorAll('.airline-btn').forEach(btn => {
        btn.style.borderColor = 'var(--border-strong)';
        btn.style.background = 'var(--bg-secondary)';
        btn.style.transform = 'none';
    });
    document.querySelectorAll('.origin-btn').forEach(btn => {
        btn.style.borderColor = 'var(--border-strong)';
        btn.style.background = 'var(--bg-secondary)';
    });

    // Hide conditional sections
    document.getElementById('foreign-airline-question').style.display = 'none';
    document.getElementById('law-not-applicable').style.display = 'none';
    document.getElementById('origin-destination-section').style.display = 'none';

    // Reset state
    document.getElementById('airline').value = '';
    selectedAirline = '';
    isMexicanAirline = false;
    flightFromMexico = null;
}

// ==================== FAQ TOGGLE ====================
function toggleFaq(questionElement) {
    const faqItem = questionElement.parentElement;
    const wasActive = faqItem.classList.contains('active');

    // Close all other FAQ items
    document.querySelectorAll('.faq-item').forEach(item => {
        item.classList.remove('active');
    });

    // Toggle current item (close if it was already open)
    if (!wasActive) {
        faqItem.classList.add('active');
    }
}

// ==================== PAGE NAVIGATION ====================
function showPage(pageNumber) {
    const pages = document.querySelectorAll('.page');
    pages.forEach(page => {
        page.classList.remove('active');
    });
    document.querySelector(`.page[data-page="${pageNumber}"]`).classList.add('active');
    currentPage = pageNumber;

    // Show/hide FAQ section based on page
    const faqSection = document.getElementById('faq-section');

    if (pageNumber === 1) {
        if (faqSection) faqSection.style.display = 'block';
        // Reset compensation when going back to page 1
        calculatedCompensation = 0;
        selectedAirline = '';
    } else {
        if (faqSection) faqSection.style.display = 'none';
    }

    updateProgress();
    updatePageTitles();
    updateCompensationPreviews();

    // Scroll to top of page on navigation
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function goToPageIfBackwards(targetPage) {
    // Only allow navigation if target page is before current page
    if (targetPage < currentPage) {
        showPage(targetPage);
    }
}

function nextPage() {
    if (validatePage(currentPage) && currentPage < totalPages) {
        showPage(currentPage + 1);
        // Calculate compensation preview as user progresses through pages 2, 3, 4
        if (currentPage >= 2 && currentPage <= 4) {
            calculateCompensationPreview();
        }
        // Calculate full compensation when reaching page 4
        if (currentPage === 4) {
            calculateCompensation();
            updatePageTitles();
            updateCompensationChoiceVisibility();
        }
    }
}

function prevPage() {
    if (currentPage > 1) {
        showPage(currentPage - 1);
    }
}

// ==================== PAGE TITLES ====================
function updatePageTitles() {
    const titleElement = document.getElementById('page-title-text');
    const emojiElement = document.getElementById('page-title-emoji');
    const subtitleElement = document.getElementById('page-subtitle');
    const descriptionElement = document.getElementById('page-description');
    const pageTitleContainer = document.getElementById('page-title');
    const heroSection = document.getElementById('hero-section');
    const trustBadgeSection = document.getElementById('trust-badge-section');
    const faqSection = document.getElementById('faq-section');

    if (currentPage === 4 && calculatedCompensation > 0 && selectedAirline) {
        // Hide hero, trust-badge, and FAQ on page 4
        heroSection.style.display = 'none';
        trustBadgeSection.style.display = 'none';
        if (faqSection) faqSection.style.display = 'none';

        // Show the title elements on page 4
        pageTitleContainer.style.display = 'block';
        subtitleElement.style.display = 'block';
        descriptionElement.style.display = 'block';

        const passengerCount = parseInt(document.getElementById('passenger_count')?.value || 1);
        const totalCompensation = calculatedCompensation * passengerCount;

        emojiElement.textContent = "🎉";

        if (passengerCount > 1) {
            titleElement.innerHTML = `¡Felicidades! Te toca una compensación de <span style="color: #e74c3c; font-weight: bold;">${formatter.format(totalCompensation)} MXN</span><br><small style="color: #666; font-size: 0.7em;">(${formatter.format(calculatedCompensation)} × ${passengerCount} pasajeros)</small>`;
        } else {
            titleElement.innerHTML = `¡Felicidades! Te toca una compensación de <span style="color: #e74c3c; font-weight: bold;">${formatter.format(totalCompensation)} MXN</span>`;
        }

        subtitleElement.textContent = "";
        descriptionElement.innerHTML = "";
    } else if (currentPage === 1) {
        // Show hero, trust-badge, and FAQ on page 1
        heroSection.style.display = 'block';
        trustBadgeSection.style.display = 'block';
        if (faqSection) faqSection.style.display = 'block';

        // Hide title elements on page 1 (we have the hero section instead)
        pageTitleContainer.style.display = 'none';
        subtitleElement.style.display = 'none';
        descriptionElement.style.display = 'none';
    } else {
        // Pages 2, 3, 4: Hide everything
        heroSection.style.display = 'none';
        trustBadgeSection.style.display = 'none';
        if (faqSection) faqSection.style.display = 'none';
        pageTitleContainer.style.display = 'none';
        subtitleElement.style.display = 'none';
        descriptionElement.style.display = 'none';
    }
}

// ==================== VALIDATION ====================
function validateField(fieldId) {
    const field = document.getElementById(fieldId);
    const errorElement = document.getElementById(fieldId + '_error');
    const checkmark = field?.parentElement.querySelector('.input-checkmark');

    if (!field) return true;

    let isValid = true;

    // Special validation for passenger names - must match passenger count
    if (fieldId === 'passenger_name') {
        const passengerCount = parseInt(document.getElementById('passenger_count')?.value || 1);
        const names = field.value.trim();

        if (!names) {
            isValid = false;
        } else {
            // Count names by splitting on commas
            const nameList = names.split(',').map(n => n.trim()).filter(n => n.length > 0);
            const nameCount = nameList.length;

            if (nameCount !== passengerCount) {
                isValid = false;
                if (errorElement) {
                    errorElement.textContent = `Por favor ingresa ${passengerCount} nombre(s). Tienes ${nameCount}.`;
                }
            }
        }
    } else if (field.type === 'email') {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        isValid = emailRegex.test(field.value);
    } else if (field.type === 'number') {
        isValid = field.value && parseFloat(field.value) > 0;
    } else if (field.hasAttribute('pattern')) {
        const pattern = new RegExp(field.getAttribute('pattern'));
        isValid = pattern.test(field.value);
    } else {
        isValid = field.value && field.value.trim() !== '';
    }

    // Update visual states
    if (errorElement) {
        if (!isValid) {
            errorElement.classList.add('show');
            field.classList.remove('valid');
            field.classList.add('invalid');
            if (checkmark) checkmark.classList.remove('show');
        } else {
            errorElement.classList.remove('show');
            field.classList.remove('invalid');
            field.classList.add('valid');
            if (checkmark) checkmark.classList.add('show');
        }
    }

    return isValid;
}

function validatePage(pageNumber) {
    if (pageNumber === 1) {
        const originValid = validateField('origin');
        const destValid = validateField('destination');

        if (!originValid || !destValid) {
            alert('Por favor, completa todos los campos correctamente antes de continuar.');
        }

        return originValid && destValid;
    }

    if (pageNumber === 2) {
        const delayHours = document.getElementById('delay_hours').value;
        if (!delayHours || delayHours === '' || parseInt(delayHours) === 0) {
            alert('Por favor, selecciona cuánto fue el retraso del vuelo.');
            return false;
        }
        return true;
    }

    if (pageNumber === 3) {
        const ticketPriceValid = validateField('ticket_price');
        if (!ticketPriceValid) {
            alert('Por favor, ingresa el precio del boleto correctamente.');
            return false;
        }
        return true;
    }

    if (pageNumber === 4) {
        const airlineValid = validateField('airline');
        if (!airlineValid) {
            alert('Por favor, selecciona una aerolínea.');
            return false;
        }

        const currentPageElement = document.querySelector(`.page[data-page="${pageNumber}"]`);
        const requiredFields = currentPageElement.querySelectorAll('[required]');
        let isValid = true;

        requiredFields.forEach(field => {
            if (field.type === 'hidden') {
                return;
            }
            if (!validateField(field.id)) {
                isValid = false;
            }
        });

        if (!isValid) {
            alert('Por favor, completa todos los campos correctamente antes de continuar.');
        }
        return isValid;
    }

    return true;
}

// ==================== PROGRESS ====================
function updateProgress() {
    const progressLineFill = document.getElementById('progress-line-fill');
    const compensationDisplay = document.getElementById('compensation-display');
    const page2Subtitle = document.getElementById('page2-subtitle');

    // Calculate percentage based on pages mapped to 3 milestones
    let percentage = 0;
    if (currentPage === 1) {
        percentage = 0;
    } else if (currentPage === 2) {
        percentage = 33;
    } else if (currentPage === 3) {
        percentage = 66;
    } else if (currentPage === 4) {
        percentage = 100;
    }

    // Update milestone states
    const milestone1 = document.getElementById('milestone-1');
    const milestone2 = document.getElementById('milestone-2');
    const milestone3 = document.getElementById('milestone-3');

    // Reset all milestones
    [milestone1, milestone2, milestone3].forEach(m => {
        m.classList.remove('active', 'completed');
    });

    // Set states based on current page
    if (currentPage === 1) {
        milestone1.classList.add('active');
    } else if (currentPage >= 2 && currentPage <= 4) {
        milestone1.classList.add('completed');
        milestone2.classList.add('active');
    }

    // Update progress line
    if (progressLineFill) {
        progressLineFill.style.width = percentage + '%';
    }

    // Display compensation amount - visible on all pages after calculation, but hide on page 1
    if (currentPage === 1) {
        // Clear compensation on page 1
        if (compensationDisplay) {
            compensationDisplay.style.display = 'none';
            compensationDisplay.textContent = '';
        }
    } else if (calculatedCompensation > 0 && compensationDisplay) {
        const oldText = compensationDisplay.textContent;
        const newText = `💰 ${formatter.format(calculatedCompensation)}`;

        compensationDisplay.textContent = newText;
        compensationDisplay.style.display = 'inline';

        // Add animation if compensation changed (including first time)
        if (oldText !== newText) {
            compensationDisplay.classList.remove('compensation-updated');
            // Force reflow to restart animation
            void compensationDisplay.offsetWidth;
            compensationDisplay.classList.add('compensation-updated');

            // Remove animation class after it completes
            setTimeout(() => {
                compensationDisplay.classList.remove('compensation-updated');
            }, 500);
        }
    } else if (compensationDisplay) {
        compensationDisplay.style.display = 'none';
    }

    // Show page 2 subtitle when on page 2+ with valid compensation
    if (page2Subtitle) {
        if (currentPage >= 2 && calculatedCompensation > 0 && selectedAirline) {
            page2Subtitle.style.display = 'block';
        } else {
            page2Subtitle.style.display = 'none';
        }
    }

    // Show/hide back button
    const backButton = document.getElementById(`back-${currentPage}`);
    if (backButton) {
        backButton.style.visibility = currentPage === 1 ? 'hidden' : 'visible';
    }

    // Update page titles to reflect airline selection
    updatePageTitles();
}

// ==================== COMPENSATION CALCULATION ====================
function formatCurrency(input) {
    let value = input.value.replace(/[^\d.]/g, '');
    const parts = value.split('.');
    if (parts.length > 2) {
        value = parts[0] + '.' + parts.slice(1).join('');
    }
    if (parts[1] && parts[1].length > 2) {
        value = parseFloat(value).toFixed(2);
    }
    if (value) {
        const [integer, decimal] = value.split('.');
        const formattedInteger = integer.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
        input.value = decimal !== undefined ? `${formattedInteger}.${decimal}` : formattedInteger;
    }
}

function getNumericValue(formattedValue) {
    return parseFloat(formattedValue.replace(/,/g, '')) || 0;
}

function calculateCompensationPreview() {
    const delayValue = document.getElementById('delay_hours').value;
    const delayHours = parseFloat(delayValue);
    const ticketPriceInput = document.getElementById('ticket_price').value;
    const ticketPrice = parseFloat(ticketPriceInput) || 0;
    const airline = document.getElementById('airline').value;

    if (!delayValue || isNaN(delayHours) || !airline || ticketPrice <= 0) {
        calculatedCompensation = 0;
        selectedAirline = '';
        updateProgress();
        return;
    }

    selectedAirline = airline;
    const airlineKey = airline.toLowerCase().replace(/\s/g, '');

    // Match backend logic exactly from email_generator_simple.py
    if (delayHours === 5.0) {
        calculatedCompensation = ticketPrice * 1.25;
    } else if (delayHours === 1.5) {
        if (airlineKey === 'volaris') {
            calculatedCompensation = 50.00;
        } else if (airlineKey === 'vivaaerobus') {
            calculatedCompensation = 75.00;
        } else {
            calculatedCompensation = ticketPrice * 0.05;
        }
    } else if (delayHours === 3.0) {
        let bestAmount = ticketPrice * 0.075;
        if (airlineKey === 'volaris') {
            bestAmount = Math.max(250.00, ticketPrice * 0.075);
        } else if (airlineKey === 'vivaaerobus') {
            const vivaOffer = ticketPrice * 0.08;
            if (vivaOffer > bestAmount) {
                bestAmount = vivaOffer;
            }
        }
        calculatedCompensation = bestAmount;
    } else {
        calculatedCompensation = 0;
    }

    updateProgress();
}

function updateCompensationPreviews() {
    const page2Preview = document.getElementById('page-2-preview');
    const page2PreviewText = document.getElementById('page-2-preview-text');
    const page3Preview = document.getElementById('page-3-preview');
    const page3PreviewText = document.getElementById('page-3-preview-text');

    const delayValue = document.getElementById('delay_hours').value;
    const delayHours = parseFloat(delayValue);
    const ticketPrice = parseFloat(document.getElementById('ticket_price')?.value || 0);

    // Page 2: Show preview when delay is selected
    if (currentPage === 2 && delayValue && !isNaN(delayHours)) {
        let previewText = '';

        if (delayHours === 1.5) {
            previewText = 'Retraso de 1-2 horas: Entre $50-75 MXN o 5% del boleto según aerolínea.\nIngresa el precio del boleto para calcular tu compensación exacta.';
        } else if (delayHours === 3.0) {
            previewText = 'Retraso de 2-4 horas: Mínimo 7.5% del precio del boleto por ley. Algunas aerolíneas ofrecen más.\nIngresa el precio del boleto para ver tu compensación.';
        } else if (delayHours === 5.0) {
            previewText = 'Retraso de +4 horas o cancelación: 125% del precio del boleto garantizado por ley.\nIngresa el precio para calcular tu compensación exacta.';
        }

        if (page2PreviewText) page2PreviewText.textContent = previewText;
        if (page2Preview) page2Preview.style.display = 'block';
    } else if (page2Preview) {
        page2Preview.style.display = 'none';
    }

    // Page 3: Show preview when delay is selected
    if (currentPage === 3 && delayValue && !isNaN(delayHours)) {
        let previewText = '';

        if (ticketPrice > 0) {
            if (delayHours === 1.5) {
                const minComp = ticketPrice * 0.05;
                previewText = `Con tu boleto de ${formatter.format(ticketPrice)}, tu compensación será entre $50-75 MXN o ${formatter.format(minComp)} (5% del boleto), dependiendo de la aerolínea que selecciones.`;
            } else if (delayHours === 3.0) {
                const minComp = ticketPrice * 0.075;
                previewText = `Con tu boleto de ${formatter.format(ticketPrice)}, tu compensación mínima es ${formatter.format(minComp)} (7.5% por ley). Algunas aerolíneas ofrecen más. ¡Selecciona tu aerolínea para ver el monto exacto!`;
            } else if (delayHours === 5.0) {
                const comp = ticketPrice * 1.25;
                previewText = `Con tu boleto de ${formatter.format(ticketPrice)}, tu compensación garantizada es ${formatter.format(comp)} (125% del boleto). ¡Selecciona tu aerolínea para continuar!`;
            }
        } else {
            if (delayHours === 1.5) {
                previewText = 'Con el retraso de 1-2 horas, tu compensación será entre $50-75 MXN o 5% del boleto según aerolínea.';
            } else if (delayHours === 3.0) {
                previewText = 'Con el retraso de 2-4 horas, te corresponde mínimo 7.5% del precio del boleto. ¡Ingresa el precio para ver tu compensación exacta!';
            } else if (delayHours === 5.0) {
                previewText = 'Con el retraso de +4 horas o cancelación, te corresponde el 125% del precio del boleto. ¡Ingresa el precio para calcular cuánto te deben!';
            }
        }

        if (page3PreviewText) page3PreviewText.textContent = previewText;
        if (page3Preview) page3Preview.style.display = 'block';
    } else if (page3Preview) {
        page3Preview.style.display = 'none';
    }
}

function calculateCompensation() {
    const delayValue = document.getElementById('delay_hours').value;
    const delayHours = parseFloat(delayValue);

    if (!delayValue || isNaN(delayHours)) {
        document.getElementById('eligibility-message-box').style.display = 'none';
        return;
    }

    const ticketPriceInput = document.getElementById('ticket_price').value;
    const ticketPrice = parseFloat(ticketPriceInput) || 0;
    const airline = document.getElementById('airline').value;
    selectedAirline = airline;

    const resultElement = document.getElementById('claim-result');
    const msgBox = document.getElementById('eligibility-message-box');

    msgBox.style.display = 'block';

    // TIER 1: 1-2 HOURS
    if (delayHours === 1.5) {
        if (!airline) {
            resultElement.innerHTML = `
                ✅ <strong>COMPENSACIÓN GARANTIZADA POR LEY</strong>
                <br><br>
                Por un retraso de 1-2 horas, las aerolíneas ofrecen:
                <br>• <strong>Volaris:</strong> Voucher de $50 MXN
                <br>• <strong>VivaAerobus:</strong> Cupón o Viva Cash de $75 MXN
                <br>• <strong>Aeroméxico:</strong> Cupón del 5% del precio del boleto
                <br><br>
                Selecciona tu aerolínea abajo para ver tu compensación exacta.
                <br><br>
                <span style="font-size: 0.85em; color: #7f8c8d;">Fuente: <a href="${LACM_URL}" target="_blank">Ley de Aviación Civil (Art. 47 Bis)</a></span>
            `;
            calculatedCompensation = 0;
            return;
        }

        const airlineKey = airline.toLowerCase().replace(/\s/g, '');
        let compensationAmount = 0;
        let compensationForm = '';
        let policyUrl = airlinePolicyUrls[airline] || LACM_URL;

        if (airlineKey === 'volaris') {
            compensationAmount = 50.00;
            compensationForm = 'Voucher Electrónico';
        } else if (airlineKey === 'vivaaerobus') {
            compensationAmount = 75.00;
            compensationForm = 'Cupón de descuento o Viva Cash';
        } else {
            compensationAmount = ticketPrice * 0.05;
            compensationForm = 'Cupón de descuento';
        }

        calculatedCompensation = compensationAmount;

        resultElement.innerHTML = `
            <p style="margin: 0; font-size: 1em; color: var(--text-primary);">
                <strong>Compensación mínima:</strong> ${formatter.format(compensationAmount)}<br>
                <strong>Forma:</strong> ${compensationForm}
            </p>
            <p style="margin-top: 10px; font-size: 0.85em; color: var(--text-muted);">
                Fuente: <a href="${policyUrl}" target="_blank">${airlineKey === 'volaris' || airlineKey === 'vivaaerobus' ? `Política de ${airline}` : 'Política de Aeroméxico'}</a>
            </p>
        `;
        updateProgress();
        return;
    }

    // TIER 2: 2-4 HOURS
    if (delayHours === 3.0) {
        if (!ticketPriceInput && !airline) {
            resultElement.innerHTML = `
                ✅ <strong>COMPENSACIÓN GARANTIZADA POR LEY</strong>
                <br><br>
                Por un retraso de 2-4 horas, la ley mexicana garantiza:
                <br>• <strong>Mínimo 7.5% del precio del boleto</strong>
                <br><br>
                Algunas aerolíneas ofrecen más:
                <br>• Volaris: mínimo 7.5% o $250 (lo que sea mayor)
                <br>• VivaAerobus: 8% del boleto
                <br><br>
                Ingresa el precio del boleto y aerolínea abajo para calcular tu compensación exacta.
                <br><br>
                <span style="font-size: 0.85em; color: var(--text-muted);">Fuente: <a href="${LACM_URL}" target="_blank">Ley de Aviación Civil (Art. 47 Bis)</a></span>
            `;
            calculatedCompensation = 0;
            return;
        }

        if (ticketPrice > 0 && !airline) {
            const minCompensation = ticketPrice * 0.075;
            calculatedCompensation = minCompensation;
            resultElement.innerHTML = `
                ✅ <strong>COMPENSACIÓN GARANTIZADA POR LEY</strong>
                <br><br>
                Por ley, te deben <strong>mínimo:</strong>
                <br><br>
                La compensación exacta depende de la aerolínea. Selecciónala abajo:
                <br>• Volaris: mínimo 7.5% o $250 (lo que sea mayor)
                <br>• VivaAerobus: 8% del boleto
                <br>• Aeroméxico: 7.5% mínimo
                <br><br>
                <span style="font-size: 0.85em; color: var(--text-muted);">Fuente: <a href="${LACM_URL}" target="_blank">Ley de Aviación Civil (Art. 47 Bis)</a></span>
            `;
            updateProgress();
            return;
        }

        if (ticketPrice > 0 && airline) {
            let bestAmount = ticketPrice * 0.075;
            let source = `<a href="${LACM_URL}" target="_blank">Ley de Aviación Civil (Art. 47 Bis)</a>`;
            let compensationForm = 'Cupón de descuento o servicios';

            const airlineKey = airline.toLowerCase().replace(/\s/g, '');
            const policyUrl = airlinePolicyUrls[airline] || '#';

            if (airlineKey === 'volaris') {
                bestAmount = Math.max(250.00, ticketPrice * 0.075);
                source = `<a href="${policyUrl}" target="_blank">Política de Volaris</a>`;
                compensationForm = 'Voucher electrónico';
            } else if (airlineKey === 'vivaaerobus') {
                const vivaOffer = ticketPrice * 0.08;
                if (vivaOffer > bestAmount) {
                    bestAmount = vivaOffer;
                    source = `<a href="${policyUrl}" target="_blank">Política de VivaAerobus</a>`;
                    compensationForm = 'Cupón de descuento o Viva Cash';
                }
            }

            calculatedCompensation = bestAmount;

            resultElement.innerHTML = `
                <p style="margin: 0; font-size: 1em; color: var(--text-primary);">
                    <strong>Compensación mínima:</strong> ${formatter.format(bestAmount)}<br>
                    <strong>Forma:</strong> ${compensationForm}
                </p>
                <p style="margin-top: 10px; font-size: 0.85em; color: var(--text-muted);">
                    Fuente: ${source}
                </p>
            `;
            updateProgress();
            return;
        }
    }

    // TIER 3: +4 HOURS OR CANCELLATION
    if (delayHours === 5.0) {
        if (!ticketPriceInput && !airline) {
            resultElement.innerHTML = `
                ✅ <strong>¡COMPENSACIÓN MÁXIMA GARANTIZADA!</strong>
                <br><br>
                Por un retraso de +4 horas o cancelación, la ley garantiza:
                <br>• <strong>125% del precio del boleto</strong>
                <br><br>
                Ingresa el precio del boleto abajo para calcular tu compensación exacta.
                <br><br>
                <span style="font-size: 0.85em; color: var(--text-muted);">Fuente: <a href="${LACM_URL}" target="_blank">Ley de Aviación Civil (Art. 47 Bis)</a></span>
            `;
            calculatedCompensation = 0;
            return;
        }

        if (ticketPrice > 0 && !airline) {
            const compensation = ticketPrice * 1.25;
            calculatedCompensation = compensation;
            resultElement.innerHTML = `
                ✅ <strong>¡COMPENSACIÓN MÁXIMA GARANTIZADA!</strong>
                <br><br>
                Por ley, te deben:
                <br><br>
                Selecciona tu aerolínea abajo para generar tu email de reclamación.
                <br><br>
                <span style="font-size: 0.85em; color: var(--text-muted);">Fuente: <a href="${LACM_URL}" target="_blank">Ley de Aviación Civil (Art. 47 Bis)</a></span>
            `;
            updateProgress();
            return;
        }

        if (ticketPrice > 0 && airline) {
            const bestAmount = ticketPrice * 1.25;
            calculatedCompensation = bestAmount;
            const source = `<a href="${LACM_URL}" target="_blank">Ley de Aviación Civil (Art. 47 Bis)</a>`;

            resultElement.innerHTML = `
                <p style="margin: 0; font-size: 1em; color: var(--text-primary);">
                    <strong>Compensación mínima:</strong> ${formatter.format(bestAmount)}<br>
                    <strong>Forma:</strong> Transferencia bancaria / Efectivo (derecho del pasajero a elegir)
                </p>
                <p style="margin-top: 10px; font-size: 0.85em; color: var(--text-muted);">
                    Fuente: ${source}
                </p>
            `;
            updateProgress();
            return;
        }
    }
}

function updateCompensationChoiceVisibility() {
    const delayHours = parseFloat(document.getElementById('delay_hours').value);
    const compensationSection = document.getElementById('compensation-choice-section');
    const compensationHiddenInput = document.getElementById('compensation_choice');

    if (delayHours === 5.0) {
        compensationSection.style.display = 'block';
        compensationHiddenInput.required = true;
    } else {
        compensationSection.style.display = 'none';
        compensationHiddenInput.required = false;
        compensationHiddenInput.value = '';
        document.querySelectorAll('.compensation-option').forEach(btn => {
            btn.classList.remove('selected');
        });
    }
}

// ==================== JURISDICTION DATA ====================
const MEXICO_AIRPORTS = new Set(['AGU', 'BJX', 'CEN', 'CJS', 'CME', 'CPE', 'CTM', 'CUL', 'CUN', 'CUU', 'CVM', 'CZM', 'DGO', 'GDL', 'GYM', 'HMO', 'HUX', 'IZT', 'JAL', 'LAP', 'LMM', 'LTO', 'MAM', 'MEX', 'MID', 'MLM', 'MTY', 'MZT', 'NLD', 'NOG', 'OAX', 'PAZ', 'PBC', 'PPE', 'PVR', 'PXM', 'QRO', 'REX', 'SJD', 'SLP', 'TAM', 'TAP', 'TGZ', 'TIJ', 'TLC', 'TRC', 'TSL', 'VER', 'VSA', 'ZCL', 'ZIH', 'ZLO']);

const EU_AIRPORTS = new Set(['MAD', 'BCN', 'AGP', 'PMI', 'ALC', 'SVQ', 'VLC', 'BIO', 'IBZ', 'FUE', 'TFS', 'ACE', 'CDG', 'ORY', 'NCE', 'LYS', 'MRS', 'TLS', 'BOD', 'NTE', 'BSL', 'FRA', 'MUC', 'TXL', 'DUS', 'HAM', 'CGN', 'STR', 'BER', 'NUE', 'LHR', 'LGW', 'MAN', 'STN', 'EDI', 'BHX', 'GLA', 'LTN', 'BRS', 'FCO', 'MXP', 'LIN', 'VCE', 'NAP', 'BGY', 'BLQ', 'PSA', 'CAG', 'AMS', 'EIN', 'RTM', 'LIS', 'OPO', 'FAO', 'BRU', 'VIE', 'ZRH', 'GVA', 'ARN', 'CPH', 'OSL', 'HEL', 'DUB', 'ATH', 'PRG', 'WAW', 'BUD', 'OTP', 'SOF', 'RIX', 'TLL', 'VNO']);

const EUROPEAN_AIRLINES = new Set(['Lufthansa', 'Air France', 'KLM', 'British Airways', 'Iberia', 'Ryanair', 'EasyJet', 'Vueling', 'Wizz Air', 'Norwegian', 'TAP Portugal', 'Alitalia', 'ITA Airways', 'Swiss', 'Austrian Airlines', 'Brussels Airlines', 'Finnair', 'SAS', 'Aegean Airlines', 'Air Europa', 'Eurowings', 'Condor', 'Transavia', 'LOT Polish']);

// ==================== INITIALIZATION ====================
function initializeForm(backData = null) {
    const priceInput = document.getElementById('ticket_price');
    const airlineSelect = document.getElementById('airline');

    // Delay option buttons
    document.querySelectorAll('.delay-option:not(.compensation-option)').forEach(button => {
        button.addEventListener('click', function () {
            document.querySelectorAll('.delay-option:not(.compensation-option)').forEach(btn => {
                btn.classList.remove('selected');
            });

            this.classList.add('selected');
            document.getElementById('delay_hours').value = delayMap[this.dataset.value].value;

            calculateCompensationPreview();
            updateCompensationPreviews();
            updateCompensationChoiceVisibility();
        });
    });

    // Compensation choice buttons
    document.querySelectorAll('.compensation-option').forEach(button => {
        button.addEventListener('click', function () {
            document.querySelectorAll('.compensation-option').forEach(btn => {
                btn.classList.remove('selected');
            });

            this.classList.add('selected');
            document.getElementById('compensation_choice').value = this.dataset.value;
        });
    });

    // Price input
    if (priceInput) {
        priceInput.addEventListener('input', (e) => {
            let value = e.target.value;
            value = value.replace(/[^\d.]/g, '');
            const parts = value.split('.');
            if (parts.length > 2) {
                value = parts[0] + '.' + parts.slice(1).join('');
            }
            e.target.value = value;
            calculateCompensationPreview();
        });
        priceInput.addEventListener('blur', () => {
            validateField('ticket_price');
        });
    }

    // Airline select
    if (airlineSelect) {
        function updateAirlineLogo() {
            const selectedValue = airlineSelect.value;
            airlineSelect.classList.remove('volaris-selected', 'vivaaerobus-selected', 'aeromexico-selected');
            if (selectedValue === 'Volaris') {
                airlineSelect.classList.add('volaris-selected');
            } else if (selectedValue === 'VivaAerobus') {
                airlineSelect.classList.add('vivaaerobus-selected');
            } else if (selectedValue === 'Aeromexico') {
                airlineSelect.classList.add('aeromexico-selected');
            }
        }

        airlineSelect.addEventListener('input', () => {
            updateAirlineLogo();
            calculateCompensationPreview();
            validateField('airline');
        });
        airlineSelect.addEventListener('change', () => {
            updateAirlineLogo();
            calculateCompensationPreview();
            validateField('airline');
        });
    }

    // Origin/destination validation
    const originInput = document.getElementById('origin');
    const destInput = document.getElementById('destination');

    if (originInput) {
        originInput.addEventListener('input', () => validateField('origin'));
        originInput.addEventListener('blur', () => validateField('origin'));
    }

    if (destInput) {
        destInput.addEventListener('input', () => validateField('destination'));
        destInput.addEventListener('blur', () => validateField('destination'));
    }

    // All required field validation
    document.querySelectorAll('input[required], select[required]').forEach(field => {
        field.addEventListener('blur', () => {
            if (field.id) validateField(field.id);
        });
        field.addEventListener('input', () => {
            if (field.id && field.value) validateField(field.id);
        });
    });

    // Passenger count handling
    const passengerCountInput = document.getElementById('passenger_count');
    if (passengerCountInput) {
        const passengerNameHint = document.querySelector('#passenger_name + .input-checkmark + small') ||
                                  document.querySelector('label[for="passenger_name"] + input + small');

        function updatePassengerNameHint() {
            const count = parseInt(passengerCountInput.value) || 1;
            if (passengerNameHint) {
                if (count > 1) {
                    passengerNameHint.innerHTML = `💡 Debes ingresar <strong>${count} nombres</strong> separados por comas`;
                    passengerNameHint.style.color = '#006847';
                } else {
                    passengerNameHint.innerHTML = 'Ingresa el nombre completo del pasajero';
                    passengerNameHint.style.color = '#666';
                }
            }
        }

        passengerCountInput.addEventListener('input', () => {
            updatePageTitles();
            updatePassengerNameHint();
            const passengerNameField = document.getElementById('passenger_name');
            if (passengerNameField && passengerNameField.value) {
                validateField('passenger_name');
            }
        });
        passengerCountInput.addEventListener('change', () => {
            updatePageTitles();
            updatePassengerNameHint();
            const passengerNameField = document.getElementById('passenger_name');
            if (passengerNameField && passengerNameField.value) {
                validateField('passenger_name');
            }
        });

        updatePassengerNameHint();
    }

    // Mobile keyboard scroll fix
    const allInputs = document.querySelectorAll('input, select, textarea');
    function scrollInputIntoView(element) {
        const inputRect = element.getBoundingClientRect();
        const scrollOffset = inputRect.top + window.pageYOffset - 20;
        window.scrollTo({
            top: scrollOffset,
            behavior: 'smooth'
        });
    }

    allInputs.forEach(input => {
        input.addEventListener('focus', function () {
            setTimeout(() => {
                scrollInputIntoView(this);
            }, 400);
        });
        input.addEventListener('input', function () {
            scrollInputIntoView(this);
        });
    });

    // Handle back data from preview page
    if (backData) {
        document.getElementById('origin').value = backData.origin;
        document.getElementById('destination').value = backData.destination;
        document.getElementById('delay_hours').value = backData.delay_hours;
        document.getElementById('ticket_price').value = backData.ticket_price;
        document.getElementById('airline').value = backData.airline;
        document.getElementById('flight_number').value = backData.flight_number;
        document.getElementById('reservation_code').value = backData.reservation_code;
        document.getElementById('date').value = backData.date;

        const passengerName = document.getElementById('passenger_name');
        if (passengerName) passengerName.value = backData.passenger_name;

        const passengerEmail = document.getElementById('passenger_email');
        if (passengerEmail) passengerEmail.value = backData.passenger_email;

        document.getElementById('passenger_count').value = backData.passenger_count || '1';

        // Mark delay option
        const delayHoursFloat = parseFloat(backData.delay_hours);
        let delayDataValue = '1';
        if (delayHoursFloat === 1.5) delayDataValue = '1';
        else if (delayHoursFloat === 3.0) delayDataValue = '2';
        else if (delayHoursFloat === 5.0) delayDataValue = '3';

        document.querySelectorAll('.delay-option').forEach(btn => {
            if (btn.dataset.value === delayDataValue) {
                btn.classList.add('selected');
            }
        });

        selectedAirline = backData.airline;

        if (airlineSelect) {
            const selectedValue = airlineSelect.value;
            airlineSelect.classList.remove('volaris-selected', 'vivaaerobus-selected', 'aeromexico-selected');
            if (selectedValue === 'Volaris') {
                airlineSelect.classList.add('volaris-selected');
            } else if (selectedValue === 'VivaAerobus') {
                airlineSelect.classList.add('vivaaerobus-selected');
            } else if (selectedValue === 'Aeromexico') {
                airlineSelect.classList.add('aeromexico-selected');
            }
        }

        calculateCompensationPreview();

        if (backData.compensation_choice) {
            const choiceButton = document.querySelector(`.compensation-option[data-value="${backData.compensation_choice}"]`);
            if (choiceButton) {
                choiceButton.classList.add('selected');
                document.getElementById('compensation_choice').value = backData.compensation_choice;
            }
        }

        updateCompensationChoiceVisibility();
        showPage(4);
    } else {
        showPage(1);
    }
}

// Export for global access
window.selectAirline = selectAirline;
window.selectOriginType = selectOriginType;
window.resetAirlineSelection = resetAirlineSelection;
window.toggleFaq = toggleFaq;
window.nextPage = nextPage;
window.prevPage = prevPage;
window.goToPageIfBackwards = goToPageIfBackwards;
window.initializeForm = initializeForm;
