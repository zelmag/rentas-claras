# 🔍 Combined Search Feature Plan

## Goal
Allow users to search with combined terms like "ensenada 3" to find:
- Property: **Ensenada**
- Unit: **3**

## Current State Analysis

### ✅ What Already Works
The search already searches across **name**, **property**, AND **unit** fields:
```javascript
const matches = name.includes(term) || property.includes(term) || unit.includes(term);
```

### ❌ The Problem
When a user types "ensenada 3", the current logic checks:
- Does "ensenada 3" exist in name? → **No**
- Does "ensenada 3" exist in property? → **No** (property is just "Ensenada")
- Does "ensenada 3" exist in unit? → **No** (unit is just "3")

All three fail because the search term is split across different fields.

---

## 📋 Step-by-Step Implementation Plan

### Step 1: Create a Combined Search String
**What**: Create a combined searchable string that includes all fields together.
**Why**: So "ensenada 3" can match "ensenada | 3" in one check.
**Risk**: Low - this is additive, doesn't break existing behavior.

```javascript
// Current approach
const name = item.dataset.name.toLowerCase();
const property = item.dataset.property.toLowerCase();
const unit = item.dataset.unit.toLowerCase();
const matches = name.includes(term) || property.includes(term) || unit.includes(term);

// New approach - ADD a combined string check
const combined = `${name} ${property} ${unit}`;
const matches = combined.includes(term) ||
                name.includes(term) ||
                property.includes(term) ||
                unit.includes(term);
```

### Step 2: Handle Multi-Word Search (Tokenized)
**What**: Split the search term into words and check if ALL words exist.
**Why**: "ensenada 3" should find items where "ensenada" is in property AND "3" is in unit.
**Risk**: Medium - need to ensure order doesn't matter.

```javascript
function filterBySearchTerm(searchableCombined, term) {
    term = term.toLowerCase().trim();

    // If term contains spaces, check if ALL words match somewhere
    const words = term.split(/\s+/).filter(w => w.length > 0);

    if (words.length > 1) {
        // All words must be present somewhere in the combined string
        return words.every(word => searchableCombined.includes(word));
    }

    // Single word - simple includes check
    return searchableCombined.includes(term);
}
```

### Step 3: Update All Filter Functions
**Files to update**:
1. `/templates/inquilinos.html` → `filterTenants()`
2. `/templates/pagos.html` → `filterTenants()`
3. `/templates/contratos.html` → `filterContracts()`
4. `/templates/depositos.html` → `filterContracts()`
5. `/templates/recordatorios.html` → `filterTenants()`

### Step 4: Update Placeholder Text
**What**: Update the search placeholder to reflect the new capability.
**File**: `/templates/partials/search_box.html`
**Change**:
```html
<!-- From -->
<input placeholder="Buscar nombre o propiedad...">

<!-- To -->
<input placeholder="Buscar nombre, propiedad o unidad...">
```

### Step 5: Test All Search Scenarios
**Test cases**:
| Search Term | Should Find |
|-------------|-------------|
| `ensenada` | All tenants in Ensenada property |
| `3` | All tenants in unit 3 (any property) |
| `ensenada 3` | Tenant in Ensenada unit 3 |
| `maria` | All tenants named Maria |
| `maria ensenada` | Maria who lives in Ensenada |
| `maria 5` | Maria in unit 5 |
| `3 ensenada` | Same as "ensenada 3" (order doesn't matter) |

---

## 🛡️ Safety Measures

### 1. Backward Compatibility
- Keep existing individual field checks as fallback
- New behavior is additive, not replacing

### 2. Performance
- No additional DOM queries
- Simple string operations only
- Same O(n) complexity as before

### 3. Edge Cases Handled
- Empty search → show all
- Single word → works as before
- Multiple spaces → normalized
- Leading/trailing spaces → trimmed

### 4. Testing Approach
- Test locally first
- Test on each page that uses search
- Verify no regressions for existing search behavior

---

## 📁 Files to Modify (in order)

| # | File | Change |
|---|------|--------|
| 1 | `partials/search_box.html` | Update placeholder text |
| 2 | `inquilinos.html` | Update `filterTenants()` |
| 3 | `pagos.html` | Update `filterTenants()` |
| 4 | `contratos.html` | Update `filterContracts()` |
| 5 | `depositos.html` | Update `filterContracts()` |
| 6 | `recordatorios.html` | Update `filterTenants()` |

---

## ✅ Final Implementation Code

This is the pattern to apply to each filter function:

```javascript
function filterTenants(term) {
    term = term.toLowerCase().trim();

    // Split search into words for multi-word matching
    const searchWords = term.split(/\s+/).filter(w => w.length > 0);

    document.querySelectorAll('.tenant-card').forEach(card => {
        const name = (card.dataset.name || '').toLowerCase();
        const property = (card.dataset.property || '').toLowerCase();
        const unit = (card.dataset.unit || '').toLowerCase();

        // Create combined searchable string
        const combined = `${name} ${property} ${unit}`;

        // Check if ALL search words are present in the combined string
        const matches = searchWords.length === 0 ||
                        searchWords.every(word => combined.includes(word));

        card.style.display = matches ? 'block' : 'none';
    });

    // ... rest of function (show/hide sections) remains the same
}
```

---

## 🎯 Expected User Experience

**Before**:
- User types "ensenada 3" → No results 😞

**After**:
- User types "ensenada 3" → Shows tenant in Ensenada unit 3 ✅
- User types "3 ensenada" → Same result (order doesn't matter) ✅
- User types "mar ens" → Shows Maria in Ensenada (partial matching) ✅

---

## 📝 Notes

- The `recordatorios.html` filter is slightly different (uses DOM text content instead of data attributes) - will need adaptation
- All changes are in JavaScript only - no backend changes needed
- Changes are isolated to the filter functions - no risk to data integrity
