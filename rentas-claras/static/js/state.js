/**
 * RentasClaras - Central State Management (Single Source of Truth)
 * =================================================================
 * 
 * This module provides centralized state management across all pages.
 * The database is the ultimate SOT, but we cache in localStorage for
 * optimistic updates and offline support.
 * 
 * State Flow:
 * 1. User action → Update local state → Update UI immediately
 * 2. Sync to server → Update localStorage cache
 * 3. Other pages poll/subscribe → Receive updates
 */

const RentasState = (function() {
    'use strict';

    // State version for cache invalidation
    const STATE_VERSION = '1.0';
    const CACHE_KEY = 'rentasState';
    const LAST_UPDATE_KEY = 'rentasLastUpdate';
    
    // Event listeners for state changes
    const listeners = new Set();
    
    // Polling interval (ms) for checking updates
    const POLL_INTERVAL = 30000; // 30 seconds
    
    // Current state cache
    let currentState = null;
    let pollTimer = null;

    /**
     * Initialize the state manager
     */
    function init() {
        // Load cached state
        currentState = loadFromCache();
        
        // Start polling for updates
        startPolling();
        
        // Listen for storage events from other tabs
        window.addEventListener('storage', handleStorageChange);
        
        // Sync on page visibility change
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'visible') {
                refresh();
            }
        });

        console.log('📊 RentasState initialized');
    }

    /**
     * Load state from localStorage cache
     */
    function loadFromCache() {
        try {
            const cached = localStorage.getItem(CACHE_KEY);
            if (cached) {
                const parsed = JSON.parse(cached);
                if (parsed.version === STATE_VERSION) {
                    return parsed.data;
                }
            }
        } catch (e) {
            console.warn('Failed to load state cache:', e);
        }
        return null;
    }

    /**
     * Save state to localStorage cache
     */
    function saveToCache(state) {
        try {
            localStorage.setItem(CACHE_KEY, JSON.stringify({
                version: STATE_VERSION,
                data: state,
                timestamp: Date.now()
            }));
            localStorage.setItem(LAST_UPDATE_KEY, Date.now().toString());
        } catch (e) {
            console.warn('Failed to save state cache:', e);
        }
    }

    /**
     * Handle storage changes from other tabs
     */
    function handleStorageChange(event) {
        if (event.key === LAST_UPDATE_KEY) {
            // Another tab updated the state, reload from cache
            currentState = loadFromCache();
            notifyListeners('external_update');
        }
    }

    /**
     * Notify all listeners of state change
     */
    function notifyListeners(eventType, details = {}) {
        listeners.forEach(callback => {
            try {
                callback({
                    type: eventType,
                    state: currentState,
                    ...details
                });
            } catch (e) {
                console.error('State listener error:', e);
            }
        });
    }

    /**
     * Subscribe to state changes
     * @param {Function} callback - Called with {type, state, ...details}
     * @returns {Function} Unsubscribe function
     */
    function subscribe(callback) {
        listeners.add(callback);
        // Immediately call with current state if available
        if (currentState) {
            callback({ type: 'init', state: currentState });
        }
        return () => listeners.delete(callback);
    }

    /**
     * Fetch fresh state from server
     */
    async function refresh() {
        try {
            const response = await fetch('/api/state/summary');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const data = await response.json();
            if (data.success) {
                currentState = data.summary;
                saveToCache(currentState);
                notifyListeners('refresh', { source: 'server' });
                return currentState;
            }
        } catch (e) {
            console.warn('Failed to refresh state:', e);
            // Return cached state on error
            return currentState;
        }
    }

    /**
     * Start polling for updates
     */
    function startPolling() {
        stopPolling();
        pollTimer = setInterval(() => {
            if (document.visibilityState === 'visible') {
                refresh();
            }
        }, POLL_INTERVAL);
    }

    /**
     * Stop polling
     */
    function stopPolling() {
        if (pollTimer) {
            clearInterval(pollTimer);
            pollTimer = null;
        }
    }

    /**
     * Get current state (from cache, non-blocking)
     */
    function getState() {
        return currentState;
    }

    /**
     * Get current month payment summary
     */
    function getPaymentSummary() {
        if (!currentState) return null;
        return {
            totalCollected: currentState.total_collected,
            totalExpected: currentState.total_expected,
            pendingPayments: currentState.pending_payments,
            pendingAmount: currentState.pending_amount,
            collectionPercent: currentState.collection_percent,
            paidCount: currentState.paid_count,
            unpaidCount: currentState.unpaid_count
        };
    }

    /**
     * Update payment status locally and sync to server
     * @param {string} tenantId 
     * @param {boolean} isPaid 
     * @param {Object} options - payment_method, visits, visit_charge, year, month
     */
    async function updatePayment(tenantId, isPaid, options = {}) {
        // BUGFIX: Use currentState's year/month if available, otherwise calculate from current date
        // This ensures we use the same month context the server is using
        const stateYear = currentState?.year;
        const stateMonth = currentState?.month;
        
        const {
            payment_method = '',
            visits = 0,
            visit_charge = 0,
            year = stateYear || new Date().getFullYear(),
            month = stateMonth || (new Date().getMonth() + 1)
        } = options;

        // Optimistic update - update local state immediately
        if (currentState && currentState.payments) {
            const key = `${tenantId}_${year}_${month}`;
            currentState.payments[key] = {
                paid: isPaid,
                payment_method,
                visits,
                visit_charge,
                updated_at: Date.now()
            };
            // Also save to cache immediately for cross-tab sync
            saveToCache(currentState);
        }

        // Notify listeners of optimistic update
        notifyListeners('payment_update', { tenantId, isPaid, optimistic: true });

        // Sync to server
        try {
            const response = await fetch('/api/payment', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    tenant_id: tenantId,
                    paid: isPaid,
                    payment_method,
                    visits,
                    visit_charge,
                    year,
                    month
                })
            });

            if (response.ok) {
                // Refresh full state from server to ensure consistency
                await refresh();
                notifyListeners('payment_update', { tenantId, isPaid, optimistic: false, synced: true });
                return { success: true };
            } else {
                throw new Error(`Server returned ${response.status}`);
            }
        } catch (e) {
            console.error('Failed to sync payment:', e);
            // Keep optimistic update but mark as pending sync
            // BUGFIX: Queue for retry when back online
            queuePendingSync({ tenantId, isPaid, payment_method, visits, visit_charge, year, month });
            notifyListeners('payment_sync_error', { tenantId, error: e.message });
            return { success: false, error: e.message };
        }
    }

    /**
     * Queue a payment for sync when back online
     * BUGFIX: Added to ensure no data is lost during network issues
     */
    function queuePendingSync(paymentData) {
        try {
            const queue = JSON.parse(localStorage.getItem('pendingPayments') || '[]');
            // Deduplicate - only keep latest entry per tenant/month
            const filtered = queue.filter(item => 
                !(item.tenantId === paymentData.tenantId && 
                  item.year === paymentData.year && 
                  item.month === paymentData.month)
            );
            filtered.push({
                ...paymentData,
                timestamp: Date.now()
            });
            localStorage.setItem('pendingPayments', JSON.stringify(filtered));
            console.log('📥 Queued payment for sync:', paymentData.tenantId);
        } catch (e) {
            console.error('Failed to queue payment:', e);
        }
    }

    /**
     * Get payment status for a tenant/month
     */
    function getPaymentStatus(tenantId, year, month) {
        if (!currentState || !currentState.payments) return null;
        const key = `${tenantId}_${year}_${month}`;
        return currentState.payments[key] || null;
    }

    /**
     * Update tenant data locally and sync to server
     */
    async function updateTenant(tenantId, data) {
        // Sync to server
        try {
            const response = await fetch(`/api/tenant/${tenantId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            if (response.ok) {
                // Refresh full state from server
                await refresh();
                notifyListeners('tenant_update', { tenantId });
                return { success: true };
            } else {
                const result = await response.json();
                return { success: false, error: result.error || 'Server error' };
            }
        } catch (e) {
            console.error('Failed to update tenant:', e);
            return { success: false, error: e.message };
        }
    }

    /**
     * Add a new tenant
     */
    async function addTenant(data) {
        try {
            const response = await fetch('/api/tenant', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            const result = await response.json();
            if (result.success) {
                // Refresh full state from server
                await refresh();
                notifyListeners('tenant_add', { tenantId: result.tenant_id });
                return { success: true, tenant_id: result.tenant_id };
            } else {
                return { success: false, error: result.error };
            }
        } catch (e) {
            console.error('Failed to add tenant:', e);
            return { success: false, error: e.message };
        }
    }

    /**
     * Delete a tenant
     */
    async function deleteTenant(tenantId) {
        try {
            const response = await fetch(`/api/tenant/${tenantId}`, {
                method: 'DELETE'
            });

            const result = await response.json();
            if (result.success) {
                // Refresh full state from server
                await refresh();
                notifyListeners('tenant_delete', { tenantId });
                return { success: true };
            } else {
                return { success: false, error: result.error };
            }
        } catch (e) {
            console.error('Failed to delete tenant:', e);
            return { success: false, error: e.message };
        }
    }

    /**
     * Update contract renewal status
     */
    async function updateRenewal(tenantId, data) {
        try {
            const response = await fetch('/api/renewal', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ tenant_id: tenantId, ...data })
            });

            if (response.ok) {
                await refresh();
                notifyListeners('renewal_update', { tenantId });
                return { success: true };
            } else {
                return { success: false, error: 'Server error' };
            }
        } catch (e) {
            console.error('Failed to update renewal:', e);
            return { success: false, error: e.message };
        }
    }

    /**
     * Format currency in Mexican Pesos
     */
    function formatCurrency(amount) {
        return '$' + Number(amount).toLocaleString('es-MX', {
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        });
    }

    /**
     * Get relative time string (e.g., "hace 5 min")
     */
    function getRelativeTime(timestamp) {
        if (!timestamp) return 'nunca';
        
        const now = Date.now();
        const diff = now - (typeof timestamp === 'string' ? new Date(timestamp).getTime() : timestamp);
        
        const seconds = Math.floor(diff / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);
        const days = Math.floor(hours / 24);
        
        if (seconds < 60) return 'ahora';
        if (minutes < 60) return `hace ${minutes} min`;
        if (hours < 24) return `hace ${hours}h`;
        if (days < 7) return `hace ${days} día${days > 1 ? 's' : ''}`;
        
        return new Date(timestamp).toLocaleDateString('es-MX');
    }

    // Auto-initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Public API
    return {
        init,
        refresh,
        subscribe,
        getState,
        getPaymentSummary,
        getPaymentStatus,
        updatePayment,
        updateTenant,
        addTenant,
        deleteTenant,
        updateRenewal,
        formatCurrency,
        getRelativeTime,
        startPolling,
        stopPolling
    };
})();

// Export for module systems if available
if (typeof module !== 'undefined' && module.exports) {
    module.exports = RentasState;
}
