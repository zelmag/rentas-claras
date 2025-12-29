        console.log('🚀 Main script starting...');

        // =============================================
        // 🔍 DEBUG: Global Error Handler & Tracing
        // =============================================
        window.onerror = function(message, source, lineno, colno, error) {
            console.error('🚨 GLOBAL ERROR:', {
                message,
                source,
                lineno,
                colno,
                error: error?.stack || error
            });
            return false;
        };

        window.addEventListener('unhandledrejection', function(event) {
            console.error('🚨 UNHANDLED PROMISE REJECTION:', event.reason);
        });

        // Debug utility to check button clickability
        function debugButtonClickability() {
            console.log('🔍 === BUTTON CLICKABILITY DEBUG ===');

            // Check all status pills
            const statusPills = document.querySelectorAll('.status-pill');
            console.log(`Found ${statusPills.length} status pills`);

            statusPills.forEach((btn, i) => {
                const rect = btn.getBoundingClientRect();
                const styles = window.getComputedStyle(btn);
                const tenantId = btn.closest('[data-tenant-id]')?.dataset?.tenantId || 'unknown';

                console.log(`Button ${i} (tenant: ${tenantId}):`, {
                    visible: rect.width > 0 && rect.height > 0,
                    position: { top: rect.top, left: rect.left, width: rect.width, height: rect.height },
                    pointerEvents: styles.pointerEvents,
                    zIndex: styles.zIndex,
                    opacity: styles.opacity,
                    display: styles.display,
                    visibility: styles.visibility,
                    disabled: btn.disabled,
                    hasOnclick: !!btn.onclick || btn.hasAttribute('onclick')
                });

                // Check for overlapping elements
                const centerX = rect.left + rect.width / 2;
                const centerY = rect.top + rect.height / 2;
                const elementAtPoint = document.elementFromPoint(centerX, centerY);
                if (elementAtPoint !== btn && !btn.contains(elementAtPoint)) {
                    console.warn(`⚠️ Button ${i} is covered by:`, elementAtPoint, elementAtPoint?.className);
                }
            });

            // Check payment toggles
            const toggles = document.querySelectorAll('.payment-toggle input[type="checkbox"]');
            console.log(`Found ${toggles.length} payment toggles`);
            toggles.forEach((toggle, i) => {
                const tenantId = toggle.closest('[data-tenant-id]')?.dataset?.tenantId || 'unknown';
                console.log(`Toggle ${i} (tenant: ${tenantId}):`, {
                    checked: toggle.checked,
                    disabled: toggle.disabled,
                    hasOnchange: !!toggle.onchange || toggle.hasAttribute('onchange')
                });
            });

            // Check for modals blocking clicks
            const modals = document.querySelectorAll('.phone-modal, .confirm-modal');
            modals.forEach((modal, i) => {
                const styles = window.getComputedStyle(modal);
                if (styles.display !== 'none' && styles.visibility !== 'hidden') {
                    console.warn(`⚠️ Modal ${i} might be blocking clicks:`, {
                        display: styles.display,
                        visibility: styles.visibility,
                        zIndex: styles.zIndex,
                        hasShowClass: modal.classList.contains('show')
                    });
                }
            });

            console.log('🔍 === END DEBUG ===');
        }

        // Make debug function available globally
        window.debugButtonClickability = debugButtonClickability;

        // Add click event listener to document to trace all clicks
        document.addEventListener('click', function(e) {
            const target = e.target;
            const isButton = target.matches('button, .status-pill, .payment-toggle, [onclick]') ||
                            target.closest('button, .status-pill, .payment-toggle, [onclick]');

            if (isButton) {
                console.log('🖱️ Click detected:', {
                    element: target.tagName,
                    className: target.className,
                    id: target.id,
                    onclick: target.getAttribute('onclick'),
                    closestTenantId: target.closest('[data-tenant-id]')?.dataset?.tenantId,
                    defaultPrevented: e.defaultPrevented,
                    propagationStopped: e.cancelBubble
                });
            }
        }, true); // Use capture phase to see clicks before they're handled

        // Read config from data attributes (no more Jinja in JS!)
        const configEl = document.getElementById('pagos-config');
        const dayOfMonth = parseInt(configEl?.dataset.dayOfMonth || '1');
        const currentYear = parseInt(configEl?.dataset.currentYear || new Date().getFullYear());
        const currentMonth = parseInt(configEl?.dataset.currentMonth || (new Date().getMonth() + 1));
        const testMode = configEl?.dataset.testMode === 'true';
        const testPhone = configEl?.dataset.testPhone || '';
        const monthName = configEl?.dataset.monthName || '';
        console.log('✅ Variables initialized from config:', { dayOfMonth, currentYear, currentMonth, testMode, monthName });

        // BUGFIX: Track in-flight payment requests to prevent duplicates
        const inFlightRequests = new Map();

        // BUGFIX: Track toggle operations in progress to prevent race conditions
        const toggleInProgress = new Set();

        // =============================================
        // SINGLE SOURCE OF TRUTH (SOT) for Payment State
        // Persists state in localStorage for cross-page consistency
        // BUGFIX: Now scoped by month/year to prevent cross-month state pollution
        // =============================================

        // Generate a unique key for each month/year combination
        function getSOTKey() {
            return `paymentStateSOT_${currentYear}_${currentMonth}`;
        }

        function getPaymentSOT() {
            try {
                const key = getSOTKey();
                const data = localStorage.getItem(key);
                return data ? JSON.parse(data) : { version: 2, year: currentYear, month: currentMonth, lastUpdated: 0, tenants: {} };
            } catch (e) {
                console.error('Error reading SOT:', e);
                return { version: 2, year: currentYear, month: currentMonth, lastUpdated: 0, tenants: {} };
            }
        }

        function updatePaymentSOT(tenantId, isPaid, paymentMethod = null) {
            const sot = getPaymentSOT();
            sot.tenants[tenantId] = {
                isPaid,
                paymentMethod,
                updatedAt: Date.now()
            };
            sot.lastUpdated = Date.now();
            const key = getSOTKey();
            localStorage.setItem(key, JSON.stringify(sot));
            console.log('SOT updated:', tenantId, isPaid, 'key:', key);
            return sot;
        }

        // BUGFIX: Clear stale SOT entries older than 90 days to prevent localStorage bloat
        function cleanupStaleSOT() {
            const now = Date.now();
            const maxAge = 90 * 24 * 60 * 60 * 1000; // 90 days in ms
            const keysToRemove = [];

            for (let i = 0; i < localStorage.length; i++) {
                const key = localStorage.key(i);
                if (key && key.startsWith('paymentStateSOT_')) {
                    try {
                        const data = JSON.parse(localStorage.getItem(key));
                        if (data && data.lastUpdated && (now - data.lastUpdated) > maxAge) {
                            keysToRemove.push(key);
                        }
                    } catch (e) {
                        // Invalid data, remove it
                        keysToRemove.push(key);
                    }
                }
            }

            keysToRemove.forEach(key => {
                localStorage.removeItem(key);
                console.log('Cleaned up stale SOT:', key);
            });

            // Also clean up the old non-scoped key if it exists
            if (localStorage.getItem('paymentStateSOT')) {
                localStorage.removeItem('paymentStateSOT');
                console.log('Cleaned up legacy paymentStateSOT key');
            }
        }

        // BUGFIX: Reconcile SOT with server state on page load
        // Server state is authoritative - only keep SOT entries that are MORE RECENT
        function reconcileSOTWithServer() {
            const sot = getPaymentSOT();
            const serverStateMap = new Map();

            // Build map of server state from DOM (rendered by Jinja)
            document.querySelectorAll('.tenant-item').forEach(item => {
                const tenantId = item.dataset.tenantId;
                const isPaidServer = item.classList.contains('paid');
                serverStateMap.set(tenantId, isPaidServer);
            });

            // Check each SOT entry - if server disagrees and SOT is old (>5 min), trust server
            const fiveMinutesAgo = Date.now() - (5 * 60 * 1000);
            let needsUpdate = false;

            Object.entries(sot.tenants).forEach(([tenantId, state]) => {
                const serverState = serverStateMap.get(tenantId);
                if (serverState !== undefined && serverState !== state.isPaid) {
                    // Server disagrees - check if SOT is stale
                    if (state.updatedAt < fiveMinutesAgo) {
                        console.log(`SOT stale for ${tenantId}, trusting server (SOT: ${state.isPaid}, Server: ${serverState})`);
                        delete sot.tenants[tenantId];
                        needsUpdate = true;
                    } else {
                        console.log(`SOT fresh for ${tenantId}, keeping local state (SOT: ${state.isPaid}, Server: ${serverState})`);
                    }
                }
            });

            if (needsUpdate) {
                const key = getSOTKey();
                localStorage.setItem(key, JSON.stringify(sot));
            }
        }

        function applyPaymentSOT() {
            console.log('Applying SOT to DOM...');

            // First reconcile with server to remove stale entries
            reconcileSOTWithServer();

            const sot = getPaymentSOT();
            let appliedCount = 0;

            Object.entries(sot.tenants).forEach(([tenantId, state]) => {
                // Apply to both views
                syncBothViews(tenantId, state.isPaid);
                appliedCount++;
            });

            if (appliedCount > 0) {
                console.log(`SOT applied to ${appliedCount} tenants`);
                updateCounts();
                // BUGFIX #10: Call updatePropertyFilterCounts instead of non-existent flushPropertyFilterCounts
                if (typeof updatePropertyFilterCounts === 'function') {
                    updatePropertyFilterCounts();
                }
            }
        }

        // Master sync function - updates BOTH card and table views
        function syncBothViews(tenantId, isPaid) {
            syncCardView(tenantId, isPaid);
            syncTableView(tenantId, isPaid);
        }

        // #4: VIEW SWITCHING FUNCTIONS - Segmented control buttons
        function toggleView() {
            const toggle = document.getElementById('viewToggle');
            if (toggle.checked) {
                switchToTableView();
            } else {
                switchToCardView();
            }
        }

        function switchToCardView() {
            console.log('switchToCardView called');
            const cardView = document.getElementById('cardView');
            const excelView = document.getElementById('excelView');

            if (!cardView || !excelView) {
                console.error('View elements not found:', { cardView, excelView });
                return;
            }

            // Direct style manipulation - guaranteed to work
            cardView.style.display = 'block';
            excelView.style.display = 'none';

            // Update segmented control button states - PROMINENT for Don Raúl
            const cardBtn = document.getElementById('cardViewBtn');
            const tableBtn = document.getElementById('tableViewBtn');

            if (cardBtn) {
                cardBtn.style.background = '#0A7A0A';
                cardBtn.style.color = 'white';
                cardBtn.style.boxShadow = '0 4px 12px rgba(10, 122, 10, 0.4)';
                cardBtn.style.border = '3px solid #065F06';
            }
            if (tableBtn) {
                tableBtn.style.background = 'transparent';
                tableBtn.style.color = '#666';
                tableBtn.style.boxShadow = 'none';
                tableBtn.style.border = '3px solid transparent';
            }

            // Update hint text for Don Raúl
            const viewHint = document.getElementById('viewHint');
            if (viewHint) {
                viewHint.innerHTML = '🃏 Vista de tarjetas activa - más detalles por inquilino';
            }

            // Update hidden checkbox for compatibility
            const toggle = document.getElementById('viewToggle');
            if (toggle) toggle.checked = false;

            localStorage.setItem('preferredView', 'card');

            // BUGFIX #6: Apply SOT to ensure card view has correct state after switch
            applyPaymentSOT();

            console.log('Switched to card view');
        }

        function switchToTableView() {
            console.log('switchToTableView called');
            const cardView = document.getElementById('cardView');
            const excelView = document.getElementById('excelView');

            if (!cardView || !excelView) {
                console.error('View elements not found:', { cardView, excelView });
                return;
            }

            // Direct style manipulation - guaranteed to work
            cardView.style.display = 'none';
            excelView.style.display = 'block';

            // Update segmented control button states - PROMINENT for Don Raúl
            const cardBtn = document.getElementById('cardViewBtn');
            const tableBtn = document.getElementById('tableViewBtn');

            if (tableBtn) {
                tableBtn.style.background = '#0A7A0A';
                tableBtn.style.color = 'white';
                tableBtn.style.boxShadow = '0 4px 12px rgba(10, 122, 10, 0.4)';
                tableBtn.style.border = '3px solid #065F06';
            }
            if (cardBtn) {
                cardBtn.style.background = 'transparent';
                cardBtn.style.color = '#666';
                cardBtn.style.boxShadow = 'none';
                cardBtn.style.border = '3px solid transparent';
            }

            // Update hint text for Don Raúl
            const viewHint = document.getElementById('viewHint');
            if (viewHint) {
                viewHint.innerHTML = '📊 Vista de tabla activa - como Excel';
            }

            // Update hidden checkbox for compatibility
            const toggle = document.getElementById('viewToggle');
            if (toggle) toggle.checked = true;

            localStorage.setItem('preferredView', 'table');

            // BUGFIX #6: Apply SOT to ensure table view has correct state after switch
            applyPaymentSOT();

            console.log('Switched to table view');
        }

        // #4: Restore user's preferred view on page load - DEFAULT is now TABLE
        window.addEventListener('DOMContentLoaded', () => {
            const preferredView = localStorage.getItem('preferredView') || 'table';
            if (preferredView === 'card') {
                switchToCardView();
            } else {
                switchToTableView();
            }

            // Initialize counts and subtotals on page load
            updateCounts();

            // Apply SOT (Single Source of Truth) to restore payment state from localStorage
            // This ensures state persists across page navigation (e.g., Contratos → Pagos)
            setTimeout(() => {
                applyPaymentSOT();
            }, 100);

            // Set up search functionality
            const searchInput = document.getElementById('tenantSearch');
            if (searchInput) {
                searchInput.addEventListener('input', function(e) {
                    filterTenants(e.target.value);
                });
            }

            // 🔍 DEBUG: Run button clickability check after page loads
            setTimeout(() => {
                console.log('🔍 Running automatic button clickability debug...');
                debugButtonClickability();
            }, 500);
        });

        // Toggle paid status from Excel table view
        function togglePaidTable(btn, tenantId) {
            console.log('🔘 togglePaidTable called:', { btn, tenantId, btnClass: btn?.className });

            try {
                // BUGFIX #9: Prevent double-clicks with toggleInProgress
                if (toggleInProgress.has(tenantId)) {
                    console.log('⏳ Toggle already in progress for', tenantId);
                    return;
                }
                toggleInProgress.add(tenantId);

                // Determine current state and toggle it
                const row = btn.closest('tr');
                if (!row) {
                    console.error('❌ Could not find parent row for button');
                    toggleInProgress.delete(tenantId);
                    return;
                }

                const currentlyPaid = btn.classList.contains('paid');
                const newPaidStatus = !currentlyPaid;
                console.log('📊 Status change:', { tenantId, currentlyPaid, newPaidStatus });

                // 1. UPDATE SOT FIRST (Single Source of Truth)
                updatePaymentSOT(tenantId, newPaidStatus);

                // Update table row appearance
                const pagadoCell = row.querySelector('.pagado-cell');
                const rentCell = row.querySelector('.rent-cell');
                const rentAmount = rentCell ? rentCell.textContent.trim() : '$0';

                if (newPaidStatus) {
                    row.classList.add('paid-row');
                    row.classList.remove('unpaid-row');
                    btn.className = 'status-pill status-pill--small tenant-status-btn-table paid';
                    btn.textContent = '✓';
                    if (pagadoCell) {
                        pagadoCell.textContent = rentAmount;
                    }
                    if (rentCell) {
                        rentCell.style.color = '';
                    }
                } else {
                    row.classList.add('unpaid-row');
                    row.classList.remove('paid-row');
                    btn.className = 'status-pill status-pill--small tenant-status-btn-table unpaid';
                    btn.textContent = '';
                    if (pagadoCell) {
                        pagadoCell.textContent = '';
                    }
                    if (rentCell) {
                        rentCell.style.color = '#CC0000';
                    }
                }

                // 2. Sync card view with table view state
                syncCardView(tenantId, newPaidStatus);

                // Update property totals
                updatePropertyTotals();

                // 3. Save to database
                console.log('💾 Saving to database:', { tenantId, newPaidStatus });
                fetch('/api/payment', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ tenant_id: tenantId, paid: newPaidStatus, year: currentYear, month: currentMonth })
                }).then(response => {
                    toggleInProgress.delete(tenantId);
                    if (response.ok) {
                    console.log(`✅ Guardado: ${tenantId} = ${newPaidStatus ? 'pagado' : 'pendiente'}`);
                        updateCounts();
                        updateLastSaved();  // BUGFIX #4: Update sync indicator when table toggle saves
                    } else {
                        console.error('❌ Server returned error:', response.status);
                    }
                }).catch(err => {
                    toggleInProgress.delete(tenantId);
                    console.error('❌ Payment update failed:', err);
                });
            } catch (error) {
                console.error('🚨 Error in togglePaidTable:', error);
                toggleInProgress.delete(tenantId);
            }
        }

        // Fallback function for direct API update when card view buttons not found
        function updatePaymentDirectly(tenantId, isPaid) {
            fetch('/api/payment', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ tenant_id: tenantId, paid: isPaid, year: currentYear, month: currentMonth })
            }).then(response => {
                if (response.ok) {
                    updateCounts();
                }
            }).catch(err => console.error('Payment update failed:', err));
        }

        // Helper function to sync table view when card view changes
        function syncTableView(tenantId, isPaid) {
            const tableRow = document.querySelector(`tr[data-tenant-id="${tenantId}"]`);
            if (!tableRow) return; // Table view might not exist

            const btn = tableRow.querySelector('.tenant-status-btn-table');
            const pagadoCell = tableRow.querySelector('.pagado-cell');
            const rentCell = tableRow.querySelector('.rent-cell');
            const rentAmount = rentCell ? rentCell.textContent.trim() : '$0';

            if (isPaid) {
                tableRow.classList.add('paid-row');
                tableRow.classList.remove('unpaid-row');
                if (btn) {
                    btn.className = 'status-pill status-pill--small tenant-status-btn-table paid';
                    btn.textContent = '✓';
                }
                if (pagadoCell) {
                    pagadoCell.textContent = rentAmount;
                }
                if (rentCell) {
                    rentCell.style.color = '';
                }
            } else {
                tableRow.classList.add('unpaid-row');
                tableRow.classList.remove('paid-row');
                if (btn) {
                    btn.className = 'status-pill status-pill--small tenant-status-btn-table unpaid';
                    btn.textContent = '';
                }
                if (pagadoCell) {
                    pagadoCell.textContent = '';
                }
                if (rentCell) {
                    rentCell.style.color = '#CC0000';
                }
            }

            // Update property totals
            updatePropertyTotals();
        }

        // Helper function to sync card view when table view changes
        function syncCardView(tenantId, isPaid) {
            const cardItem = document.querySelector(`.tenant-item[data-tenant-id="${tenantId}"]`);
            if (!cardItem) {
                console.log('syncCardView: No card item found for', tenantId);
                return;
            }

            // BUGFIX: .payment-toggle is a LABEL, need to find the INPUT inside .payment-toggle-container
            const toggleContainer = cardItem.querySelector('.payment-toggle-container');
            const toggleInput = toggleContainer ? toggleContainer.querySelector('input[type="checkbox"]') : null;
            const toggleLabel = cardItem.querySelector('.payment-toggle-label');
            const checkbox = cardItem.querySelector('.tenant-checkbox');
            const paymentSelect = cardItem.querySelector('.payment-method');
            const container = cardItem.querySelector('.payment-buttons');

            console.log('syncCardView:', tenantId, 'isPaid:', isPaid, 'toggleInput found:', !!toggleInput);

            // Update toggle state - the actual INPUT element
            if (toggleInput) {
                toggleInput.checked = isPaid;
                console.log('syncCardView: Set toggleInput.checked =', isPaid);
            }

            // Update toggle label text
            if (toggleLabel) {
                toggleLabel.textContent = isPaid ? 'Ya pagó' : 'No ha pagado';
                toggleLabel.classList.remove('paid', 'unpaid');
                toggleLabel.classList.add(isPaid ? 'paid' : 'unpaid');
            }

            // Update payment buttons if present
            if (container) {
                container.querySelectorAll('.payment-btn').forEach(b => {
                    b.classList.remove('active-green', 'active-red');
                });
                const activeBtn = container.querySelector(`.payment-btn[onclick*="${isPaid}"]`);
                if (activeBtn) {
                    activeBtn.classList.add(isPaid ? 'active-green' : 'active-red');
                }
            }

            // Update item state
            if (isPaid) {
                cardItem.classList.add('paid');
                if (checkbox) checkbox.checked = false;
                if (paymentSelect) paymentSelect.disabled = false;
            } else {
                cardItem.classList.remove('paid');
                if (checkbox) checkbox.checked = true;
                if (paymentSelect) {
                    paymentSelect.disabled = true;
                    paymentSelect.value = '';
                }
            }

            updateWhatsAppButton(cardItem, isPaid);
        }

        // Update property totals when payment status changes
        function updatePropertyTotals() {
            const propertySections = document.querySelectorAll('.excel-property-section');
            propertySections.forEach(section => {
                let totalPaid = 0;
                const rows = section.querySelectorAll('tr[data-tenant-id]');
                rows.forEach(row => {
                    if (row.classList.contains('paid-row')) {
                        const rentCell = row.querySelector('.rent-cell');
                        if (rentCell) {
                            const rentText = rentCell.textContent.replace(/[$,]/g, '');
                            totalPaid += parseFloat(rentText) || 0;
                        }
                    }
                });
                const totalCell = section.querySelector('.property-total-paid');
                if (totalCell) {
                    totalCell.textContent = '$' + totalPaid.toLocaleString('en-US', {maximumFractionDigits: 0});
                }
            });
        }

        // PDF Receipt Download Function - Creates a professional PDF receipt for each tenant
        function downloadReceipt(btn) {
            const tenantId = btn.getAttribute('data-tenant-id');
            const tenantName = btn.getAttribute('data-tenant-name');
            const tenantUnit = btn.getAttribute('data-tenant-unit');
            const property = btn.getAttribute('data-property');
            const rent = btn.getAttribute('data-rent');
            const isPaid = btn.getAttribute('data-paid') === 'true';

            // Generate folio number (unique identifier)
            const now = new Date();
            const folio = `RC-${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}-${tenantId}`;

            // Format date in Spanish
            const months = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];
            const dateStr = `${now.getDate()} de ${months[now.getMonth()]} de ${now.getFullYear()}`;
            const timeStr = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;

            // Current month/year for billing period
            const billingMonth = months[currentMonth - 1] + ' ' + currentYear;

            // Status text and color
            const statusText = isPaid ? 'PAGADO' : 'PENDIENTE';
            const statusColor = isPaid ? '#0A7A0A' : '#CC0000';
            const statusBg = isPaid ? '#DCFCE7' : '#FEE2E2';

            // Format rent amount
            const rentFormatted = parseFloat(rent).toLocaleString('es-MX', { style: 'currency', currency: 'MXN' });

            // Create PDF content using HTML and print dialog
            const pdfContent = `
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Recibo de Renta - ${tenantName}</title>
                <style>
                    * { margin: 0; padding: 0; box-sizing: border-box; }
                    body {
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                        padding: 40px;
                        color: #333;
                        max-width: 800px;
                        margin: 0 auto;
                    }
                    .header {
                        text-align: center;
                        margin-bottom: 40px;
                        border-bottom: 3px solid #0A7A0A;
                        padding-bottom: 20px;
                    }
                    .logo {
                        font-size: 28px;
                        font-weight: 800;
                        color: #0A7A0A;
                        margin-bottom: 8px;
                    }
                    .subtitle { color: #666; font-size: 14px; }
                    .folio {
                        background: #F5F5F5;
                        padding: 12px 24px;
                        border-radius: 8px;
                        display: inline-block;
                        margin-top: 16px;
                        font-weight: 700;
                        font-size: 14px;
                    }
                    .status-badge {
                        display: inline-block;
                        padding: 12px 32px;
                        border-radius: 8px;
                        font-weight: 800;
                        font-size: 18px;
                        margin: 24px 0;
                        background: ${statusBg};
                        color: ${statusColor};
                        border: 3px solid ${statusColor};
                    }
                    .section { margin: 32px 0; }
                    .section-title {
                        font-size: 14px;
                        color: #666;
                        text-transform: uppercase;
                        letter-spacing: 1px;
                        margin-bottom: 12px;
                    }
                    .info-grid {
                        display: grid;
                        grid-template-columns: 1fr 1fr;
                        gap: 16px;
                    }
                    .info-item {
                        background: #FAFAFA;
                        padding: 16px;
                        border-radius: 8px;
                        border: 1px solid #E5E5E5;
                    }
                    .info-label { font-size: 12px; color: #666; margin-bottom: 4px; }
                    .info-value { font-size: 16px; font-weight: 700; }
                    .amount-section {
                        background: #F5F5F5;
                        padding: 32px;
                        border-radius: 12px;
                        text-align: center;
                        margin: 32px 0;
                    }
                    .amount-label { font-size: 14px; color: #666; margin-bottom: 8px; }
                    .amount-value {
                        font-size: 48px;
                        font-weight: 800;
                        color: ${isPaid ? '#0A7A0A' : '#CC0000'};
                    }
                    .footer {
                        margin-top: 48px;
                        padding-top: 24px;
                        border-top: 2px solid #E5E5E5;
                        text-align: center;
                        color: #999;
                        font-size: 12px;
                    }
                    .timestamp { margin-top: 8px; }
                    @media print {
                        body { padding: 20px; }
                        .no-print { display: none; }
                    }
                </style>
            </head>
            <body>
                <div class="header">
                    <div class="logo">RentasClaras</div>
                    <div class="subtitle">Sistema de Administración de Rentas</div>
                    <div class="folio">Folio: ${folio}</div>
                </div>

                <div style="text-align: center;">
                    <div class="status-badge">${statusText}</div>
                </div>

                <div class="section">
                    <div class="section-title">Datos del Inquilino</div>
                    <div class="info-grid">
                        <div class="info-item">
                            <div class="info-label">Nombre</div>
                            <div class="info-value">${tenantName}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Unidad</div>
                            <div class="info-value">${tenantUnit}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Propiedad</div>
                            <div class="info-value">${property}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Periodo</div>
                            <div class="info-value">${billingMonth}</div>
                        </div>
                    </div>
                </div>

                <div class="amount-section">
                    <div class="amount-label">Monto de Renta</div>
                    <div class="amount-value">${rentFormatted}</div>
                </div>

                <div class="footer">
                    <div>Este documento es un comprobante oficial de RentasClaras</div>
                    <div class="timestamp">Generado el ${dateStr} a las ${timeStr}</div>
                    <div style="margin-top: 16px; color: #0A7A0A; font-weight: 700;">
                        Conserve este recibo para su registro
                    </div>
                </div>

                <div class="no-print" style="text-align: center; margin-top: 32px;">
                    <button onclick="window.print()" style="background: #0A7A0A; color: white; border: none; padding: 16px 32px; border-radius: 8px; font-size: 16px; font-weight: 700; cursor: pointer;">
                        Imprimir / Guardar PDF
                    </button>
                </div>
            </body>
            </html>
            `;

            // Open in new window for printing/saving as PDF
            const printWindow = window.open('', '_blank');
            printWindow.document.write(pdfContent);
            printWindow.document.close();
        }

        // MONTHLY SUMMARY PRINT - Don Raúl requested this for his physical folder
        function printMonthlySummary() {
            // Get current month/year info
            const months = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];
            const monthName = months[currentMonth - 1];
            const now = new Date();
            const dateStr = now.toLocaleDateString('es-MX', { year: 'numeric', month: 'long', day: 'numeric' });
            const timeStr = now.toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit' });

            // Collect tenant data from the page
            let tenantsHTML = '';
            let totalExpected = 0;
            let totalPaid = 0;
            let totalPending = 0;
            let paidCount = 0;
            let pendingCount = 0;

            // Group by property
            const propertySections = document.querySelectorAll('.excel-property-section');

            propertySections.forEach(section => {
                const header = section.querySelector('.excel-table thead th');
                if (!header) return;
                const propertyName = header.textContent.trim();
                if (!propertyName) return;

                let propertyTotal = 0;
                let propertyPaid = 0;
                let propertyHTML = '';

                const rows = section.querySelectorAll('.excel-table tbody tr[data-tenant-id]');
                const sot = getPaymentSOT();

                rows.forEach(row => {
                    const cells = row.querySelectorAll('td');
                    if (cells.length < 6) return;

                    const tenantId = row.dataset.tenantId;
                    const unit = cells[0].textContent.trim();
                    const name = cells[1].textContent.trim().replace('⚠️', '').trim();

                    // Column 2 is the rent-cell, not column 4
                    const rentCell = row.querySelector('.rent-cell');
                    const rentText = rentCell ? rentCell.textContent.replace(/[$,]/g, '').trim() : cells[2].textContent.replace(/[$,]/g, '').trim();
                    const rent = parseFloat(rentText) || 0;

                    // Use SOT as source of truth for paid status, fallback to DOM class
                    let isPaid = false;
                    if (sot.tenants[tenantId]) {
                        isPaid = sot.tenants[tenantId].isPaid;
                    } else {
                        isPaid = row.classList.contains('paid-row');
                    }

                    propertyTotal += rent;
                    if (isPaid) {
                        propertyPaid += rent;
                        paidCount++;
                    } else {
                        pendingCount++;
                    }

                    propertyHTML += `
                        <tr style="${isPaid ? 'background: #f0fff4;' : 'background: #fff5f5;'}">
                            <td style="padding: 8px; border: 1px solid #ddd;">${unit}</td>
                            <td style="padding: 8px; border: 1px solid #ddd;">${name}</td>
                            <td style="padding: 8px; border: 1px solid #ddd; text-align: right;">$${rent.toLocaleString('es-MX')}</td>
                            <td style="padding: 8px; border: 1px solid #ddd; text-align: center; font-weight: 700; color: ${isPaid ? '#0A7A0A' : '#CC0000'};">${isPaid ? '✓ PAGADO' : '✗ PENDIENTE'}</td>
                        </tr>
                    `;
                });

                totalExpected += propertyTotal;
                totalPaid += propertyPaid;
                totalPending += (propertyTotal - propertyPaid);

                tenantsHTML += `
                    <div style="margin-bottom: 24px; page-break-inside: avoid;">
                        <h3 style="background: #0A7A0A; color: white; padding: 10px 16px; margin: 0; border-radius: 8px 8px 0 0;">${propertyName}</h3>
                        <table style="width: 100%; border-collapse: collapse; border: 2px solid #0A7A0A;">
                            <thead>
                                <tr style="background: #f5f5f5;">
                                    <th style="padding: 10px; border: 1px solid #ddd; text-align: left;">Unidad</th>
                                    <th style="padding: 10px; border: 1px solid #ddd; text-align: left;">Inquilino</th>
                                    <th style="padding: 10px; border: 1px solid #ddd; text-align: right;">Renta</th>
                                    <th style="padding: 10px; border: 1px solid #ddd; text-align: center;">Estado</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${propertyHTML}
                            </tbody>
                            <tfoot>
                                <tr style="background: #e8f5e8; font-weight: 700;">
                                    <td colspan="2" style="padding: 10px; border: 1px solid #ddd;">Subtotal ${propertyName}</td>
                                    <td style="padding: 10px; border: 1px solid #ddd; text-align: right;">$${propertyTotal.toLocaleString('es-MX')}</td>
                                    <td style="padding: 10px; border: 1px solid #ddd; text-align: center; color: #0A7A0A;">$${propertyPaid.toLocaleString('es-MX')} cobrados</td>
                                </tr>
                            </tfoot>
                        </table>
                    </div>
                `;
            });

            // Calculate collection percentage
            const collectionPercent = totalExpected > 0 ? Math.round((totalPaid / totalExpected) * 100) : 0;

            // Generate the printable HTML
            const printContent = `
            <!DOCTYPE html>
            <html lang="es">
            <head>
                <meta charset="UTF-8">
                <title>Resumen de Rentas - ${monthName} ${currentYear}</title>
                <style>
                    * { box-sizing: border-box; margin: 0; padding: 0; }
                    body {
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
                        padding: 24px;
                        color: #333;
                        line-height: 1.4;
                    }
                    .header {
                        text-align: center;
                        margin-bottom: 24px;
                        padding-bottom: 16px;
                        border-bottom: 3px solid #0A7A0A;
                    }
                    .logo { font-size: 28px; font-weight: 800; color: #0A7A0A; }
                    .month-title { font-size: 22px; font-weight: 700; margin-top: 8px; }
                    .summary-box {
                        display: flex;
                        justify-content: space-around;
                        background: #f5f5f5;
                        padding: 20px;
                        border-radius: 12px;
                        margin-bottom: 24px;
                        flex-wrap: wrap;
                        gap: 16px;
                    }
                    .summary-item { text-align: center; }
                    .summary-value { font-size: 28px; font-weight: 800; }
                    .summary-value.green { color: #0A7A0A; }
                    .summary-value.red { color: #CC0000; }
                    .summary-value.gray { color: #333; }
                    .summary-label { font-size: 14px; color: #666; margin-top: 4px; }
                    .progress-bar {
                        background: #e0e0e0;
                        border-radius: 8px;
                        height: 24px;
                        margin-bottom: 24px;
                        overflow: hidden;
                    }
                    .progress-fill {
                        background: #0A7A0A;
                        height: 100%;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        color: white;
                        font-weight: 700;
                        font-size: 14px;
                    }
                    .footer {
                        margin-top: 24px;
                        padding-top: 16px;
                        border-top: 2px solid #ddd;
                        text-align: center;
                        color: #666;
                        font-size: 12px;
                    }
                    @media print {
                        body { padding: 12px; }
                        .no-print { display: none; }
                    }
                </style>
            </head>
            <body>
                <div class="header">
                    <div class="logo">🏠 RentasClaras</div>
                    <div class="month-title">Resumen de Rentas — ${monthName} ${currentYear}</div>
                </div>

                <div class="summary-box">
                    <div class="summary-item">
                        <div class="summary-value gray">${paidCount + pendingCount}</div>
                        <div class="summary-label">Total Inquilinos</div>
                    </div>
                    <div class="summary-item">
                        <div class="summary-value green">${paidCount}</div>
                        <div class="summary-label">Pagaron</div>
                    </div>
                    <div class="summary-item">
                        <div class="summary-value red">${pendingCount}</div>
                        <div class="summary-label">Pendientes</div>
                    </div>
                    <div class="summary-item">
                        <div class="summary-value gray">$${totalExpected.toLocaleString('es-MX')}</div>
                        <div class="summary-label">Total Esperado</div>
                    </div>
                    <div class="summary-item">
                        <div class="summary-value green">$${totalPaid.toLocaleString('es-MX')}</div>
                        <div class="summary-label">Cobrado</div>
                    </div>
                    <div class="summary-item">
                        <div class="summary-value red">$${totalPending.toLocaleString('es-MX')}</div>
                        <div class="summary-label">Falta Cobrar</div>
                    </div>
                </div>

                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${collectionPercent}%;">${collectionPercent}% cobrado</div>
                </div>

                ${tenantsHTML}

                <!-- GRAND TOTAL Section -->
                <div style="margin-top: 32px; page-break-inside: avoid;">
                    <table style="width: 100%; border-collapse: collapse; border: 3px solid #0A7A0A; background: linear-gradient(135deg, #f0fff4 0%, #e8f5e8 100%);">
                        <thead>
                            <tr style="background: #0A7A0A;">
                                <th colspan="4" style="padding: 16px; color: white; font-size: 20px; text-align: center; letter-spacing: 1px;">
                                    💰 GRAN TOTAL — ${monthName} ${currentYear}
                                </th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td style="padding: 16px; border: 1px solid #0A7A0A; text-align: center; width: 25%;">
                                    <div style="font-size: 12px; color: #666; text-transform: uppercase;">Total Esperado</div>
                                    <div style="font-size: 24px; font-weight: 800; color: #333;">$${totalExpected.toLocaleString('es-MX')}</div>
                                </td>
                                <td style="padding: 16px; border: 1px solid #0A7A0A; text-align: center; width: 25%; background: #dcfce7;">
                                    <div style="font-size: 12px; color: #0A7A0A; text-transform: uppercase; font-weight: 600;">✓ Total Cobrado</div>
                                    <div style="font-size: 28px; font-weight: 800; color: #0A7A0A;">$${totalPaid.toLocaleString('es-MX')}</div>
                                </td>
                                <td style="padding: 16px; border: 1px solid #0A7A0A; text-align: center; width: 25%; background: #fee2e2;">
                                    <div style="font-size: 12px; color: #CC0000; text-transform: uppercase; font-weight: 600;">✗ Pendiente</div>
                                    <div style="font-size: 24px; font-weight: 800; color: #CC0000;">$${totalPending.toLocaleString('es-MX')}</div>
                                </td>
                                <td style="padding: 16px; border: 1px solid #0A7A0A; text-align: center; width: 25%;">
                                    <div style="font-size: 12px; color: #666; text-transform: uppercase;">% Cobranza</div>
                                    <div style="font-size: 24px; font-weight: 800; color: ${collectionPercent >= 80 ? '#0A7A0A' : collectionPercent >= 50 ? '#F59E0B' : '#CC0000'};">${collectionPercent}%</div>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>

                <div class="footer">
                    <div>Generado por RentasClaras el ${dateStr} a las ${timeStr}</div>
                    <div style="margin-top: 8px; color: #0A7A0A; font-weight: 600;">
                        Conserve este documento para su registro
                    </div>
                </div>

                <div class="no-print" style="text-align: center; margin-top: 32px;">
                    <button onclick="window.print()" style="background: #0A7A0A; color: white; border: none; padding: 16px 32px; border-radius: 8px; font-size: 16px; font-weight: 700; cursor: pointer;">
                        🖨️ Imprimir / Guardar PDF
                    </button>
                </div>
            </body>
            </html>
            `;

            // Open in new window for printing
            const printWindow = window.open('', '_blank');
            printWindow.document.write(printContent);
            printWindow.document.close();
        }

        // Excel Download Function - Creates multi-sheet Excel file matching user's format
        function downloadExcel() {
            // Get all tenant data from the page using SOT as source of truth for paid status
            const tenantsData = {};
            const propertySections = document.querySelectorAll('.excel-property-section');
            const sot = getPaymentSOT();

            // Get month/year from page
            const months = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];
            const monthName = months[currentMonth - 1];

            propertySections.forEach(section => {
                const table = section.querySelector('.excel-table');
                if (!table) return;

                // Get property name from first header
                const headerRow = table.querySelector('thead tr:first-child th');
                if (!headerRow) return;
                const propertyName = headerRow.textContent.trim();

                // Skip the summary section
                if (propertyName === '' || propertyName.includes('GRAN TOTAL')) return;

                const rows = table.querySelectorAll('tbody tr[data-tenant-id]');
                if (rows.length === 0) return;

                tenantsData[propertyName] = [];

                rows.forEach((row, index) => {
                    const cells = row.querySelectorAll('td');
                    if (cells.length < 6) return;

                    const tenantId = row.dataset.tenantId;
                    const name = cells[1].textContent.trim().replace('⚠️', '').trim();

                    // Column 2 is Renta (rent), not "inicia"
                    const rentCell = row.querySelector('.rent-cell');
                    const rentText = rentCell ? rentCell.textContent.replace(/[$,]/g, '').trim() : cells[2].textContent.replace(/[$,]/g, '').trim();
                    const rent = parseFloat(rentText) || 0;

                    // Determine paid status from SOT first, then fall back to DOM state
                    let isPaid = false;
                    if (sot.tenants[tenantId]) {
                        isPaid = sot.tenants[tenantId].isPaid;
                    } else {
                        isPaid = row.classList.contains('paid-row');
                    }

                    // Pagado amount is rent if paid, 0 if unpaid
                    const pagado = isPaid ? rent : 0;

                    // Row label: A, B, C... for some properties, 1, 2, 3... for Ensenada
                    const rowLabel = cells[0].textContent.trim();

                    tenantsData[propertyName].push({
                        label: rowLabel,
                        name: name,
                        rent: rent,
                        pagado: pagado,
                        isPaid: isPaid
                    });
                });
            });

            // Create workbook with SheetJS
            const wb = XLSX.utils.book_new();
            let grandTotals = [];

            // Create a sheet for each property
            Object.keys(tenantsData).forEach(propertyName => {
                const tenants = tenantsData[propertyName];
                if (!tenants || tenants.length === 0) return;

                // Build sheet data matching the user's Excel format
                const sheetData = [];

                // Row 1: RENTAS + Year
                sheetData.push(['', 'RENTAS ' + currentYear, '', '', '', '']);

                // Row 2: Property name
                sheetData.push(['', propertyName, '', '', '', '']);

                // Row 3: Month header
                sheetData.push(['', '', '', 'Renta', 'Pagado', monthName]);

                // Row 4: Column headers
                sheetData.push(['', 'Nombre', '', 'Renta', 'Pagado', 'Estado']);

                // Tenant rows
                let totalRent = 0;
                let totalPagado = 0;

                tenants.forEach(tenant => {
                    sheetData.push([
                        tenant.label,
                        tenant.name,
                        '',  // Empty column
                        tenant.rent,
                        tenant.pagado || '',
                        tenant.isPaid ? 'PAGADO' : 'PENDIENTE'
                    ]);
                    totalRent += tenant.rent;
                    totalPagado += tenant.pagado || 0;
                });

                // Empty row
                sheetData.push([]);

                // Totals row
                sheetData.push(['', 'TOTAL ' + propertyName, '', totalRent, totalPagado, '']);

                // Store for summary sheet
                grandTotals.push({ name: propertyName, total: totalRent, pagado: totalPagado });

                // Create worksheet
                const ws = XLSX.utils.aoa_to_sheet(sheetData);

                // Set column widths
                ws['!cols'] = [
                    { wch: 4 },   // A - row label
                    { wch: 25 },  // B - name
                    { wch: 8 },   // C - empty
                    { wch: 12 },  // D - renta
                    { wch: 12 },  // E - pagado
                    { wch: 12 }   // F - estado
                ];

                // Add sheet to workbook (limit sheet name to 31 chars)
                const sheetName = propertyName.substring(0, 31);
                XLSX.utils.book_append_sheet(wb, ws, sheetName);
            });

            // Create summary sheet
            const summaryData = [
                ['', 'RESUMEN DE RENTAS', '', '', ''],
                ['', monthName + ' ' + currentYear, '', '', ''],
                [],
                ['', 'Propiedad', '', 'Total', 'Cobrado']
            ];

            grandTotals.forEach(item => {
                summaryData.push(['', item.name, '', item.total, item.pagado]);
            });

            // Grand totals
            const grandTotal = grandTotals.reduce((sum, item) => sum + item.total, 0);
            const grandPagado = grandTotals.reduce((sum, item) => sum + item.pagado, 0);
            summaryData.push([]);
            summaryData.push(['', 'GRAN TOTAL', '', grandTotal, grandPagado]);

            // Add percentage collected
            const percentCollected = grandTotal > 0 ? Math.round((grandPagado / grandTotal) * 100) : 0;
            summaryData.push(['', 'Porcentaje cobrado', '', '', percentCollected + '%']);

            const summaryWs = XLSX.utils.aoa_to_sheet(summaryData);
            summaryWs['!cols'] = [
                { wch: 4 },
                { wch: 20 },
                { wch: 8 },
                { wch: 12 },
                { wch: 12 }
            ];
            XLSX.utils.book_append_sheet(wb, summaryWs, 'Resumen');

            // Generate filename with month and year
            const filename = 'Rentas_' + monthName + '_' + currentYear + '.xlsx';

            // Download the file
            XLSX.writeFile(wb, filename);

            console.log('✅ Excel downloaded:', filename, 'Totals:', grandTotals);
        }

        // UX #1: Confirmation Modal State
        let pendingConfirmAction = null;
        let pendingConfirmBtn = null;

        // Get tenant info for modal context
        function getTenantInfoFromBtn(btn) {
            const item = btn.closest('.tenant-item') || btn.closest('tr[data-tenant-id]');
            if (!item) return { name: '', amount: '', month: '' };

            const tenantId = item.dataset.tenantId;

            // Try to get name
            let name = '';
            const nameEl = item.querySelector('.tenant-name');
            if (nameEl) {
                name = nameEl.textContent.trim();
            } else {
                // From table view
                const nameCell = item.querySelector('td:nth-child(2)');
                if (nameCell) name = nameCell.textContent.trim();
            }

            // Try to get amount
            let amount = '';
            const rentEl = item.querySelector('.tenant-rent');
            if (rentEl) {
                amount = rentEl.textContent.trim();
            } else {
                const rentCell = item.querySelector('.rent-cell');
                if (rentCell) amount = rentCell.textContent.trim();
            }

            // Get current month from page
            const monthEl = document.querySelector('[style*="text-transform: capitalize"]');
            const month = monthEl ? monthEl.textContent.trim() : '';

            return { name, amount, month };
        }

        function showConfirmModal(title, message, icon, actionType, btn) {
            const modal = document.getElementById('confirmModal');
            const titleEl = document.getElementById('confirmTitle');
            const messageEl = document.getElementById('confirmMessage');
            const iconEl = document.getElementById('confirmIcon');
            const confirmBtn = document.getElementById('confirmBtn');

            // Get tenant context
            const tenantInfo = getTenantInfoFromBtn(btn);
            const tenantNameEl = document.getElementById('confirmTenantName');
            const monthYearEl = document.getElementById('confirmMonthYear');
            const amountEl = document.getElementById('confirmAmount');
            const contextEl = document.getElementById('confirmContext');

            titleEl.textContent = title;
            messageEl.textContent = message;
            iconEl.textContent = icon;

            // Populate context if we have tenant info
            if (tenantInfo.name && tenantNameEl) {
                tenantNameEl.textContent = tenantInfo.name;
                monthYearEl.textContent = tenantInfo.month;
                amountEl.textContent = tenantInfo.amount;
                if (contextEl) contextEl.style.display = 'block';
            } else if (contextEl) {
                contextEl.style.display = 'none';
            }

            // Update button style based on action type
            confirmBtn.className = actionType === 'paid' ? 'btn-confirm-paid' : 'btn-confirm-unpaid';
            confirmBtn.textContent = actionType === 'paid' ? 'Sí, pagó' : 'Marcar pendiente';

            pendingConfirmBtn = btn;
            pendingConfirmAction = actionType;

            modal.classList.add('show');
        }

        function closeConfirmModal() {
            const modal = document.getElementById('confirmModal');
            modal.classList.remove('show');
            pendingConfirmAction = null;
            pendingConfirmBtn = null;
        }

        function executeConfirmedAction() {
            if (pendingConfirmBtn) {
                executeTogglePaid(pendingConfirmBtn);
            }
            closeConfirmModal();
        }

        // #1 & #3: Toggle paid status - DIRECT toggle like contratos (no modal)
        function togglePaid(btn) {
            // Execute toggle directly - no confirmation needed
            executeTogglePaid(btn);
        }

        // NEW: Two-button payment status system (like Contratos renewal buttons)
        function setPaymentStatus(btn, tenantId, isPaid) {
            const item = btn.closest('.tenant-item');
            if (!item) {
                console.error('Could not find tenant-item for button');
                return;
            }

            const container = btn.closest('.payment-buttons');
            const checkbox = item.querySelector('.tenant-checkbox');
            const paymentSelect = item.querySelector('.payment-method');
            const tenantName = item.querySelector('.tenant-name')?.textContent?.trim() || 'Inquilino';
            const rentText = item.querySelector('.tenant-rent')?.textContent || '$0';

            // 1. UPDATE SOT FIRST (Single Source of Truth)
            updatePaymentSOT(tenantId, isPaid, paymentSelect?.value || null);

            // Update button states
            container.querySelectorAll('.payment-btn').forEach(b => {
                b.classList.remove('active-green', 'active-red');
            });

            // Set active state
            if (isPaid) {
                btn.classList.add('active-green');
                item.classList.add('paid');
                if (checkbox) checkbox.checked = false;
                if (paymentSelect) paymentSelect.disabled = false;
                updateWhatsAppButton(item, true);
                showPersistentConfirmation(`¡${tenantName} PAGÓ! ${rentText}`, 'paid');

                // Auto-show details to show payment method selector
                const details = item.querySelector('.tenant-details');
                if (details && !details.classList.contains('show')) {
                    details.classList.add('show');
                    if (paymentSelect) {
                        setTimeout(() => {
                            paymentSelect.scrollIntoView({ behavior: 'smooth', block: 'center' });
                            paymentSelect.focus();
                        }, 200);
                    }
                }
            } else {
                btn.classList.add('active-red');
                item.classList.remove('paid');
                if (checkbox) checkbox.checked = true;
                if (paymentSelect) {
                    paymentSelect.disabled = true;
                    paymentSelect.value = '';
                }
                updateWhatsAppButton(item, false);
                showPersistentConfirmation(`${tenantName} marcado como PENDIENTE`, 'unpaid');
            }

            // Update last saved immediately for instant user feedback
            updateLastSaved();

            // BUGFIX: Cancel any existing request for this tenant to prevent duplicates
            if (inFlightRequests.has(tenantId)) {
                inFlightRequests.get(tenantId).abort();
            }

            const controller = new AbortController();
            inFlightRequests.set(tenantId, controller);

            // Save to database
            fetch('/api/payment', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    tenant_id: tenantId,
                    paid: isPaid,
                    payment_method: paymentSelect?.value || null,
                    year: currentYear,
                    month: currentMonth
                }),
                signal: controller.signal
            }).then(response => {
                inFlightRequests.delete(tenantId);
                if (response.ok) {
                    console.log(`Guardado: ${tenantId} = ${isPaid ? 'pagado' : 'pendiente'}`);
                }
            }).catch(err => {
                inFlightRequests.delete(tenantId);
                if (err.name === 'AbortError') {
                    console.log('Previous request cancelled for tenant:', tenantId);
                    return;
                }
                console.error('Error guardando, guardando localmente:', err);
                const queue = JSON.parse(localStorage.getItem('pendingPayments') || '[]');
                // BUGFIX: Deduplicate queue - only keep latest entry per tenant
                const filteredQueue = queue.filter(item => item.tenantId !== tenantId);
                filteredQueue.push({ tenantId: tenantId, paid: isPaid, year: currentYear, month: currentMonth, timestamp: Date.now() });
                localStorage.setItem('pendingPayments', JSON.stringify(filteredQueue));
                showPersistentConfirmation('Guardado localmente (sin conexión)', 'warning');
            });

            // Sync table view with card view state
            syncTableView(tenantId, isPaid);

            updateCounts();
        }

        // NEW: Toggle switch payment status handler with CONFIRMATION
        // Don Raúl requested: "¿Estás seguro?" before changing status
        function togglePaymentStatus(toggle, tenantId) {
            console.log('🔘 togglePaymentStatus called:', { toggle, tenantId, checked: toggle?.checked });

            try {
                const isPaid = toggle.checked;
                const item = toggle.closest('.tenant-item');
                if (!item) {
                    console.error('❌ Could not find tenant-item for toggle');
                    return;
                }

                const tenantName = item.querySelector('.tenant-name')?.textContent?.trim() || 'Inquilino';
                const rentText = item.querySelector('.tenant-rent')?.textContent || '$0';
                console.log('📊 Toggle details:', { tenantId, tenantName, rentText, isPaid });

                // REVERT the toggle immediately - wait for confirmation
                toggle.checked = !isPaid;

                // Show confirmation modal
                showPaymentConfirmModal(tenantId, tenantName, rentText, isPaid, toggle, item);
            } catch (error) {
                console.error('🚨 Error in togglePaymentStatus:', error);
            }
        }

        // Show confirmation modal for payment status change
        function showPaymentConfirmModal(tenantId, tenantName, rentText, markAsPaid, toggle, item) {
            console.log('📋 showPaymentConfirmModal called:', { tenantId, tenantName, markAsPaid });

            try {
                const modal = document.getElementById('confirmModal');
                const icon = document.getElementById('confirmIcon');
                const title = document.getElementById('confirmTitle');
                const tenantNameEl = document.getElementById('confirmTenantName');
                const monthYearEl = document.getElementById('confirmMonthYear');
                const amountEl = document.getElementById('confirmAmount');
                const message = document.getElementById('confirmMessage');
                const confirmBtn = document.getElementById('confirmBtn');

                if (!modal) {
                    console.error('❌ Confirmation modal not found!');
                    return;
                }

                // Set content based on action
                if (markAsPaid) {
                    icon.textContent = '💰';
                    title.textContent = '¿Confirmar PAGO?';
                    message.textContent = '¿Está seguro que este inquilino YA PAGÓ?';
                    confirmBtn.textContent = '✓ Sí, Ya Pagó';
                    confirmBtn.className = 'btn-confirm-paid';
                } else {
                    icon.textContent = '⚠️';
                    title.textContent = '¿Marcar como NO PAGADO?';
                    message.textContent = '¿Está seguro que este inquilino NO HA PAGADO?';
                    confirmBtn.textContent = '✗ Marcar Pendiente';
                    confirmBtn.className = 'btn-confirm-unpaid';
                }

                // Set context
                tenantNameEl.textContent = tenantName;
                monthYearEl.textContent = `${monthName} ${currentYear}`;
                amountEl.textContent = rentText;

                // Store pending action for execution
                pendingConfirmAction = {
                    type: 'payment',
                    tenantId: tenantId,
                    markAsPaid: markAsPaid,
                    toggle: toggle,
                    item: item
                };

                // Show modal
                modal.classList.add('show');
                console.log('✅ Confirmation modal shown');
            } catch (error) {
                console.error('🚨 Error in showPaymentConfirmModal:', error);
            }
        }

        // Close confirmation modal
        function closeConfirmModal() {
            const modal = document.getElementById('confirmModal');
            modal.classList.remove('show');
            pendingConfirmAction = null;
        }

        // Execute the confirmed action
        function executeConfirmedAction() {
            if (!pendingConfirmAction) return;

            const { type, tenantId, markAsPaid, toggle, item } = pendingConfirmAction;

            if (type === 'payment') {
                // Close modal first
                closeConfirmModal();

                // Now execute the actual payment status change
                executePaymentStatusChange(tenantId, markAsPaid, toggle, item);
            }
        }

        // Execute the actual payment status change (after confirmation)
        function executePaymentStatusChange(tenantId, isPaid, toggle, item) {
            // BUGFIX #9: Prevent double-clicks with toggleInProgress
            if (toggleInProgress.has(tenantId)) {
                console.log('Toggle already in progress for', tenantId);
                return;
            }
            toggleInProgress.add(tenantId);

            // Now actually update the toggle
            toggle.checked = isPaid;

            const checkbox = item.querySelector('.tenant-checkbox');
            const paymentSelect = item.querySelector('.payment-method');
            const tenantName = item.querySelector('.tenant-name')?.textContent?.trim() || 'Inquilino';
            const rentText = item.querySelector('.tenant-rent')?.textContent || '$0';
            const toggleLabel = item.querySelector('.payment-toggle-label');

            // 1. UPDATE SOT FIRST (Single Source of Truth)
            updatePaymentSOT(tenantId, isPaid, paymentSelect?.value || null);

            // Update toggle label
            if (toggleLabel) {
                toggleLabel.textContent = isPaid ? 'Ya pagó' : 'No ha pagado';
                toggleLabel.classList.remove('paid', 'unpaid');
                toggleLabel.classList.add(isPaid ? 'paid' : 'unpaid');
            }

            // Update item state
            if (isPaid) {
                item.classList.add('paid');
                if (checkbox) checkbox.checked = false;
                if (paymentSelect) paymentSelect.disabled = false;
                updateWhatsAppButton(item, true);
                showPersistentConfirmation(`¡${tenantName} PAGÓ! ${rentText}`, 'paid');

                // Auto-show details to show payment method selector
                const details = item.querySelector('.tenant-details');
                if (details && !details.classList.contains('show')) {
                    details.classList.add('show');
                    if (paymentSelect) {
                        setTimeout(() => {
                            paymentSelect.scrollIntoView({ behavior: 'smooth', block: 'center' });
                            paymentSelect.focus();
                        }, 200);
                    }
                }
            } else {
                item.classList.remove('paid');
                if (checkbox) checkbox.checked = true;
                if (paymentSelect) {
                    paymentSelect.disabled = true;
                    paymentSelect.value = '';
                }
                updateWhatsAppButton(item, false);
                showPersistentConfirmation(`${tenantName} marcado como PENDIENTE`, 'unpaid');
            }

            // Update last saved immediately for instant user feedback
            updateLastSaved();

            // BUGFIX: Cancel any existing request for this tenant to prevent duplicates
            if (inFlightRequests.has(tenantId)) {
                inFlightRequests.get(tenantId).abort();
            }

            const controller = new AbortController();
            inFlightRequests.set(tenantId, controller);

            // 2. Save to database
            fetch('/api/payment', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    tenant_id: tenantId,
                    paid: isPaid,
                    payment_method: paymentSelect?.value || null,
                    year: currentYear,
                    month: currentMonth
                }),
                signal: controller.signal
            }).then(response => {
                inFlightRequests.delete(tenantId);
                toggleInProgress.delete(tenantId);
                if (response.ok) {
                    console.log(`Guardado: ${tenantId} = ${isPaid ? 'pagado' : 'pendiente'}`);
                }
            }).catch(err => {
                inFlightRequests.delete(tenantId);
                toggleInProgress.delete(tenantId);
                if (err.name === 'AbortError') {
                    console.log('Previous request cancelled for tenant:', tenantId);
                    return;
                }
                console.error('Error guardando, guardando localmente:', err);
                const queue = JSON.parse(localStorage.getItem('pendingPayments') || '[]');
                // BUGFIX: Deduplicate queue - only keep latest entry per tenant
                const filteredQueue = queue.filter(item => item.tenantId !== tenantId);
                filteredQueue.push({ tenantId: tenantId, paid: isPaid, year: currentYear, month: currentMonth, timestamp: Date.now() });
                localStorage.setItem('pendingPayments', JSON.stringify(filteredQueue));
                showPersistentConfirmation('Guardado localmente (sin conexión)', 'warning');
            });

            // 3. Sync table view with card view state
            syncTableView(tenantId, isPaid);

            updateCounts();
        }

        // Execute the actual toggle after confirmation
        function executeTogglePaid(btn) {
            const item = btn.closest('.tenant-item');
            if (!item) {
                console.error('Could not find tenant-item for button');
                return;
            }

            const checkbox = item.querySelector('.tenant-checkbox');
            if (!checkbox) {
                console.error('Could not find checkbox for tenant');
                return;
            }

            const paymentSelect = item.querySelector('.payment-method');
            const tenantId = btn.dataset.tenantId;
            const tenantName = item.querySelector('.tenant-name')?.textContent?.trim() || 'Inquilino';
            const rentText = item.querySelector('.tenant-rent')?.textContent || '$0';

            // Show loading state on button
            const originalHtml = btn.innerHTML;
            btn.innerHTML = '<span class="loading-spinner"></span> Guardando...';
            btn.classList.add('btn-loading');

            // Toggle the hidden checkbox
            checkbox.checked = !checkbox.checked;

            // Determine new paid status (checked = NOT paid, needs reminder)
            const isPaid = !checkbox.checked;

            // 1. UPDATE SOT FIRST (Single Source of Truth)
            updatePaymentSOT(tenantId, isPaid, paymentSelect?.value || null);

            // Update the button appearance
            if (checkbox.checked) {
                // Now UNPAID (will receive reminder)
                btn.className = 'status-pill status-pill--full-width tenant-status-btn unpaid';
                btn.innerHTML = '<span class="icon"></span><span class="label">No ha pagado</span>';
                item.classList.remove('paid');
                if (paymentSelect) {
                    paymentSelect.disabled = true;
                    paymentSelect.value = '';
                }
                updateWhatsAppButton(item, false);
                // #1: Show PERSISTENT confirmation (no blinking)
                showPersistentConfirmation(`${tenantName} marcado como PENDIENTE`, 'unpaid');
            } else {
                // Now PAID (won't receive reminder)
                btn.className = 'status-pill status-pill--full-width tenant-status-btn paid';
                btn.innerHTML = '<span class="icon"></span><span class="label">Ya pagó</span>';
                item.classList.add('paid');
                if (paymentSelect) {
                    paymentSelect.disabled = false;
                }
                updateWhatsAppButton(item, true);
                // #1: Show PERSISTENT confirmation (no blinking)
                showPersistentConfirmation(`¡${tenantName} PAGÓ! ${rentText}`, 'paid');

                // #9: Auto-show details to show payment method selector
                const details = item.querySelector('.tenant-details');
                if (details && !details.classList.contains('show')) {
                    details.classList.add('show');
                    // Scroll to the payment method selector
                    if (paymentSelect) {
                        setTimeout(() => {
                            paymentSelect.scrollIntoView({ behavior: 'smooth', block: 'center' });
                            paymentSelect.focus();
                        }, 200);
                    }
                }
            }

            // Update last saved immediately for instant user feedback
            updateLastSaved();

            // BUGFIX: Cancel any existing request for this tenant to prevent duplicates
            if (inFlightRequests.has(tenantId)) {
                inFlightRequests.get(tenantId).abort();
            }

            const controller = new AbortController();
            inFlightRequests.set(tenantId, controller);

            // 2. Save to database with loading state
            fetch('/api/payment', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    tenant_id: tenantId,
                    paid: isPaid,
                    payment_method: paymentSelect.value || null,
                    year: currentYear,
                    month: currentMonth
                }),
                signal: controller.signal
            }).then(response => {
                inFlightRequests.delete(tenantId);
                if (response.ok) {
                    console.log(`Guardado: ${tenantId} = ${isPaid ? 'pagado' : 'pendiente'}`);
                }
            }).catch(err => {
                inFlightRequests.delete(tenantId);
                if (err.name === 'AbortError') {
                    console.log('Previous request cancelled for tenant:', tenantId);
                    return;
                }
                console.error('Error guardando, guardando localmente:', err);
                // BUGFIX: Deduplicate queue - only keep latest entry per tenant
                const queue = JSON.parse(localStorage.getItem('pendingPayments') || '[]');
                const filteredQueue = queue.filter(item => item.tenantId !== tenantId);
                filteredQueue.push({ tenantId: tenantId, paid: isPaid, year: currentYear, month: currentMonth, timestamp: Date.now() });
                localStorage.setItem('pendingPayments', JSON.stringify(filteredQueue));
                showPersistentConfirmation('Guardado localmente (sin conexión)', 'warning');
            });

            // 3. Sync table view with card view state
            syncTableView(tenantId, isPaid);

            updateCounts();
        }

        function updateCounts() {
            const checkboxes = document.querySelectorAll('.tenant-checkbox');
            let pending = 0;
            let paid = 0;
            let paidAmount = 0;
            let totalAmount = 0;
            let pendingBaseRent = 0;  // Track base rent only (without late fees) for top banner

            // Track per-property counts and amounts
            const propertyPaidCounts = {};
            const propertyPendingCounts = {};
            const propertyPaidAmounts = {};

            checkboxes.forEach(cb => {
                const propertyName = cb.dataset.property;
                const item = cb.closest('.tenant-item');
                const rentText = item.querySelector('.tenant-rent')?.textContent || '$0';
                const rent = parseFloat(rentText.replace(/[$,]/g, '')) || 0;

                // Get base rent from data attribute (without late fees)
                const tenantAmountEl = item.querySelector('.tenant-amount');
                const baseRent = parseFloat(tenantAmountEl?.dataset.baseRent) || rent;

                totalAmount += rent;

                if (!propertyPaidCounts[propertyName]) {
                    propertyPaidCounts[propertyName] = 0;
                    propertyPaidAmounts[propertyName] = 0;
                }
                if (!propertyPendingCounts[propertyName]) {
                    propertyPendingCounts[propertyName] = 0;
                }

                if (cb.checked) {
                    pending++;
                    propertyPendingCounts[propertyName]++;
                    pendingBaseRent += baseRent;  // Add base rent only for pending tenants
                } else {
                    paid++;
                    paidAmount += rent;
                    propertyPaidCounts[propertyName]++;
                    propertyPaidAmounts[propertyName] += rent;
                }
            });

            // Update property paid counters
            Object.keys(propertyPaidCounts).forEach(propName => {
                const paidCounter = document.querySelector(`[data-property-paid="${propName}"]`);
                if (paidCounter) {
                    paidCounter.textContent = `${propertyPaidCounts[propName]} pagaron`;
                }

                const pendingCounter = document.querySelector(`[data-property-pending="${propName}"]`);
                if (pendingCounter) {
                    pendingCounter.textContent = `${propertyPendingCounts[propName]} pendientes`;
                }

                // Get property total from data attribute
                const propertySection = document.querySelector(`.property-section[data-property="${propName}"]`);
                const propertyTotal = propertySection ? parseFloat(propertySection.dataset.propertyTotal) || 0 : 0;
                const propertyPaidAmount = propertyPaidAmounts[propName] || 0;
                const propertyPendingAmount = propertyTotal - propertyPaidAmount;

                // Update subtotal amounts (with peso values)
                const subtotalAmountPaid = document.querySelector(`[data-subtotal-amount-paid="${propName}"]`);
                if (subtotalAmountPaid) {
                    subtotalAmountPaid.textContent = `$${propertyPaidAmount.toLocaleString()} cobrados`;
                }

                const subtotalAmountPending = document.querySelector(`[data-subtotal-amount-pending="${propName}"]`);
                if (subtotalAmountPending) {
                    subtotalAmountPending.textContent = `$${propertyPendingAmount.toLocaleString()} pendientes`;
                }

                // Update old subtotal counters (for hidden elements)
                const subtotalPaid = document.querySelector(`[data-subtotal-paid="${propName}"]`);
                if (subtotalPaid) {
                    subtotalPaid.textContent = `${propertyPaidCounts[propName]} pagados`;
                }

                const subtotalPending = document.querySelector(`[data-subtotal-pending="${propName}"]`);
                if (subtotalPending) {
                    subtotalPending.textContent = `${propertyPendingCounts[propName]} pendientes`;
                }
            });

            document.getElementById('pendingCount').textContent = pending;
            document.getElementById('paidCount').textContent = paid;
            document.getElementById('selectedCount').textContent = pending;

            // Update grand total breakdown (pending/paid amounts)
            const pendingAmount = totalAmount - paidAmount;

            const grandTotalPending = document.getElementById('grandTotalPending');
            const grandTotalPaid = document.getElementById('grandTotalPaid');
            const collectionRateStat = document.getElementById('collectionRate');

            if (grandTotalPending) {
                grandTotalPending.textContent = `$${pendingAmount.toLocaleString()} MXN`;
            }
            if (grandTotalPaid) {
                grandTotalPaid.textContent = `$${paidAmount.toLocaleString()} MXN`;
            }

            // Update collection rate progress bar
            const progressBar = document.getElementById('collectionProgressBar');
            const progressText = document.getElementById('collectionProgressText');
            const percentageLabel = document.getElementById('collectionPercentage');

            if (progressBar && totalAmount > 0) {
                const percentage = Math.round((paidAmount / totalAmount) * 100);
                progressBar.style.width = `${percentage}%`;

                // Update percentage label
                if (percentageLabel) {
                    percentageLabel.textContent = `${percentage}%`;
                }

                // Update collection rate stat in grand total
                if (collectionRateStat) {
                    collectionRateStat.textContent = `${percentage}% cobrado`;
                }

                // Show text inside bar only if there's enough space (>15%)
                if (progressText) {
                    if (percentage >= 15) {
                        progressText.textContent = `$${paidAmount.toLocaleString()}`;
                    } else {
                        progressText.textContent = '';
                    }
                }

                // Add 'complete' class when 100%
                if (percentage === 100) {
                    progressBar.classList.add('complete');
                    // #11: CELEBRATION at 100%!
                    triggerCelebration();
                } else {
                    progressBar.classList.remove('complete');
                }
            }

            // #8: Update TOP "Falta Cobrar" section (base rent only, without late fees)
            const faltaCobrarTop = document.getElementById('faltaCobrarTop');
            const faltaPersonasTop = document.getElementById('faltaPersonasTop');
            if (faltaCobrarTop) {
                faltaCobrarTop.textContent = `$${pendingBaseRent.toLocaleString()} MXN`;
            }
            if (faltaPersonasTop) {
                faltaPersonasTop.textContent = `de ${pending} personas`;
            }

            // UX #3: Update property filter tab counts (use debounced version for performance)
            debouncedUpdatePropertyFilterCounts();
        }

        // #1: PERSISTENT CONFIRMATION function (no blinking, solid green/red)
        function showPersistentConfirmation(message, type) {
            const toast = document.getElementById('undoToast');
            const messageEl = document.getElementById('undoMessage');

            if (!toast || !messageEl) return;

            messageEl.textContent = message;

            // Color based on type
            if (type === 'paid') {
                toast.style.background = '#0A7A0A';
            } else if (type === 'unpaid') {
                toast.style.background = '#CC0000';
            } else {
                toast.style.background = '#333333';
            }

            toast.classList.add('show');

            // Hide after 3 seconds
            setTimeout(() => {
                toast.classList.remove('show');
            }, 3000);
        }

        // #11: CELEBRATION with confetti when 100% collected
        let celebrationShown = false;
        function triggerCelebration() {
            if (celebrationShown) return;
            celebrationShown = true;

            // Show celebration banner
            const banner = document.getElementById('celebrationBanner');
            if (banner) {
                banner.classList.add('show');
                setTimeout(() => {
                    banner.classList.remove('show');
                }, 4000);
            }

            // Create confetti
            const container = document.getElementById('confettiContainer');
            if (!container) return;

            const colors = ['#0A7A0A', '#CC0000', '#FFD700', '#FF6B6B', '#4ECDC4'];

            for (let i = 0; i < 50; i++) {
                setTimeout(() => {
                    const confetti = document.createElement('div');
                    confetti.className = 'confetti';
                    confetti.style.left = Math.random() * 100 + '%';
                    confetti.style.top = '-20px';
                    confetti.style.background = colors[Math.floor(Math.random() * colors.length)];
                    confetti.style.borderRadius = Math.random() > 0.5 ? '50%' : '0';
                    confetti.style.opacity = '1';
                    container.appendChild(confetti);

                    // Animate falling
                    const duration = 2000 + Math.random() * 2000;
                    const endX = (Math.random() - 0.5) * 200;
                    confetti.animate([
                        { transform: 'translateY(0) rotate(0deg)', opacity: 1 },
                        { transform: `translateY(100vh) translateX(${endX}px) rotate(720deg)`, opacity: 0 }
                    ], {
                        duration: duration,
                        easing: 'ease-out'
                    });

                    // Remove after animation
                    setTimeout(() => confetti.remove(), duration);
                }, i * 50);
            }

            // Reset after 10 seconds so it can trigger again if user changes things
            setTimeout(() => {
                celebrationShown = false;
            }, 10000);
        }

        // =============================================
        // UX #3: Property Filter Tabs
        // =============================================

        // BUGFIX: Debounce helper to prevent DOM thrashing on rapid updates
        let filterCountTimer = null;
        function debouncedUpdatePropertyFilterCounts() {
            if (filterCountTimer) {
                clearTimeout(filterCountTimer);
            }
            filterCountTimer = setTimeout(() => {
                updatePropertyFilterCounts();
            }, 100);
        }

        let activePropertyFilter = 'all';

        function filterByProperty(propertyName, btn) {
            console.log('filterByProperty called with:', propertyName);
            activePropertyFilter = propertyName;

            // Update tab active states and styles (green active, same as contratos)
            const allTabs = document.querySelectorAll('.property-filter-tab');
            allTabs.forEach(tab => {
                tab.classList.remove('active');
                tab.style.background = 'transparent';
                tab.style.color = '#333333';
            });
            btn.classList.add('active');
            btn.style.background = '#0A7A0A';
            btn.style.color = 'white';

            // BUGFIX: Re-apply search filter if active (don't clear user's search)
            const searchInput = document.getElementById('tenantSearch');
            const hadSearch = searchInput && searchInput.value;

            // Temporarily clear search visibility results but keep the value
            if (hadSearch) {
                document.getElementById('searchResults').style.display = 'none';
            }

            // Filter card view
            const allItems = document.querySelectorAll('.tenant-item');
            const allSections = document.querySelectorAll('.property-section');

            // Filter excel view
            const excelSections = document.querySelectorAll('.excel-property-section');

            if (propertyName === 'all') {
                // Show all
                allItems.forEach(item => item.style.display = 'flex');
                allSections.forEach(section => section.style.display = 'block');
                excelSections.forEach(section => section.style.display = 'block');
            } else {
                // Filter by property (use includes for partial matching like Contratos)
                allItems.forEach(item => {
                    const itemProperty = item.dataset.property || '';
                    item.style.display = itemProperty.includes(propertyName) ? 'flex' : 'none';
                });

                allSections.forEach(section => {
                    const sectionProperty = section.dataset.property || '';
                    section.style.display = sectionProperty.includes(propertyName) ? 'block' : 'none';
                });

                // For Excel view, hide non-matching sections
                excelSections.forEach(section => {
                    const sectionTable = section.querySelector('.excel-table');
                    if (sectionTable) {
                        const headerRow = sectionTable.querySelector('thead tr:first-child th');
                        if (headerRow) {
                            const headerText = headerRow.textContent.trim();
                            section.style.display = headerText.includes(propertyName) ? 'block' : 'none';
                        }
                    }
                });
            }

            // BUGFIX: Sync visible items between card and table views after filtering
            // This ensures payment state is consistent when switching tabs
            allItems.forEach(item => {
                // Only sync visible items to avoid unnecessary DOM updates
                if (item.style.display !== 'none') {
                    const tenantId = item.dataset.tenantId;
                    const isPaid = item.classList.contains('paid');
                    syncTableView(tenantId, isPaid);
                }
            });

            // Update counts display
            updatePropertyFilterCounts();

            // BUGFIX: Re-apply search filter if user had one active
            if (hadSearch) {
                setTimeout(() => {
                    filterTenants(searchInput.value);
                }, 10);
            }
        }

        function updatePropertyFilterCounts() {
            // Get counts per property
            const allItems = document.querySelectorAll('.tenant-item');
            const propertyCounts = {};
            let totalPending = 0;

            allItems.forEach(item => {
                const property = item.dataset.property;
                // BUGFIX: Use checkbox state as source of truth instead of .paid class
                // checkbox.checked=true means PENDING, false means PAID (inverted logic)
                const checkbox = item.querySelector('.tenant-checkbox');
                const isPaid = checkbox ? !checkbox.checked : item.classList.contains('paid');

                if (!propertyCounts[property]) {
                    propertyCounts[property] = { total: 0, pending: 0 };
                }

                propertyCounts[property].total++;
                if (!isPaid) {
                    propertyCounts[property].pending++;
                    totalPending++;
                }
            });

            // Update tab badges
            const allTabCount = document.getElementById('tabCountAll');
            if (allTabCount) {
                allTabCount.textContent = totalPending > 0 ? `${totalPending} pendientes` : '✓ Todos pagaron';
            }

            Object.keys(propertyCounts).forEach(propName => {
                const tabCount = document.querySelector(`[data-tab-count="${propName}"]`);
                if (tabCount) {
                    const pending = propertyCounts[propName].pending;
                    tabCount.textContent = pending > 0 ? `${pending} pendientes` : '✓';
                }
            });
        }

        // =============================================
        // Search/Filter Tenants
        // =============================================

        function filterTenants(searchTerm) {
            const clearBtn = document.getElementById('clearSearch');
            const resultsDiv = document.getElementById('searchResults');
            const term = (searchTerm || '').toLowerCase().trim();

            // Show/hide clear button
            if (clearBtn) {
                clearBtn.style.display = term ? 'block' : 'none';
            }

            // Filter card view
            const allItems = document.querySelectorAll('.tenant-item');
            const allSections = document.querySelectorAll('.property-section');

            // Filter excel view rows
            const allRows = document.querySelectorAll('.excel-table tbody tr');

            if (!term) {
                // Show all tenants and sections
                allItems.forEach(item => item.style.display = 'flex');
                allSections.forEach(section => section.style.display = 'block');
                allRows.forEach(row => row.style.display = '');
                // Also show all Excel property sections
                const excelSections = document.querySelectorAll('.excel-property-section');
                excelSections.forEach(section => section.style.display = 'block');
                if (resultsDiv) resultsDiv.style.display = 'none';
                return;
            }

            let matchCount = 0;
            const propertyVisibility = {};

            // Filter card view
            allItems.forEach(item => {
                const checkbox = item.querySelector('.tenant-checkbox');
                if (!checkbox) return;
                const name = (checkbox.dataset.name || '').toLowerCase();
                const property = checkbox.dataset.property;

                if (name.includes(term)) {
                    item.style.display = 'flex';
                    matchCount++;
                    propertyVisibility[property] = true;
                } else {
                    item.style.display = 'none';
                }
            });

            // Filter excel view
            allRows.forEach(row => {
                const nameCell = row.querySelector('td:nth-child(2)');
                if (!nameCell) return;
                const name = nameCell.textContent.toLowerCase();

                if (name.includes(term)) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });

            // Hide property sections with no visible tenants (card view)
            allSections.forEach(section => {
                const propertyName = section.dataset.property;
                section.style.display = propertyVisibility[propertyName] ? 'block' : 'none';
            });

            // Hide Excel property sections with no visible tenants
            const excelPropertySections = document.querySelectorAll('.excel-property-section');
            excelPropertySections.forEach(section => {
                const visibleRows = section.querySelectorAll('tr[data-tenant-id]');
                let hasVisible = false;
                visibleRows.forEach(row => {
                    if (row.style.display !== 'none') {
                        hasVisible = true;
                    }
                });
                section.style.display = hasVisible ? 'block' : 'none';
            });

            // Show results count
            resultsDiv.style.display = 'block';
            if (matchCount === 0) {
                resultsDiv.innerHTML = `No se encontró "<strong>${searchTerm}</strong>"`;
            } else if (matchCount === 1) {
                resultsDiv.innerHTML = `1 inquilino encontrado`;
            } else {
                resultsDiv.innerHTML = `${matchCount} inquilinos encontrados`;
            }
        }

        function clearSearch() {
            const searchInput = document.getElementById('tenantSearch');
            searchInput.value = '';
            filterTenants('');
            searchInput.focus();
        }

        function updatePaymentMethod(select) {
            const item = select.closest('.tenant-item');
            const tenantId = item.dataset.tenantId;
            const method = select.value;

            if (method && tenantId) {
                // UPDATE SOT with the payment method
                updatePaymentSOT(tenantId, true, method);

                fetch('/api/payment', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        tenant_id: tenantId,
                        paid: true,
                        payment_method: method,
                        year: currentYear,
                        month: currentMonth
                    })
                }).then(response => {
                    if (response.ok) {
                        console.log(`Método guardado: ${tenantId} = ${method}`);
                        updateLastSaved();
                    }
                });
            }
        }

        function markAllUnpaid() {
            // Get all tenant IDs from both card and table views
            const allTenantIds = new Set();

            // Collect from card view
            document.querySelectorAll('.tenant-item').forEach(item => {
                if (item.dataset.tenantId) allTenantIds.add(item.dataset.tenantId);
            });

            // Collect from table view
            document.querySelectorAll('tr[data-tenant-id]').forEach(row => {
                if (row.dataset.tenantId) allTenantIds.add(row.dataset.tenantId);
            });

            console.log('🔄 markAllUnpaid: Processing', allTenantIds.size, 'tenants');

            allTenantIds.forEach(tenantId => {
                // 1. UPDATE SOT FIRST (Single Source of Truth)
                updatePaymentSOT(tenantId, false, null);

                // 2. Sync BOTH views using the master sync function
                syncBothViews(tenantId, false);

                // 3. Save to database
                fetch('/api/payment', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ tenant_id: tenantId, paid: false, year: currentYear, month: currentMonth })
                });
            });

            // Update property totals in table view
            updatePropertyTotals();
            updateCounts();
            updateLastSaved();
            console.log('✅ markAllUnpaid: Complete');
        }

        function markAllPaid() {
            // Get all tenant IDs from both card and table views
            const allTenantIds = new Set();

            // Collect from card view
            document.querySelectorAll('.tenant-item').forEach(item => {
                if (item.dataset.tenantId) allTenantIds.add(item.dataset.tenantId);
            });

            // Collect from table view
            document.querySelectorAll('tr[data-tenant-id]').forEach(row => {
                if (row.dataset.tenantId) allTenantIds.add(row.dataset.tenantId);
            });

            console.log('🔄 markAllPaid: Processing', allTenantIds.size, 'tenants');

            allTenantIds.forEach(tenantId => {
                // 1. UPDATE SOT FIRST (Single Source of Truth)
                updatePaymentSOT(tenantId, true, null);

                // 2. Sync BOTH views using the master sync function
                syncBothViews(tenantId, true);

                // 3. Save to database
                fetch('/api/payment', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ tenant_id: tenantId, paid: true, year: currentYear, month: currentMonth })
                });
            });

            // Update property totals in table view
            updatePropertyTotals();
            updateCounts();
            updateLastSaved();
            console.log('✅ markAllPaid: Complete');
        }

        function generateLinks() {
            const checkboxes = document.querySelectorAll('.tenant-checkbox:checked');
            const linksContainer = document.getElementById('whatsappLinks');
            const previewContainer = document.getElementById('messagePreview');

            if (checkboxes.length === 0) {
                alert('¡Todos han pagado! No hay inquilinos pendientes.');
                return;
            }

            // Clear previous links
            linksContainer.innerHTML = '';

            // Generate links for each selected tenant
            checkboxes.forEach((cb, index) => {
                const name = cb.dataset.name;
                const phone = testMode ? testPhone : cb.dataset.phone;

                // Fetch the message from server
                fetch(`/api/message?tenant_id=${cb.dataset.id}&day=${dayOfMonth}`)
                    .then(response => response.json())
                    .then(data => {
                        const link = document.createElement('a');
                        link.href = data.whatsapp_url;
                        link.target = '_blank';
                        link.className = 'whatsapp-link';
                        link.innerHTML = `
                            <span class="link-name">${index + 1}. ${name}</span>
                            <span class="link-icon">Enviar</span>
                        `;
                        linksContainer.appendChild(link);

                        // Show preview of first message
                        if (index === 0) {
                            previewContainer.textContent = data.message;
                            previewContainer.style.display = 'block';
                        }
                    });
            });

            linksContainer.style.display = 'flex';
        }

        // =============================================
        // WhatsApp Cloud API - Send All Function
        // =============================================

        async function sendAllViaApi() {
            const btn = document.getElementById('sendAllApiBtn');
            const statusDiv = document.getElementById('apiStatus');
            const pendingCount = parseInt(document.getElementById('selectedCount').textContent);

            if (pendingCount === 0) {
                alert('¡Todos han pagado! No hay inquilinos pendientes.');
                return;
            }

            // Confirm before sending
            if (!confirm(`¿Enviar recordatorio de renta a ${pendingCount} inquilino(s) pendientes vía WhatsApp? Esto enviará mensajes automáticamente.`)) {
                return;
            }

            // Show loading state
            btn.disabled = true;
            btn.innerHTML = 'Enviando...';
            statusDiv.style.display = 'block';
            statusDiv.style.background = '#fef3c7';
            statusDiv.style.color = '#92400e';
            statusDiv.innerHTML = 'Enviando mensajes a inquilinos pendientes...';

            try {
                const response = await fetch('/api/whatsapp/send-all', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });

                const data = await response.json();

                if (data.success) {
                    // Show success
                    statusDiv.style.background = '#dcfce7';
                    statusDiv.style.color = '#166534';
                    statusDiv.innerHTML = `
                        <strong>¡Enviado!</strong><br>
                        ${data.summary.sent} mensajes enviados<br>
                        ${data.summary.skipped_paid > 0 ? `${data.summary.skipped_paid} ya pagaron (no se les envió)<br>` : ''}
                        ${data.summary.skipped_no_phone > 0 ? `${data.summary.skipped_no_phone} sin teléfono<br>` : ''}
                        ${data.summary.failed > 0 ? `${data.summary.failed} fallaron<br>` : ''}
                    `;

                    // Show toast
                    showUndoToast(`${data.summary.sent} mensajes enviados`, null);
                } else {
                    // Show error
                    statusDiv.style.background = '#fee2e2';
                    statusDiv.style.color = '#dc2626';
                    statusDiv.innerHTML = `
                        <strong>Error</strong><br>
                        ${data.error || 'Error desconocido'}<br>
                        <small>Revisa la configuración en docs/SETUP_WHATSAPP_API.md</small>
                    `;
                }
            } catch (err) {
                statusDiv.style.background = '#fee2e2';
                statusDiv.style.color = '#dc2626';
                statusDiv.innerHTML = `
                    <strong>Error de conexión</strong><br>
                    ${err.message}<br>
                    <small>Verifica tu conexión a internet</small>
                `;
            } finally {
                btn.disabled = false;
                btn.innerHTML = '📤 Enviar TODOS via WhatsApp API';
            }
        }

        // Check WhatsApp API status on page load
        async function checkWhatsAppStatus() {
            try {
                const response = await fetch('/api/whatsapp/status');
                const data = await response.json();

                const btn = document.getElementById('sendAllApiBtn');
                if (!data.configured) {
                    btn.style.background = '#9ca3af';
                    btn.innerHTML = 'Configurar WhatsApp API';
                    btn.onclick = () => {
                        alert('WhatsApp API no está configurado.\\n\\nPasos:\\n1. Ve a docs/SETUP_WHATSAPP_API.md\\n2. Sigue los pasos para obtener credenciales\\n3. Agrega las credenciales al archivo .env');
                    };
                }
            } catch (err) {
                console.log('WhatsApp API check failed:', err);
            }
        }

        // Run on page load
        window.addEventListener('DOMContentLoaded', () => {
            checkWhatsAppStatus();
        });

        // =============================================
        // Confirmation dialogs for bulk actions
        // =============================================

        function confirmMarkAllUnpaid() {
            if (confirm('¿Marcar TODOS los inquilinos como pendientes de pago? Esta acción se puede deshacer.')) {
                markAllUnpaid();
                showUndoToast('Todos marcados como pendientes', 'markAllPaid');
            }
        }

        function confirmMarkAllPaid() {
            if (confirm('¿Marcar TODOS los inquilinos como pagados? Esta acción se puede deshacer.')) {
                markAllPaid();
                showUndoToast('Todos marcados como pagados', 'markAllUnpaid');
            }
        }

        // =============================================
        // Undo Toast Functionality
        // =============================================

        let lastAction = null;
        let undoTimeout = null;

        function showUndoToast(message, undoActionName) {
            const toast = document.getElementById('undoToast');
            const messageEl = document.getElementById('undoMessage');
            const undoBtn = document.getElementById('undoBtn');

            messageEl.textContent = message;
            lastAction = undoActionName;

            toast.classList.add('show');

            // Clear previous timeout
            if (undoTimeout) {
                clearTimeout(undoTimeout);
            }

            // Hide after 5 seconds
            undoTimeout = setTimeout(() => {
                toast.classList.remove('show');
                lastAction = null;
            }, 5000);
        }

        function undoLastAction() {
            const toast = document.getElementById('undoToast');

            if (lastAction === 'markAllPaid') {
                markAllPaid();
            } else if (lastAction === 'markAllUnpaid') {
                markAllUnpaid();
            }

            toast.classList.remove('show');
            if (undoTimeout) {
                clearTimeout(undoTimeout);
            }
            lastAction = null;
        }

        // =============================================
        // Offline Detection
        // =============================================

        function updateOnlineStatus() {
            const banner = document.getElementById('offlineBanner');
            if (navigator.onLine) {
                banner.style.display = 'none';
            } else {
                banner.style.display = 'block';
            }
        }

        // Initialize counts on page load
        // NOTE: Checkbox state and payment status are now managed by SOT (Single Source of Truth)
        // The SOT is applied in the main DOMContentLoaded handler (line ~3584)
        // This handler only sets up offline detection - it does NOT modify checkbox state
        document.addEventListener('DOMContentLoaded', function() {
            // Setup offline detection ONLY - do NOT modify checkbox/paid state here
            // SOT handles all state management to prevent race conditions
            updateOnlineStatus();
            window.addEventListener('online', function() {
                updateOnlineStatus();
                syncPendingPayments();  // Sync when back online
            });
            window.addEventListener('offline', updateOnlineStatus);

            // BUGFIX #5: Sync pending payments on page load if online
            // This ensures any payments saved during offline are synced when page reloads
            if (navigator.onLine) {
                syncPendingPayments();
            }

            // BUGFIX #6: Cleanup stale SOT entries older than 90 days
            cleanupStaleSOT();
        });

        // =============================================
        // Sync pending payments when back online
        // =============================================

        function syncPendingPayments() {
            const queue = JSON.parse(localStorage.getItem('pendingPayments') || '[]');
            if (queue.length === 0) return;

            console.log(`🔄 Syncing ${queue.length} pending payments...`);

            queue.forEach((item, index) => {
                fetch('/api/payment', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        tenant_id: item.tenantId,
                        paid: item.paid,
                        year: item.year || currentYear,
                        month: item.month || currentMonth
                    })
                }).then(response => {
                    if (response.ok) {
                        console.log(`Synced payment for ${item.tenantId}`);
                    }
                });
            });

            // Clear the queue after syncing
            localStorage.removeItem('pendingPayments');
            showUndoToast(`${queue.length} cambios sincronizados`, null);
            updateLastSaved();
        }

// =============================================
        // Last Saved Timestamp - Updates sync indicator
        // =============================================

        function updateLastSaved() {
            const syncIndicator = document.getElementById('sync-indicator');
            const syncText = document.getElementById('sync-text');
            const now = new Date();

            // Save timestamp to localStorage for persistence across page reloads
            localStorage.setItem('lastSavedTime', now.getTime().toString());

            // Update the sync indicator
            if (syncIndicator && syncText) {
                syncIndicator.classList.remove('error');
                syncIndicator.classList.add('synced');
                syncText.textContent = 'Guardado hace unos segundos';

                // Show brief "syncing" animation
                const syncIcon = syncIndicator.querySelector('.sync-icon');
                if (syncIcon) {
                    syncIcon.textContent = '↻';
                    syncIcon.classList.add('spinning');
                    setTimeout(() => {
                        syncIcon.textContent = '✓';
                        syncIcon.classList.remove('spinning');
                    }, 500);
                }
            }
        }

        // Update sync indicator on errors
        function showSyncError() {
            const syncIndicator = document.getElementById('sync-indicator');
            const syncText = document.getElementById('sync-text');
            if (syncIndicator && syncText) {
                syncIndicator.classList.remove('synced');
                syncIndicator.classList.add('error');
                syncText.textContent = 'Error al guardar - reintentando...';
            }
        }

        // =============================================
        // Phone Number Editing
        // =============================================

        let currentEditingTenantId = null;

        function editPhone(tenantId, currentPhone) {
            console.log('📞 editPhone called:', { tenantId, currentPhone });

            try {
                currentEditingTenantId = tenantId;
                const modal = document.getElementById('phoneModal');
                const input = document.getElementById('phoneInput');
                const preview = document.getElementById('phonePreview');
                const saveBtn = document.getElementById('savePhoneBtn');

                if (!modal) {
                    console.error('❌ Phone modal not found!');
                    return;
                }

                input.value = currentPhone || '+52';
                preview.className = 'phone-preview'; // Reset preview state
                preview.style.display = 'none';
                saveBtn.disabled = false;
                saveBtn.textContent = 'Guardar';

                modal.classList.add('show');
                input.focus();
                input.select();

                // Validate initial value
                if (currentPhone) {
                    validatePhonePreview(currentPhone);
                }
                console.log('✅ Phone modal shown');
            } catch (error) {
                console.error('🚨 Error in editPhone:', error);
            }
        }

        // UX #5: Phone validation with preview
        function validatePhonePreview(value) {
            const preview = document.getElementById('phonePreview');
            const previewNumber = document.getElementById('phonePreviewNumber');
            const saveBtn = document.getElementById('savePhoneBtn');

            // Remove all non-digits
            const digits = value.replace(/[^\d]/g, '');

            // Format the number for display
            let formattedNumber = '';
            let isValid = false;

            if (digits.length === 0) {
                preview.style.display = 'none';
                saveBtn.disabled = true;
                return;
            }

            // Check if it's a valid Mexican phone number
            if (digits.startsWith('52')) {
                // Already has country code
                if (digits.length === 12) {
                    // Full Mexican number: 52 + 10 digits
                    formattedNumber = `+${digits.slice(0,2)} ${digits.slice(2,4)} ${digits.slice(4,8)} ${digits.slice(8,12)}`;
                    isValid = true;
                } else if (digits.length === 13 && digits.startsWith('521')) {
                    // Old Mexican mobile format: 52 + 1 + 10 digits
                    formattedNumber = `+52 ${digits.slice(3,5)} ${digits.slice(5,9)} ${digits.slice(9,13)}`;
                    isValid = true;
                } else {
                    formattedNumber = `+${digits} (incompleto - necesita 12 dígitos)`;
                    isValid = false;
                }
            } else if (digits.length === 10) {
                // Just 10 digit Mexican local number - add country code
                formattedNumber = `+52 ${digits.slice(0,2)} ${digits.slice(2,6)} ${digits.slice(6,10)}`;
                isValid = true;
            } else if (digits.length > 10 && digits.length < 12) {
                formattedNumber = `${digits} (verificar formato)`;
                isValid = false;
            } else if (digits.length > 12) {
                formattedNumber = `${digits.slice(0,12)}... (muy largo)`;
                isValid = false;
            } else {
                formattedNumber = `${digits} (necesita 10+ dígitos)`;
                isValid = false;
            }

            // Update preview display
            preview.style.display = 'block';
            previewNumber.textContent = formattedNumber;

            if (isValid) {
                preview.className = 'phone-preview valid';
                preview.querySelector('.preview-label').textContent = 'Se guardará como:';
                saveBtn.disabled = false;
            } else {
                preview.className = 'phone-preview invalid';
                preview.querySelector('.preview-label').textContent = 'Formato incorrecto:';
                saveBtn.disabled = true;
            }
        }

        function closePhoneModal() {
            const modal = document.getElementById('phoneModal');
            modal.classList.remove('show');
            currentEditingTenantId = null;
        }

        // #9: Phone save with FEEDBACK MESSAGE
        function savePhone() {
            const input = document.getElementById('phoneInput');
            const phone = input.value.trim();

            if (!phone || !currentEditingTenantId) {
                closePhoneModal();
                return;
            }

            // Show saving state
            const saveBtn = document.querySelector('#phoneModal .btn-primary');
            if (saveBtn) {
                saveBtn.textContent = 'Guardando...';
                saveBtn.disabled = true;
            }

            fetch('/api/phone', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    tenant_id: currentEditingTenantId,
                    phone: phone
                })
            }).then(response => {
                if (response.ok) {
                    // #9: Show success feedback message BEFORE reload
                    showPersistentConfirmation('¡Teléfono guardado! Ahora puedes enviar WhatsApp.', 'paid');
                    updateLastSaved();
                    // Reload page to show updated phone after short delay
                    setTimeout(() => location.reload(), 1500);
                }
            }).catch(err => {
                showPersistentConfirmation('Error guardando teléfono. Revise su conexión.', 'unpaid');
            });

            closePhoneModal();
        }

        // =============================================
        // Inline WhatsApp Function - NOW WITH PREVIEW
        // =============================================

        // Store pending WhatsApp data for preview
        let pendingWhatsAppData = null;

        function sendWhatsApp(event, btn) {
            console.log('📱 sendWhatsApp called:', { btn, tenantId: btn?.dataset?.tenantId });

            try {
                event.preventDefault();
                const tenantId = btn.dataset.tenantId;

                if (!tenantId) {
                    console.error('❌ No tenant ID found on button');
                    return;
                }

                // Show loading state
                const originalText = btn.innerHTML;
                btn.innerHTML = 'Cargando...';

                // Fetch message and show preview (don't open WhatsApp yet)
                console.log('🔄 Fetching WhatsApp message for tenant:', tenantId);
                fetch(`/api/message?tenant_id=${tenantId}&day=${dayOfMonth}`)
                    .then(response => response.json())
                    .then(data => {
                        btn.innerHTML = originalText;
                        console.log('✅ WhatsApp data received:', data);

                        // Store the data for when user confirms
                        pendingWhatsAppData = {
                            url: data.whatsapp_url,
                            tenantName: data.tenant_name,
                            message: data.message
                        };

                        // Get phone from the tenant item
                        const item = btn.closest('.tenant-item');
                        const phoneEl = item?.querySelector('.tenant-phone-inline a');
                        const phone = phoneEl ? phoneEl.textContent.trim() : 'Teléfono no disponible';

                        // Show preview modal
                        showWhatsAppPreview(data.tenant_name, phone, data.message);
                    })
                    .catch(err => {
                        btn.innerHTML = originalText;
                        console.error('❌ Error fetching WhatsApp message:', err);
                        alert('Error al generar mensaje. Revise su conexión.');
                    });
            } catch (error) {
                console.error('🚨 Error in sendWhatsApp:', error);
            }
        }

        // Show the WhatsApp preview modal
        function showWhatsAppPreview(tenantName, phone, message) {
            const modal = document.getElementById('whatsappPreviewModal');
            const recipientEl = document.getElementById('waPreviewRecipient');
            const phoneEl = document.getElementById('waPreviewPhone');
            const messageEl = document.getElementById('waPreviewMessage');

            if (recipientEl) recipientEl.textContent = tenantName;
            if (phoneEl) phoneEl.textContent = phone;
            if (messageEl) messageEl.textContent = message;

            if (modal) {
                modal.style.display = 'flex';
                modal.classList.add('show');
            }
        }

        // Close the WhatsApp preview modal
        function closeWhatsAppPreview() {
            const modal = document.getElementById('whatsappPreviewModal');
            if (modal) {
                modal.style.display = 'none';
                modal.classList.remove('show');
            }
            pendingWhatsAppData = null;
        }

        // Confirm and send WhatsApp message
        function confirmSendWhatsApp() {
            if (pendingWhatsAppData && pendingWhatsAppData.url) {
                console.log('✅ Opening WhatsApp:', pendingWhatsAppData.url);
                window.open(pendingWhatsAppData.url, '_blank');
            }
            closeWhatsAppPreview();
        }

        // Update WhatsApp button state when payment status changes
        function updateWhatsAppButton(item, isPaid) {
            const waBtn = item.querySelector('.whatsapp-inline-btn');
            if (waBtn && !waBtn.classList.contains('disabled')) {
                if (isPaid) {
                    waBtn.classList.add('disabled');
                    waBtn.innerHTML = 'Pagado';
                    waBtn.onclick = null;
                } else {
                    waBtn.classList.remove('disabled');
                    waBtn.innerHTML = 'WhatsApp';
                }
            }
        }
