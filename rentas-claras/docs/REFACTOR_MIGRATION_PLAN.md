# RentasClaras Refactoring Migration Plan
## Safely Extracting Templates & Consolidating CSS

**Created:** December 29, 2024  
**Author:** UX Engineering Team  
**Status:** IN PROGRESS ✅  
**Risk Level:** Medium (mitigated by phased approach)

---

## ✅ COMPLETED

| Step | Description | Lines Removed | Status |
|------|-------------|---------------|--------|
| 1.1 | Extract `login.html` | 294 lines | ✅ DONE |

**Current `app.py` size:** ~9,074 lines (was 9,368)

---

## 🎯 NEXT STEPS (In Order)

### STEP 2: Extract `base.html` (Shared Layout)
**Goal:** Create template inheritance so all pages share common elements

### STEP 3: Update `login.html` to extend `base.html`
**Goal:** First test of template inheritance pattern

### STEP 4: Extract `pagos.html` (Main Page)
**Goal:** Biggest win - removes ~2,000+ lines from app.py

### STEP 5: Extract `contratos.html`
**Goal:** Complete template extraction

### STEP 6: CSS Consolidation
**Goal:** Move inline styles to external CSS files

---

## 📋 Table of Contents

1. [Overview](#1-overview)
2. [Pre-Migration Setup](#2-pre-migration-setup)
3. [Phase 1: Template Extraction](#3-phase-1-template-extraction)
4. [Phase 2: CSS Consolidation](#4-phase-2-css-consolidation)
5. [Rollback Strategy](#5-rollback-strategy)
6. [Validation Checklist](#6-validation-checklist)

---

## 1. Overview

### Current State
- **`app.py`**: 9,211 lines containing routes, templates, CSS, and JavaScript
- **Inline styles**: Hundreds of `style=""` attributes throughout templates
- **No separation**: Design system tokens exist but are bypassed

### Target State
```
rentas-claras/
├── app.py                      # ~800 lines (routes only)
├── templates/
│   ├── base.html               # Shared layout, head, nav
│   ├── pagos.html              # Pagos page
│   ├── contratos.html          # Contratos page  
│   ├── login.html              # Login page
│   └── components/
│       ├── tenant_card.html
│       ├── tenant_table_row.html
│       ├── property_section.html
│       ├── month_navigator.html
│       ├── search_bar.html
│       └── status_pill.html
├── static/
│   ├── css/
│   │   ├── design-tokens.css   # CSS variables only
│   │   ├── base.css            # Reset, typography, layout
│   │   ├── components.css      # Reusable component styles
│   │   └── pages/
│   │       ├── pagos.css
│   │       └── contratos.css
│   └── js/
│       ├── search.js
│       ├── payment-toggle.js
│       └── utils.js
```

### Guiding Principles

1. **One change at a time** - Each PR/commit does ONE thing
2. **Always deployable** - Main branch works at every step
3. **Feature flags** - New templates can be toggled on/off
4. **Visual regression testing** - Screenshots before/after each change
5. **No user-facing changes initially** - First phase is pure refactor

---

## 2. Pre-Migration Setup

### Step 2.1: Create the Directory Structure

```bash
# Run from rentas-claras/
mkdir -p templates/components
mkdir -p static/css/pages
mkdir -p static/js
```

### Step 2.2: Add Visual Regression Baseline

Before ANY changes, capture screenshots of every page state:

```bash
# Create a screenshots directory
mkdir -p tests/screenshots/baseline

# Manually capture (or use Playwright/Puppeteer):
# 1. Pagos page - Card view (desktop)
# 2. Pagos page - Card view (mobile 375px)
# 3. Pagos page - Table view (desktop)
# 4. Pagos page - Table view (mobile)
# 5. Contratos page (desktop)
# 6. Contratos page (mobile)
# 7. Login page
# 8. Each tenant card state (paid, unpaid, no phone, with late fee)
```

### Step 2.3: Add a Feature Flag System

Add to `app.py` near the top:

```python
# =============================================================================
# FEATURE FLAGS - For gradual template migration
# =============================================================================
FEATURE_FLAGS = {
    "use_external_templates": os.environ.get("USE_EXTERNAL_TEMPLATES", "false").lower() == "true",
    "use_external_css": os.environ.get("USE_EXTERNAL_CSS", "false").lower() == "true",
}

def get_feature_flag(flag_name: str) -> bool:
    """Check if a feature flag is enabled."""
    return FEATURE_FLAGS.get(flag_name, False)
```

### Step 2.4: Set Up Template Comparison Testing

Create `tests/test_template_parity.py`:

```python
"""
Tests to ensure external templates match inline templates exactly.
Run after each migration step to verify no visual changes.
"""
import pytest
from app import app

class TestTemplateParity:
    """Compare inline vs external template output."""
    
    @pytest.fixture
    def client(self):
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    
    def test_pagos_html_structure(self, client):
        """Pagos page should have same HTML structure."""
        # This will be filled in as we migrate
        pass
    
    def test_contratos_html_structure(self, client):
        """Contratos page should have same HTML structure."""
        pass
```

---

## 3. Phase 1: Template Extraction

### Overview

We'll extract templates in order of **independence** (least dependencies first):

1. **Login page** (standalone, simple)
2. **Base layout** (shared by all pages)
3. **Components** (reusable pieces)
4. **Pagos page** (most complex, last)
5. **Contratos page**

Each step follows this pattern:
1. Copy the inline HTML to external file
2. Add `{% include %}` or `{% extends %}` syntax
3. Create a feature-flagged route that uses external template
4. Test both versions work identically
5. Switch to external template
6. Remove inline template after validation period

---

### Step 1.1: Extract Login Template (Day 1)

**Why first:** Login is standalone, no dependencies, low risk.

**Current location in app.py:** Search for `LOGIN_TEMPLATE` (around line 6200)

**Actions:**

1. Create `templates/login.html`:

```html
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RentasClaras - Iniciar Sesión</title>
    <link rel="icon" type="image/svg+xml" href="/static/favicon.svg">
    <style>
        {# Copy all styles from LOGIN_TEMPLATE here #}
    </style>
</head>
<body>
    {# Copy body content from LOGIN_TEMPLATE here #}
</body>
</html>
```

2. Modify the login route:

```python
@app.route("/login", methods=["GET", "POST"])
def login():
    # ... existing logic ...
    
    if get_feature_flag("use_external_templates"):
        return render_template("login.html", error=error)
    else:
        return render_template_string(LOGIN_TEMPLATE, error=error)
```

3. Test both versions:
```bash
# Test inline version
curl http://localhost:5001/login > /tmp/login_inline.html

# Enable external templates
export USE_EXTERNAL_TEMPLATES=true

# Test external version
curl http://localhost:5001/login > /tmp/login_external.html

# Compare
diff /tmp/login_inline.html /tmp/login_external.html
```

4. **Validation:**
   - [ ] HTML output is identical
   - [ ] Login works with correct PIN
   - [ ] Login fails with incorrect PIN
   - [ ] Error message displays correctly

5. Once validated, make external template the default (flip flag).

---

### Step 1.2: Extract Base Template (Day 2)

**Why second:** All pages share common elements (head, nav, footer).

**Actions:**

1. Create `templates/base.html`:

```html
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}RentasClaras{% endblock %}</title>
    <link rel="icon" type="image/svg+xml" href="/static/favicon.svg">
    <link rel="apple-touch-icon" href="/static/icon-192.png">
    <link rel="manifest" href="/static/manifest.json">
    <meta name="theme-color" content="#0A7A0A">
    
    {# External CSS will be added in Phase 2 #}
    <style>
        {% block inline_styles %}{% endblock %}
    </style>
    
    {% block head_extra %}{% endblock %}
</head>
<body>
    {% block body %}{% endblock %}
    
    {# Bottom navigation - shared across pages #}
    {% block bottom_nav %}
    <nav class="bottom-nav">
        <a href="/" class="bottom-nav-item {% if active_tab == 'pagos' %}active{% endif %}">
            <span class="bottom-nav-icon">💰</span>
            <span>Cobrar</span>
        </a>
        <a href="/contratos" class="bottom-nav-item {% if active_tab == 'contratos' %}active{% endif %}">
            <span class="bottom-nav-icon">📋</span>
            <span>Contratos</span>
        </a>
    </nav>
    {% endblock %}
    
    {% block scripts %}{% endblock %}
</body>
</html>
```

2. Update `login.html` to extend base:

```html
{% extends "base.html" %}

{% block title %}RentasClaras - Iniciar Sesión{% endblock %}

{% block bottom_nav %}{% endblock %} {# No nav on login #}

{% block inline_styles %}
    {# Login-specific styles #}
{% endblock %}

{% block body %}
    {# Login form content #}
{% endblock %}
```

**Validation:**
- [ ] Login page still works
- [ ] No visual changes

---

### Step 1.3: Extract Reusable Components (Days 3-5)

Extract in this order:

#### 1.3.1: Search Bar Component

Create `templates/components/search_bar.html`:

```html
{# 
  Search bar component
  Args:
    - id: unique ID for the input
    - placeholder: placeholder text
    - label: optional label above search
#}
<div class="prominent-search-section" id="stickySearch">
    {% if label %}
    <div class="prominent-search-label">{{ label }}</div>
    {% endif %}
    <div class="search-wrapper">
        <input type="text" 
               id="{{ id }}" 
               class="search-input-styled prominent-search-input" 
               placeholder="{{ placeholder }}">
        <button type="button" 
                id="clear{{ id|capitalize }}" 
                class="search-clear-btn prominent-search-clear"
                onclick="clearSearch('{{ id }}')">
            ✕
        </button>
    </div>
    <div id="{{ id }}Results" class="prominent-search-results"></div>
</div>
```

Usage in parent template:
```html
{% include "components/search_bar.html" with context %}
```

#### 1.3.2: Month Navigator Component

Create `templates/components/month_navigator.html`:

```html
{#
  Month navigation component
  Args:
    - year, month, month_name
    - prev_year, prev_month, can_go_prev
    - next_year, next_month
    - is_current_month
#}
<div class="month-navigator">
    {% if can_go_prev %}
    <a href="/?year={{ prev_year }}&month={{ prev_month }}" class="month-nav-btn">
        <svg>...</svg>
    </a>
    {% else %}
    <div class="month-nav-btn disabled">
        <svg>...</svg>
    </div>
    {% endif %}
    
    <div class="month-display">
        <div class="month-name">{{ month_name }}</div>
        <div class="month-year">{{ year }}</div>
    </div>
    
    <a href="/?year={{ next_year }}&month={{ next_month }}" class="month-nav-btn">
        <svg>...</svg>
    </a>
</div>

{% if not is_current_month %}
<a href="/" class="btn-today">
    <svg>...</svg>
    Ir a Hoy
</a>
{% endif %}
```

#### 1.3.3: Status Pill Component

Create `templates/components/status_pill.html`:

```html
{#
  Status pill/badge component
  Args:
    - status: 'success' | 'danger' | 'pending'
    - label: text to display
    - icon: optional icon
    - onclick: optional click handler
#}
<button type="button" 
        class="status-pill status-{{ status }}"
        {% if onclick %}onclick="{{ onclick }}"{% endif %}>
    {% if icon %}<span class="icon">{{ icon }}</span>{% endif %}
    {{ label }}
</button>
```

#### 1.3.4: Tenant Card Component

Create `templates/components/tenant_card.html`:

```html
{#
  Tenant card for card view
  Args:
    - tenant: Tenant object
    - property_name: string
    - month_name: string (for WhatsApp message)
#}
<div class="tenant-item {% if tenant.paid %}paid{% endif %}" 
     data-property="{{ property_name }}" 
     data-tenant-id="{{ tenant.id }}">
    
    <input type="checkbox" class="tenant-checkbox" 
           id="tenant-{{ tenant.id }}" 
           data-id="{{ tenant.id }}"
           data-name="{{ tenant.name }}"
           data-phone="{{ tenant.phone }}"
           data-property="{{ property_name }}"
           {% if not tenant.paid %}checked{% endif %}>
    
    <div class="tenant-main-info">
        <div class="tenant-name">
            <span class="tenant-unit">({{ tenant.unit }})</span> {{ tenant.name }}
        </div>
        
        <div class="tenant-phone-inline">
            {% if tenant.phone %}
            <a href="tel:{{ tenant.phone }}">{{ tenant.phone }}</a>
            <button type="button" class="edit-phone-btn" 
                    onclick="editPhone('{{ tenant.id }}', '{{ tenant.phone }}')">
                Editar
            </button>
            {% else %}
            <div class="no-phone-warning">
                <span>SIN TELÉFONO</span>
                <button type="button" class="add-phone-btn" 
                        onclick="editPhone('{{ tenant.id }}', '')">
                    Agregar
                </button>
            </div>
            {% endif %}
        </div>
        
        {% if not tenant.paid and tenant.days_late >= 1 and tenant.days_late <= 7 %}
        {% include "components/late_fee_banner.html" %}
        {% endif %}
    </div>
    
    <div class="status-amount-row">
        {% include "components/payment_toggle.html" %}
        <div class="tenant-amount" data-base-rent="{{ tenant.rent }}">
            {% if not tenant.paid and tenant.late_fee > 0 %}
            <div class="tenant-rent tenant-rent--danger">
                ${{ "{:,.0f}".format(tenant.total_owed) }}
            </div>
            {% else %}
            <div class="tenant-rent">${{ "{:,.0f}".format(tenant.rent) }}</div>
            {% endif %}
        </div>
    </div>
    
    {% if tenant.phone and not tenant.paid %}
    {% include "components/whatsapp_button.html" %}
    {% endif %}
</div>
```

**Validation for each component:**
- [ ] Component renders correctly in isolation
- [ ] Component works when included in parent
- [ ] No visual differences from inline version
- [ ] All interactive elements work (clicks, toggles)

---

### Step 1.4: Extract Pagos Page (Days 6-8)

This is the largest template. Break it into sections:

1. Create `templates/pagos.html` that extends `base.html`
2. Replace inline HTML with `{% include %}` calls to components
3. Keep all JavaScript inline initially (move in Phase 2)

```html
{% extends "base.html" %}

{% block title %}RentasClaras - Envío de Recordatorios{% endblock %}

{% block inline_styles %}
    {# Copy all CSS from HTML_TEMPLATE here - we'll move to external in Phase 2 #}
{% endblock %}

{% block body %}
<div class="container">
    <header>
        <h1>🏠 RentasClaras</h1>
        {% include "components/top_navbar.html" %}
        {% include "components/month_navigator.html" %}
    </header>
    
    {% if expiring_contracts|length > 0 %}
    {% include "components/contract_expiry_alert.html" %}
    {% endif %}
    
    {% include "components/falta_cobrar_summary.html" %}
    
    {% if test_mode %}
    <div class="test-mode-banner">
        MODO PRUEBA — Los mensajes irán a tu número {{ test_phone }}, no a los inquilinos.
    </div>
    {% endif %}
    
    {% include "components/progress_bar.html" %}
    {% include "components/search_bar.html" with id="tenantSearch", placeholder="Ej: Claudia, Juan, María...", label="¿Quién pagó? Escribe su nombre:" %}
    {% include "components/property_filter_tabs.html" %}
    {% include "components/bulk_actions.html" %}
    {% include "components/view_toggle.html" %}
    
    {# Card View #}
    <div class="card-view" id="cardView" style="display: none;">
        {% for property_name, tenants in tenants_by_property.items() %}
        {% include "components/property_section.html" %}
        {% endfor %}
    </div>
    
    {# Table View #}
    <div class="excel-view" id="excelView" style="display: block;">
        {% for property_name, tenants in tenants_by_property.items() %}
        {% include "components/property_table.html" %}
        {% endfor %}
    </div>
</div>
{% endblock %}

{% block scripts %}
<script>
    {# Copy all JavaScript from HTML_TEMPLATE here - we'll move to external in Phase 2 #}
</script>
{% endblock %}
```

**Validation:**
- [ ] All payment toggles work
- [ ] Search filters correctly
- [ ] Property tabs filter correctly
- [ ] Month navigation works
- [ ] Card/Table view toggle works
- [ ] WhatsApp links work
- [ ] Bulk actions work
- [ ] Progress bar updates correctly

---

### Step 1.5: Extract Contratos Page (Days 9-10)

Similar process to Pagos. Create `templates/contratos.html`.

**Validation:**
- [ ] Contract list displays correctly
- [ ] Renewal status toggles work
- [ ] Search filters correctly
- [ ] Property tabs work
- [ ] Expiring contracts banner shows

---

### Step 1.6: Clean Up app.py (Day 11)

After all templates are extracted and validated:

1. Remove inline template strings (`HTML_TEMPLATE`, `CONTRACTS_TEMPLATE`, `LOGIN_TEMPLATE`)
2. Remove the feature flag (make external templates permanent)
3. Final line count target: ~800-1000 lines

**Validation:**
- [ ] All pages render correctly
- [ ] All functionality works
- [ ] No console errors
- [ ] App starts without errors

---

## 4. Phase 2: CSS Consolidation

### Overview

After templates are external, we consolidate CSS:

1. Extract CSS variables to `design-tokens.css`
2. Extract component styles to `components.css`
3. Replace inline styles with classes
4. Remove duplicate CSS

---

### Step 2.1: Create Design Tokens File (Day 12)

Create `static/css/design-tokens.css`:

```css
/**
 * RentasClaras Design Tokens
 * Single source of truth for all design values
 * 
 * Usage: Link this file FIRST in base.html
 */

:root {
    /* ===========================================
       COLOR PALETTE
       3-color system: Green (success), Red (danger), Gray (neutral)
       =========================================== */
    
    /* Primary - Success, Paid, Positive Actions */
    --color-success: #0A7A0A;
    --color-success-dark: #085A08;
    --color-success-light: #DCFCE7;
    --color-success-rgb: 10, 122, 10;
    
    /* Danger - Unpaid, Warnings, Negative Actions */
    --color-danger: #CC0000;
    --color-danger-dark: #990000;
    --color-danger-light: #FEE2E2;
    --color-danger-rgb: 204, 0, 0;
    
    /* Neutral - Text, Borders, Backgrounds */
    --color-neutral: #333333;
    --color-neutral-light: #F5F5F5;
    --color-neutral-lighter: #FAFAFA;
    --color-border: #CCCCCC;
    --color-border-light: #E5E5E5;
    
    /* Base Colors */
    --color-white: #FFFFFF;
    --color-black: #000000;
    
    /* Warning (for late fees) */
    --color-warning: #F59E0B;
    --color-warning-dark: #D97706;
    --color-warning-light: #FEF3C7;
    
    /* ===========================================
       TYPOGRAPHY
       =========================================== */
    
    /* Font Family */
    --font-family-base: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    
    /* Font Sizes - Mobile First */
    --font-size-xs: 0.875rem;   /* 14px */
    --font-size-sm: 1rem;       /* 16px - MINIMUM for body */
    --font-size-base: 1.125rem; /* 18px */
    --font-size-lg: 1.25rem;    /* 20px */
    --font-size-xl: 1.5rem;     /* 24px */
    --font-size-2xl: 1.875rem;  /* 30px */
    --font-size-3xl: 2.25rem;   /* 36px */
    
    /* Font Weights */
    --font-weight-normal: 400;
    --font-weight-medium: 500;
    --font-weight-semibold: 600;
    --font-weight-bold: 700;
    --font-weight-extrabold: 800;
    
    /* Line Heights */
    --line-height-tight: 1.2;
    --line-height-base: 1.6;
    --line-height-relaxed: 1.75;
    
    /* ===========================================
       SPACING
       =========================================== */
    --space-xs: 4px;
    --space-sm: 8px;
    --space-md: 16px;
    --space-lg: 24px;
    --space-xl: 32px;
    --space-2xl: 48px;
    
    /* ===========================================
       TOUCH TARGETS
       48px minimum for accessibility (WCAG)
       =========================================== */
    --touch-target-min: 48px;
    --touch-target-md: 56px;
    --touch-target-lg: 72px;
    
    /* ===========================================
       BORDER RADIUS
       =========================================== */
    --radius-sm: 8px;
    --radius-md: 12px;
    --radius-lg: 16px;
    --radius-xl: 24px;
    --radius-full: 9999px;
    
    /* ===========================================
       SHADOWS
       =========================================== */
    --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);
    --shadow-md: 0 2px 8px rgba(0, 0, 0, 0.08);
    --shadow-lg: 0 4px 12px rgba(0, 0, 0, 0.12);
    --shadow-xl: 0 8px 24px rgba(0, 0, 0, 0.16);
    
    /* ===========================================
       TRANSITIONS
       =========================================== */
    --transition-fast: 0.15s ease;
    --transition-base: 0.2s ease;
    --transition-slow: 0.3s ease;
    
    /* ===========================================
       SAFE AREAS (Notched phones)
       =========================================== */
    --safe-area-top: env(safe-area-inset-top, 0px);
    --safe-area-bottom: env(safe-area-inset-bottom, 0px);
    --safe-area-left: env(safe-area-inset-left, 0px);
    --safe-area-right: env(safe-area-inset-right, 0px);
    
    /* ===========================================
       Z-INDEX SCALE
       =========================================== */
    --z-dropdown: 100;
    --z-sticky: 200;
    --z-modal: 300;
    --z-toast: 400;
    --z-nav: 1000;
}

/* Dark mode support (future) */
@media (prefers-color-scheme: dark) {
    :root {
        /* Define dark mode overrides here when ready */
    }
}
```

---

### Step 2.2: Create Base Styles (Day 13)

Create `static/css/base.css`:

```css
/**
 * RentasClaras Base Styles
 * Reset, typography, and layout primitives
 */

/* ===========================================
   CSS RESET
   =========================================== */
*, *::before, *::after {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

html {
    -webkit-text-size-adjust: 100%;
    -webkit-tap-highlight-color: transparent;
}

body {
    font-family: var(--font-family-base);
    font-size: var(--font-size-base);
    line-height: var(--line-height-base);
    color: var(--color-black);
    background: var(--color-white);
    min-height: 100vh;
    min-height: -webkit-fill-available;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}

/* ===========================================
   TYPOGRAPHY
   =========================================== */
h1, h2, h3, h4, h5, h6 {
    font-weight: var(--font-weight-extrabold);
    line-height: var(--line-height-tight);
}

h1 { font-size: var(--font-size-2xl); }
h2 { font-size: var(--font-size-xl); }
h3 { font-size: var(--font-size-lg); }

@media (min-width: 768px) {
    h1 { font-size: var(--font-size-3xl); }
    h2 { font-size: var(--font-size-2xl); }
}

a {
    color: inherit;
    text-decoration: none;
}

/* ===========================================
   LAYOUT UTILITIES
   =========================================== */
.container {
    width: 100%;
    max-width: 100%;
    margin: 0 auto;
    padding: var(--space-md);
    padding-top: calc(var(--space-md) + var(--safe-area-top));
    padding-bottom: calc(80px + var(--safe-area-bottom));
}

@media (min-width: 768px) {
    .container {
        max-width: 720px;
        padding: var(--space-lg);
        padding-bottom: var(--space-lg);
    }
}

@media (min-width: 1024px) {
    .container {
        max-width: 900px;
        padding: var(--space-xl);
    }
}

/* Flexbox utilities */
.flex { display: flex; }
.flex-col { flex-direction: column; }
.flex-wrap { flex-wrap: wrap; }
.items-center { align-items: center; }
.justify-center { justify-content: center; }
.justify-between { justify-content: space-between; }
.gap-sm { gap: var(--space-sm); }
.gap-md { gap: var(--space-md); }
.gap-lg { gap: var(--space-lg); }

/* ===========================================
   ACCESSIBILITY
   =========================================== */

/* Focus styles */
:focus-visible {
    outline: 3px solid var(--color-success);
    outline-offset: 2px;
}

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.01ms !important;
    }
}

/* Prevent zoom on input focus (iOS) */
@supports (-webkit-touch-callout: none) {
    input, select, textarea {
        font-size: 16px !important;
    }
}
```

---

### Step 2.3: Create Components CSS (Days 14-16)

Create `static/css/components.css`:

```css
/**
 * RentasClaras Component Styles
 * Reusable UI components
 */

/* ===========================================
   BUTTONS
   =========================================== */
.btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: var(--space-sm);
    padding: var(--space-md) var(--space-lg);
    border: none;
    border-radius: var(--radius-md);
    font-size: var(--font-size-base);
    font-weight: var(--font-weight-bold);
    cursor: pointer;
    transition: all var(--transition-base);
    min-height: var(--touch-target-md);
    width: 100%;
}

@media (min-width: 768px) {
    .btn {
        width: auto;
        min-height: var(--touch-target-lg);
        padding: var(--space-lg) var(--space-xl);
        font-size: var(--font-size-lg);
    }
}

.btn--primary {
    background: var(--color-success);
    color: var(--color-white);
}

.btn--primary:hover {
    background: var(--color-success-dark);
}

.btn--secondary {
    background: var(--color-neutral-light);
    color: var(--color-black);
    border: 3px solid var(--color-border);
}

.btn--secondary:hover {
    background: var(--color-border);
}

.btn--danger {
    background: var(--color-white);
    color: var(--color-danger);
    border: 3px solid var(--color-danger);
}

.btn--danger:hover {
    background: var(--color-danger);
    color: var(--color-white);
}

/* ===========================================
   STATUS PILL
   Unified component for payment status, renewal status, etc.
   =========================================== */
.status-pill {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: var(--space-sm);
    padding: var(--space-md) var(--space-lg);
    border: 4px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-white);
    cursor: pointer;
    font-size: var(--font-size-base);
    font-weight: var(--font-weight-extrabold);
    transition: all var(--transition-base);
    min-height: var(--touch-target-md);
    user-select: none;
}

.status-pill--success {
    border-color: var(--color-success);
    color: var(--color-success);
}

.status-pill--success:hover {
    background: var(--color-success);
    color: var(--color-white);
}

.status-pill--danger {
    border-color: var(--color-danger);
    color: var(--color-danger);
}

.status-pill--danger:hover {
    background: var(--color-danger);
    color: var(--color-white);
}

.status-pill--pending {
    background: var(--color-neutral-light);
    border-color: var(--color-neutral);
    color: var(--color-neutral);
}

/* Touch device adjustments */
@media (hover: none) {
    .status-pill--success:hover {
        background: var(--color-white);
        color: var(--color-success);
    }
    .status-pill--success:active {
        background: var(--color-success);
        color: var(--color-white);
    }
    
    .status-pill--danger:hover {
        background: var(--color-white);
        color: var(--color-danger);
    }
    .status-pill--danger:active {
        background: var(--color-danger);
        color: var(--color-white);
    }
}

/* ===========================================
   CARDS
   =========================================== */
.card {
    background: var(--color-white);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-md);
    overflow: hidden;
}

.card__header {
    background: var(--color-neutral);
    color: var(--color-white);
    padding: var(--space-md);
    font-weight: var(--font-weight-extrabold);
}

.card__body {
    padding: var(--space-md);
}

/* ===========================================
   SEARCH BAR
   =========================================== */
.search-bar {
    position: relative;
    width: 100%;
}

.search-bar__input {
    width: 100%;
    padding: var(--space-md);
    padding-left: var(--space-2xl);
    padding-right: var(--space-2xl);
    font-size: var(--font-size-lg);
    border: 3px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-white);
}

.search-bar__input:focus {
    outline: none;
    border-color: var(--color-success);
}

.search-bar__icon {
    position: absolute;
    left: var(--space-md);
    top: 50%;
    transform: translateY(-50%);
    color: var(--color-neutral);
    pointer-events: none;
}

.search-bar__clear {
    position: absolute;
    right: 0;
    top: 0;
    bottom: 0;
    width: var(--touch-target-min);
    display: none;
    align-items: center;
    justify-content: center;
    background: none;
    border: none;
    font-size: var(--font-size-xl);
    cursor: pointer;
    color: var(--color-neutral);
}

.search-bar__clear:hover {
    color: var(--color-danger);
}

.search-bar__clear.is-visible {
    display: flex;
}

/* ===========================================
   BOTTOM NAVIGATION
   =========================================== */
.bottom-nav {
    display: flex;
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background: var(--color-white);
    border-top: 2px solid var(--color-border);
    padding: var(--space-sm);
    padding-bottom: calc(var(--space-sm) + var(--safe-area-bottom));
    z-index: var(--z-nav);
    justify-content: space-around;
    gap: var(--space-sm);
    box-shadow: 0 -4px 12px rgba(0, 0, 0, 0.1);
}

@media (min-width: 768px) {
    .bottom-nav {
        display: none;
    }
}

.bottom-nav__item {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-decoration: none;
    color: var(--color-neutral);
    font-size: var(--font-size-xs);
    font-weight: var(--font-weight-bold);
    padding: var(--space-sm);
    border-radius: var(--radius-sm);
    min-width: 64px;
    min-height: var(--touch-target-min);
    transition: all var(--transition-base);
}

.bottom-nav__item.is-active {
    color: var(--color-success);
    background: rgba(var(--color-success-rgb), 0.1);
}

.bottom-nav__icon {
    font-size: 1.5rem;
    margin-bottom: 2px;
}

/* ... more components ... */
```

---

### Step 2.4: Replace Inline Styles Gradually (Days 17-20)

For each template, systematically replace inline styles:

**Before:**
```html
<div style="background: #333333; color: white; width: 72px; height: 72px; border-radius: 50%; display: flex; align-items: center; justify-content: center;">
```

**After:**
```html
<div class="month-nav-btn">
```

**Process for each file:**

1. Identify all `style=""` attributes
2. Group similar styles (these become components)
3. Create CSS classes in `components.css`
4. Replace inline styles with class names
5. Test visually after each change
6. Commit frequently

**Tracking spreadsheet:**

| File | Total Inline Styles | Replaced | Remaining |
|------|---------------------|----------|-----------|
| pagos.html | ~150 | 0 | 150 |
| contratos.html | ~80 | 0 | 80 |
| ... | ... | ... | ... |

---

### Step 2.5: Link External CSS (Day 21)

Update `templates/base.html`:

```html
<head>
    <!-- Design Tokens MUST be first -->
    <link rel="stylesheet" href="{{ url_for('static', filename='css/design-tokens.css') }}">
    <link rel="stylesheet" href="{{ url_for('static', filename='css/base.css') }}">
    <link rel="stylesheet" href="{{ url_for('static', filename='css/components.css') }}">
    
    {% block page_styles %}{% endblock %}
</head>
```

For page-specific styles:
```html
{% block page_styles %}
<link rel="stylesheet" href="{{ url_for('static', filename='css/pages/pagos.css') }}">
{% endblock %}
```

---

## 5. Rollback Strategy

### If Something Breaks

1. **Immediate rollback:** Set `USE_EXTERNAL_TEMPLATES=false` in environment
2. **Deploy:** The old inline templates will be used
3. **Investigate:** Compare old vs new template output
4. **Fix:** Correct the issue in external template
5. **Re-deploy:** Set flag back to `true`

### Git Strategy

```bash
# Create a feature branch for each phase
git checkout -b refactor/phase-1-login-template

# Make small, atomic commits
git commit -m "Extract login template to external file"
git commit -m "Add feature flag for template switching"
git commit -m "Update login route to use external template"

# Create PR for review before merging
# After merge, wait 24 hours before removing old code
```

---

## 6. Validation Checklist

### After Each Template Extraction

- [ ] HTML output matches original (use diff)
- [ ] All buttons/links work
- [ ] All forms submit correctly
- [ ] All JavaScript functionality works
- [ ] No console errors
- [ ] Page loads in < 2 seconds
- [ ] Looks correct on iPhone SE (375px)
- [ ] Looks correct on iPad (768px)
- [ ] Looks correct on Desktop (1280px)

### After CSS Consolidation

- [ ] All colors use CSS variables
- [ ] No inline styles remain
- [ ] No duplicate CSS rules
- [ ] File sizes are smaller
- [ ] Page loads faster (measure with Lighthouse)
- [ ] Contrast ratios meet WCAG AA
- [ ] Touch targets are ≥ 48px

### Final Validation

- [ ] All pages load without error
- [ ] All API endpoints work
- [ ] Payment toggles sync correctly
- [ ] WhatsApp links work
- [ ] Search filters work
- [ ] Month navigation works
- [ ] Login/logout works
- [ ] Mobile PWA installs correctly

---

## 📅 Timeline Summary

| Week | Phase | Deliverable |
|------|-------|-------------|
| Week 1 | Setup + Login | Feature flags, login.html extracted |
| Week 1 | Base Template | base.html with shared layout |
| Week 2 | Components | All reusable components extracted |
| Week 2 | Pagos Page | pagos.html complete |
| Week 3 | Contratos Page | contratos.html complete |
| Week 3 | Cleanup | Remove inline templates from app.py |
| Week 4 | CSS Phase 1 | design-tokens.css, base.css |
| Week 4 | CSS Phase 2 | components.css |
| Week 5 | CSS Phase 3 | Replace all inline styles |
| Week 5 | Polish | Final testing, optimization |

**Total estimated time:** 5 weeks (working part-time)

---

## 🚀 Getting Started

To begin the migration:

```bash
cd rentas-claras

# 1. Create directory structure
mkdir -p templates/components static/css/pages static/js

# 2. Create the feature flag (add to .env)
echo "USE_EXTERNAL_TEMPLATES=false" >> .env
echo "USE_EXTERNAL_CSS=false" >> .env

# 3. Create the first template
touch templates/login.html

# 4. Start migrating!
```

---

*Document maintained by: UX Engineering Team*  
*Last updated: December 29, 2024*
