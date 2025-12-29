# Single Source of Truth (SOT) Architecture - Bug Fix Plan

## Overview

This plan addresses three critical issues:
1. **Table → Card sync not working** (but Card → Table works)
2. **Toggle not updating visually**
3. **State not persisting** when navigating to Contratos and back to Pagos

The root cause is **no centralized state management** - state is scattered across:
- DOM elements (classes, checkbox states)
- Server database
- localStorage (only for offline queue)

---

## 🎯 Goals

1. Create a **Single Source of Truth (SOT)** in localStorage for payment state
2. Sync SOT with server on every change
3. Restore state from SOT on page load (before server response)
4. Fix all sync functions to work bidirectionally

---

## 🔍 Root Cause Analysis

### Issue 1: Table → Card sync not working

**Problem:** The `syncCardView()` function looks for `.payment-toggle` but the HTML structure is:
```html
<label class="payment-toggle" data-tenant-id="{{ tenant.id }}">
    <input type="checkbox" onchange="togglePaymentStatus(this, '{{ tenant.id }}')">
    <span class="slider"></span>
</label>
```

The issue is that `syncCardView()` queries:
```javascript
const toggleLabel = cardItem.querySelector('.payment-toggle');
const toggleInput = toggleLabel ? toggleLabel.querySelector('input[type="checkbox"]') : null;
```

This SHOULD work, but let's verify the selector is finding elements.

**Debug step:** Add console.log to verify selectors are finding elements.

### Issue 2: Toggle not updating visually

The HTML uses:
```html
<input type="checkbox" {% if tenant.paid %}checked{% endif %} onchange="...">
```

When `checked` is true = PAID
When `checked` is false = NOT PAID

But in `syncCardView()`:
```javascript
if (toggleInput) {
    toggleInput.checked = isPaid;  // isPaid=true sets checked=true ✅
}
```

This logic is correct. The issue may be:
1. `toggleInput` is null (selector not finding element)
2. The `cardItem` is not found

### Issue 3: State not persisting across page navigation

When user navigates to Contratos and back to Pagos:
1. Page reloads from server
2. Server sends initial state from database
3. If database wasn't updated (network lag), old state shows

**Solution:** Use localStorage as cache, apply immediately on page load.

---

## 📐 SOT Architecture

### State Structure

```javascript
// localStorage key: 'paymentStateSOT'
{
  version: 1,
  lastUpdated: 1703825600000,  // timestamp
  tenants: {
    "tenant-id-1": { isPaid: true, paymentMethod: "transfer", updatedAt: 1703825600000 },
    "tenant-id-2": { isPaid: false, paymentMethod: null, updatedAt: 1703825500000 },
    // ...
  }
}
```

### SOT Functions

```javascript
// 1. Get SOT from localStorage
function getPaymentSOT() {
    const data = localStorage.getItem('paymentStateSOT');
    return data ? JSON.parse(data) : { version: 1, lastUpdated: 0, tenants: {} };
}

// 2. Update SOT (called on every payment change)
function updatePaymentSOT(tenantId, isPaid, paymentMethod = null) {
    const sot = getPaymentSOT();
    sot.tenants[tenantId] = {
        isPaid,
        paymentMethod,
        updatedAt: Date.now()
    };
    sot.lastUpdated = Date.now();
    localStorage.setItem('paymentStateSOT', JSON.stringify(sot));
    return sot;
}

// 3. Apply SOT to DOM (called on page load)
function applyPaymentSOT() {
    const sot = getPaymentSOT();
    Object.entries(sot.tenants).forEach(([tenantId, state]) => {
        syncCardView(tenantId, state.isPaid);
        syncTableView(tenantId, state.isPaid);
    });
    updateCounts();
}

// 4. Sync SOT from server (reconcile after server response)
function syncSOTFromServer(tenantId, serverIsPaid) {
    updatePaymentSOT(tenantId, serverIsPaid);
}
```

---

## 📋 Implementation Steps

### Phase 1: Add SOT Infrastructure (15 min)

**Step 1.1:** Add SOT functions near top of script section
- `getPaymentSOT()`
- `updatePaymentSOT(tenantId, isPaid, paymentMethod)`
- `applyPaymentSOT()`

**Step 1.2:** Call `applyPaymentSOT()` on DOMContentLoaded
- Apply cached state immediately before server response

### Phase 2: Fix syncCardView() (10 min)

**Step 2.1:** Add debug logging to find selector issue
```javascript
console.log('syncCardView:', tenantId, isPaid);
console.log('cardItem:', cardItem);
console.log('toggleLabel:', toggleLabel);
console.log('toggleInput:', toggleInput);
```

**Step 2.2:** Fix selector if needed - may need different approach

### Phase 3: Update All Payment Functions to Use SOT (20 min)

**Step 3.1:** Update `togglePaymentStatus()` to:
1. Update SOT first
2. Update DOM
3. Send to server
4. On server success: confirm SOT
5. On server fail: keep SOT (will sync later)

**Step 3.2:** Update `togglePaidTable()` to use same pattern

**Step 3.3:** Update `setPaymentStatus()` to use same pattern

**Step 3.4:** Update `markAllPaid()` / `markAllUnpaid()` to use SOT

### Phase 4: Apply SOT on Page Load (10 min)

**Step 4.1:** Modify DOMContentLoaded to call `applyPaymentSOT()` after initial render

**Step 4.2:** Add slight delay to ensure DOM is ready:
```javascript
window.addEventListener('DOMContentLoaded', () => {
    // Wait for Jinja to render, then apply SOT
    setTimeout(() => {
        applyPaymentSOT();
    }, 100);
});
```

### Phase 5: Sync SOT with Server (10 min)

**Step 5.1:** On successful server response, update SOT with confirmed state

**Step 5.2:** On page load, fetch current state from server and reconcile with SOT

---

## 🔧 Code Changes

### Location: `/Users/zelma/Desktop/ZelmaHelps_Agent/rentas-claras/app.py`

### Change 1: Add SOT Functions (after line ~3801)

```javascript
// =============================================
// SINGLE SOURCE OF TRUTH (SOT) for Payment State
// =============================================

function getPaymentSOT() {
    try {
        const data = localStorage.getItem('paymentStateSOT');
        return data ? JSON.parse(data) : { version: 1, lastUpdated: 0, tenants: {} };
    } catch (e) {
        console.error('Error reading SOT:', e);
        return { version: 1, lastUpdated: 0, tenants: {} };
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
    localStorage.setItem('paymentStateSOT', JSON.stringify(sot));
    console.log('SOT updated:', tenantId, isPaid);
    return sot;
}

function applyPaymentSOT() {
    console.log('Applying SOT to DOM...');
    const sot = getPaymentSOT();
    let appliedCount = 0;

    Object.entries(sot.tenants).forEach(([tenantId, state]) => {
        // Apply to both views
        syncBothViews(tenantId, state.isPaid);
        appliedCount++;
    });

    console.log(`SOT applied to ${appliedCount} tenants`);
    updateCounts();
    flushPropertyFilterCounts();
}

// Master sync function - updates BOTH card and table views
function syncBothViews(tenantId, isPaid) {
    syncCardView(tenantId, isPaid);
    syncTableView(tenantId, isPaid);
}
```

### Change 2: Fix syncCardView() with better selectors

```javascript
function syncCardView(tenantId, isPaid) {
    const cardItem = document.querySelector(`.tenant-item[data-tenant-id="${tenantId}"]`);
    if (!cardItem) {
        console.log('syncCardView: cardItem not found for', tenantId);
        return;
    }

    // Find the toggle container, then the input inside
    const toggleContainer = cardItem.querySelector('.payment-toggle-container');
    const toggleInput = toggleContainer ? toggleContainer.querySelector('input[type="checkbox"]') : null;
    const toggleLabelText = cardItem.querySelector('.payment-toggle-label');
    const checkbox = cardItem.querySelector('.tenant-checkbox');
    const paymentSelect = cardItem.querySelector('.payment-method');

    console.log('syncCardView:', tenantId, isPaid, 'toggleInput:', !!toggleInput);

    // Update toggle switch
    if (toggleInput) {
        toggleInput.checked = isPaid;
    }

    // Update toggle label text
    if (toggleLabelText) {
        toggleLabelText.textContent = isPaid ? 'Ya pagó' : 'No ha pagado';
        toggleLabelText.classList.toggle('paid', isPaid);
        toggleLabelText.classList.toggle('unpaid', !isPaid);
    }

    // Update item state and checkbox
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
```

### Change 3: Update togglePaymentStatus() to use SOT

```javascript
function togglePaymentStatus(toggle, tenantId) {
    // ... existing re-entry guard ...

    const isPaid = toggle.checked;

    // 1. UPDATE SOT FIRST (Single Source of Truth)
    updatePaymentSOT(tenantId, isPaid, paymentSelect?.value || null);

    // 2. Update local DOM (already done by toggle.checked changing)
    // ... existing DOM updates ...

    // 3. Sync table view with card view state
    syncTableView(tenantId, isPaid);

    // 4. Send to server
    fetch('/api/payment', { ... })
    .then(response => {
        if (response.ok) {
            // Server confirmed - SOT is already correct
            console.log('Server confirmed:', tenantId, isPaid);
        }
    })
    .catch(err => {
        // SOT still has the intended state for later sync
        console.error('Server failed, SOT will sync later:', err);
    });

    updateCounts();
}
```

### Change 4: Update togglePaidTable() to use SOT

```javascript
function togglePaidTable(btn, tenantId) {
    // ... existing logic ...

    // 1. UPDATE SOT FIRST
    updatePaymentSOT(tenantId, newPaidStatus);

    // 2. Update table DOM
    // ... existing DOM updates ...

    // 3. Sync card view
    syncCardView(tenantId, newPaidStatus);

    // 4. Send to server
    // ... existing fetch ...
}
```

### Change 5: Apply SOT on page load

```javascript
window.addEventListener('DOMContentLoaded', () => {
    // ... existing view preference logic ...

    // Apply SOT to restore state from localStorage
    // Use setTimeout to ensure Jinja templates have rendered
    setTimeout(() => {
        applyPaymentSOT();
    }, 50);
});
```

---

## 📊 Implementation Order

| Priority | Step | Time Est. | Risk |
|----------|------|-----------|------|
| 1 | Add SOT functions | 10 min | 🟢 Low |
| 2 | Fix syncCardView() selectors | 10 min | 🟢 Low |
| 3 | Update togglePaymentStatus() | 5 min | 🟢 Low |
| 4 | Update togglePaidTable() | 5 min | 🟢 Low |
| 5 | Apply SOT on page load | 5 min | 🟢 Low |
| 6 | Test all flows | 10 min | - |

**Total estimated time:** ~45 minutes

---

## 🧪 Test Plan

### Test 1: Card → Table Sync
1. Switch to Card view
2. Toggle a tenant to "Pagado"
3. Switch to Table view
4. ✅ Verify tenant shows as paid with ✓

### Test 2: Table → Card Sync
1. Switch to Table view
2. Click status button on a tenant
3. Switch to Card view
4. ✅ Verify toggle shows "Ya pagó"

### Test 3: Navigation Persistence
1. Mark tenant as "Pagado" in Pagos
2. Click Contratos tab
3. Click Pagos tab
4. ✅ Verify tenant still shows as "Pagado"

### Test 4: Page Refresh Persistence
1. Mark tenant as "Pagado"
2. Refresh page (Cmd+R)
3. ✅ Verify tenant shows as "Pagado" immediately (before server response)

### Test 5: Rapid Toggle
1. Toggle tenant 5 times quickly
2. ✅ Verify final state is consistent across both views
3. ✅ Verify SOT has correct final state

---

## ✅ Completion Checklist

- [ ] SOT functions added
- [ ] syncCardView() fixed
- [ ] syncTableView() verified
- [ ] togglePaymentStatus() uses SOT
- [ ] togglePaidTable() uses SOT
- [ ] setPaymentStatus() uses SOT
- [ ] applyPaymentSOT() called on DOMContentLoaded
- [ ] All tests pass
- [ ] Console logs removed (production)
