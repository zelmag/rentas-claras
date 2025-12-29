# Plan: New Features for RentasClaras

## Feedback Summary

1. **Renta Prorrateada** - Handle partial/prorated rent for mid-month move-ins
2. **Pago por Adelantado** - Handle advance payments (e.g., 3 months at once)
3. **Agregar Nuevo Tenant** - Add new tenants when contracts end
4. **Responsive Design** - Make the site look good on both mobile AND desktop

---

## 1. Renta Prorrateada (Prorated Rent)

### Use Case
- Tenant moves in on January 15th
- Should only pay half rent for January
- Full rent starting February

### Solution Options

**Option A: One-time adjustment per tenant (RECOMMENDED)**
- Add `prorated_amount` field to tenant record for first month
- Shows prorated amount instead of full rent for that specific month
- Simple, covers 90% of cases

**Option B: Per-month rent override**
- Allow setting custom amount for any specific month
- More flexible but more complex UI

### Implementation (Option A)
```
Database:
  tenants table:
    + prorated_first_month INTEGER (0=no, 1=yes)
    + prorated_amount REAL (amount for first month)
    + prorated_month INTEGER (which month number)
    + prorated_year INTEGER (which year)

UI Changes:
  - When adding/editing tenant, checkbox "¿Renta prorrateada el primer mes?"
  - If checked, show input for prorated amount
  - Auto-calculate based on move-in date: (rent/30) * days_remaining

Display Logic:
  - If current month matches prorated_month/year, show prorated_amount
  - Otherwise show normal rent
```

### Effort: Medium (4-6 hours)

---

## 2. Pago por Adelantado (Advance Payments)

### Use Case
- Puerta del Sol pays 3 months upfront (Jan, Feb, Mar)
- Need to mark all 3 months as paid at once
- Should show which months are covered

### Solution Options

**Option A: Bulk payment action (RECOMMENDED)**
- "Pago Adelantado" button in modal
- Select how many months (1-12)
- Marks current + future months as paid
- Records the advance payment date

**Option B: Manual multi-month marking**
- User navigates to each month and marks paid
- Tedious but simple

### Implementation (Option A)
```
UI Changes (Modal):
  + "¿Pago adelantado?" toggle
  + When enabled: "¿Cuántos meses?" selector (2-12)
  + Shows total: "Total: $47,700 (3 meses)"
  + Confirm marks all months

Database:
  monthly_records:
    + advance_payment_id TEXT (groups related advance payments)
    + is_advance_payment INTEGER (1 if part of advance)

  New table: advance_payments
    - id TEXT PRIMARY KEY
    - tenant_id TEXT
    - start_month INTEGER
    - start_year INTEGER
    - num_months INTEGER
    - total_amount REAL
    - payment_date TEXT
    - payment_method TEXT

Display:
  - Paid items show "Adelantado ✓" badge if part of advance
  - Future months show "Cubierto hasta Mar 2025"
```

### Effort: Medium-High (6-8 hours)

---

## 3. Agregar Nuevo Tenant (Add New Tenant)

### Use Case
- Contract for Unit A ends January 31st
- New tenant moves in February 1st
- Need to add new tenant to system

### Current State
- Tenants are seeded from Excel, no UI to add/edit
- Need admin functionality

### Solution: Tenant Management Admin Page

```
New Route: /admin/tenants

Features:
  1. List all tenants (active + inactive)
  2. "Agregar Inquilino" button → form
  3. Edit existing tenant
  4. Deactivate tenant (soft delete)
  5. Reactivate tenant

Add Tenant Form:
  - Nombre *
  - Teléfono
  - Propiedad * (dropdown of existing + "Nueva propiedad")
  - Unidad *
  - Renta mensual *
  - Fecha inicio contrato *
  - Fecha fin contrato *
  - Contacto emergencia
  - Teléfono emergencia
  - Banco

  Smart Features:
  - If "No renovará" tenant exists in same unit, auto-fill dates
  - Validate no overlap with existing active tenant in same unit
  - Auto-generate ID from property prefix

Database:
  Already supports this via tenants table!
  Just need insert/update routes.

UI Location Options:
  A. New "Admin" tab in bottom nav
  B. Gear icon in header → Admin page
  C. Long-press on property header → Add tenant
```

### Effort: Medium (4-6 hours)

---

## 4. Responsive Design (Mobile + Desktop)

### Current Problem
- Designed mobile-first with `max-width: 500px`
- On desktop, everything is cramped in a narrow column
- Wastes 70% of screen space

### Solution: Responsive Breakpoints

```
Breakpoints:
  - Mobile: < 768px (current design, single column)
  - Tablet: 768px - 1024px (slightly wider, side margins)
  - Desktop: > 1024px (multi-column layout, larger elements)
```

### Desktop Layout Design

```
┌────────────────────────────────────────────────────────────────┐
│  🏠 RentasClaras              [Search...] 🔍     👤 Admin      │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────┐  ┌─────────────────────────────────┐ │
│  │   RESUMEN DEL MES    │  │                                 │ │
│  │   ◀ Enero 2025 ▶     │  │   ⚠️ PENDIENTES (12)            │ │
│  │                      │  │   ┌─────────────────────────┐   │ │
│  │   Progress: 67%      │  │   │ 🏢 Matehuala   $45,200  │   │ │
│  │   ████████░░░░       │  │   ├─────────────────────────┤   │ │
│  │                      │  │   │ Fatima    A    $9,600   │   │ │
│  │   ✓ $156,000         │  │   │ J Carlos  B    $8,400   │   │ │
│  │   ✗ $78,000          │  │   │ ...                     │   │ │
│  │                      │  │   └─────────────────────────┘   │ │
│  │   ─────────────────  │  │                                 │ │
│  │   ACCIONES RÁPIDAS   │  │   ✓ YA PAGARON (20)             │ │
│  │   [🖨️ Imprimir]      │  │   (collapsed...)                │ │
│  │   [📥 Excel]         │  │                                 │ │
│  │   [📱 WhatsApp]      │  │                                 │ │
│  └──────────────────────┘  └─────────────────────────────────┘ │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│  [💰 Pagos]    [📄 Contratos]    [⚙️ Admin]                    │
└────────────────────────────────────────────────────────────────┘
```

### CSS Implementation Plan

```css
/* Mobile First (default) */
.container {
    max-width: 500px;
    margin: 0 auto;
    padding: 16px;
}

/* Tablet */
@media (min-width: 768px) {
    .container {
        max-width: 700px;
        padding: 24px;
    }

    .tenant-item {
        padding: 20px 24px;
    }

    .toggle-btn {
        width: 80px;
        height: 80px;
    }

    .search-input {
        font-size: 1.2rem;
    }
}

/* Desktop */
@media (min-width: 1024px) {
    body {
        padding-bottom: 0; /* No sticky nav on desktop */
    }

    .container {
        max-width: 1200px;
    }

    .desktop-layout {
        display: grid;
        grid-template-columns: 320px 1fr;
        gap: 24px;
    }

    .sidebar {
        position: sticky;
        top: 20px;
        height: fit-content;
    }

    .main-content {
        /* Tenant lists side by side? */
    }

    /* Show desktop nav instead of bottom nav */
    .bottom-nav {
        display: none;
    }

    .desktop-nav {
        display: flex;
    }
}
```

### Files to Modify

1. **`templates/base.html`**
   - Add viewport meta tag (already there)
   - Add desktop nav structure

2. **`templates/pagos.html`**
   - Restructure HTML to support grid layout
   - Add `.sidebar` and `.main-content` wrappers
   - Media queries for all components

3. **`templates/contratos.html`**
   - Same responsive treatment

4. **Optional: `static/css/responsive.css`**
   - Separate file for all responsive styles
   - Easier to maintain

### Effort: Medium (4-6 hours)

---

## Priority Recommendation

| Feature | Priority | Effort | Impact |
|---------|----------|--------|--------|
| 4. Responsive Design | 🔴 HIGH | Medium | All users benefit |
| 3. Add New Tenant | 🔴 HIGH | Medium | Critical for operations |
| 2. Advance Payment | 🟡 MEDIUM | Medium-High | Puerta del Sol use case |
| 1. Prorated Rent | 🟢 LOW | Medium | Edge case |

### Suggested Order
1. **Responsive Design** - Makes app usable on parent's desktop
2. **Add New Tenant** - Critical for when contracts turn over
3. **Advance Payment** - Nice to have for Puerta del Sol
4. **Prorated Rent** - Can be handled manually for now

---

## Questions for User

1. **Responsive**: Do you want two-column layout on desktop, or just wider single column?
2. **Add Tenant**: Should this be admin-only (with password) or open?
3. **Advance Payment**: Should we show on calendar which months are pre-paid?
4. **Prorated**: Do you want auto-calculate from move-in date, or manual entry?

---

## Ready to Implement?

Tell me which feature to start with and I'll implement it! I recommend starting with **Responsive Design** since it's high impact and affects every page view.
