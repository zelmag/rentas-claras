# Depósitos Feature Plan

## Overview
Add a "Depósitos" (Deposits) view so your mom can see all security deposits received from tenants.

**Key insight**: Deposit amount = first month's rent (always equal to `tenant.rent`)

## What Mom Wants to See
For each deposit:
- 💰 **Cuánto** (How much) - The deposit amount (= 1st month rent)
- 👤 **De quién** (From who) - Tenant name
- 📅 **Cuándo** (When) - Date received (contract start date)
- 🏠 **Qué unidad** (Which unit) - Property + Unit

---

## Design: Clean & Simple Display

### Option A: Summary Cards by Property (Recommended ✅)
Similar to the contratos page layout - grouped by property with summary stats.

```
┌─────────────────────────────────────────┐
│  💰 Depósitos                           │
│  Total: $248,900                        │
├─────────────────────────────────────────┤
│  🔍 Buscar inquilino...                 │
├─────────────────────────────────────────┤
│  ▼ Matehuala          7 depósitos       │
│     $54,200 total                       │
├─────────────────────────────────────────┤
│  │ A │ Fatima         │ $9,600          │
│  │   │ 1 Jul 2024     │                 │
│  ├───┼────────────────┼─────────────────│
│  │ B │ J Carlos y Raul│ $8,400          │
│  │   │ 6 Abr 2024     │                 │
│  └───┴────────────────┴─────────────────┘
│                                         │
│  ▼ Múzquiz            7 depósitos       │
│     $57,700 total                       │
│  ...                                    │
└─────────────────────────────────────────┘
```

### Key UI Features:
1. **Total Summary** - Grand total of all deposits at the top
2. **Property Sections** - Collapsible, color-coded by property
3. **Per-Tenant Row** - Unit badge, name, date, amount
4. **Search** - Filter by tenant name, property, or unit
5. **Export** - Print/Excel (like contratos page)

---

## Implementation Plan (Bite-sized Steps)

### Phase 1: Database & Backend (No changes needed! 🎉)
The data already exists:
- `tenant.rent` = deposit amount
- `tenant.contract_start` = when deposit was received
- `tenant.property_name` + `tenant.unit` = which unit
- `tenant.name` = from whom

### Phase 2: Create Route (1 file)
**File**: `/routes/depositos.py`
```python
# New Blueprint
# - Get all tenants
# - Group by property
# - Calculate totals
# - Return to template
```

### Phase 3: Register Blueprint (1 edit)
**File**: `/app.py`
- Add import for depositos_bp
- Register the blueprint

### Phase 4: Create Template (1 file)
**File**: `/templates/depositos.html`
- Extend base.html
- Use contratos.html as inspiration for layout
- Property sections with collapsible tenant lists
- Summary card at top

### Phase 5: Add Navigation (1 edit)
**File**: `/templates/partials/bottom_nav.html`
- Add "Depósitos" icon/link to bottom nav

---

## Step-by-Step Checklist

- [ ] **Step 1**: Create `/routes/depositos.py`
  - Import dependencies
  - Create depositos_bp Blueprint
  - Add `/depositos` route
  - Group tenants by property
  - Calculate totals per property and grand total

- [ ] **Step 2**: Register blueprint in `/app.py`
  - Add `from routes.depositos import depositos_bp`
  - Add `app.register_blueprint(depositos_bp)`

- [ ] **Step 3**: Create `/templates/depositos.html`
  - Summary card with grand total
  - Search box (reuse partial)
  - Property sections (collapsible)
  - Tenant rows with: unit, name, date, amount
  - Export buttons (print, excel)

- [ ] **Step 4**: Add to navigation in `/templates/partials/bottom_nav.html`
  - Add new nav item for "Depósitos" with 💰 icon

- [ ] **Step 5**: Test the feature
  - Navigate to /depositos
  - Verify totals are correct
  - Test search functionality
  - Test print/export

---

## Data Mapping

| Display Field | Source |
|---------------|--------|
| Monto (Amount) | `tenant.rent` |
| Inquilino (Tenant) | `tenant.name` |
| Fecha (Date) | `tenant.contract_start` |
| Propiedad | `tenant.property_name` |
| Unidad | `tenant.unit` |

---

## Future Enhancements (Optional)
- Track if deposit was returned when tenant leaves
- Add notes for partial deposits or special cases
- Historical view of deposits by year
