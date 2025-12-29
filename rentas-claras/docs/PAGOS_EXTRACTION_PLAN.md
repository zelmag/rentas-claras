# Pagos Template Extraction Plan
## Root Cause Analysis & Safe Extraction Strategy

**Created:** December 29, 2024  
**Status:** PLANNED  
**Risk Level:** High (learned from failure)

---

## 🔴 What Broke (Root Cause Analysis)

### The Problem
The pagos page showed **64 tenants instead of 32** and **$514,600 instead of ~$257,300** - exactly **double** the correct values.

### Why It Broke

I used a Python regex script to extract the HTML_TEMPLATE:

```python
# BAD APPROACH - The regex that caused the problem
body_match = re.search(r'<body>(.*?)</body>', html_content, re.DOTALL)
scripts_match = re.search(r'(<script>.*)</body>', html_content, re.DOTALL)
```

**The issue:** The original `HTML_TEMPLATE` has this structure:
```html
<body>
    <div class="container">
        <!-- CONTENT WITH TENANT LOOPS -->
        {% for property_name, tenants in tenants_by_property.items() %}
            <!-- Card view -->
        {% endfor %}
        
        {% for property_name, tenants in tenants_by_property.items() %}
            <!-- Table view -->
        {% endfor %}
    </div>
    
    <nav class="bottom-nav">...</nav>
    
    <script>
        // JavaScript code
    </script>
</body>
```

My extraction script:
1. **`{% block body %}`** captured everything from `<body>` to `</body>` (including scripts)
2. **`{% block scripts %}`** captured from `<script>` to `</body>` again

**Result:** The body content was included TWICE:
- Once in `{% block body %}` (with scripts at the end)
- And the scripts block ALSO included part of the body structure

This created **duplicate tenant loops** in the rendered output.

---

## 🟢 New Approach: Manual, Precise Extraction

### Why This Won't Break Again

| Old Approach | New Approach |
|--------------|--------------|
| Regex-based automated extraction | Manual, line-by-line extraction |
| Captured overlapping content | Clear boundary identification |
| No validation step | Multiple validation checkpoints |
| All-or-nothing | Incremental with testing |

### The New Strategy

**Step 1: Identify Exact Line Numbers**
```
HTML_TEMPLATE structure in app.py:
├── Line 364: HTML_TEMPLATE = """
├── Line 365-376: <!DOCTYPE>, <head> opening, meta tags
├── Line 377-2617: <style>...</style>
├── Line 2618: </head>
├── Line 2619: <body>
├── Line 2620-3520: Body content (tenant loops, cards, tables)
├── Line 3521-3540: Bottom navigation
├── Line 3541-5974: <script>...</script>
├── Line 5975: </body>
├── Line 5976: </html>
└── Line 5977: """
```

**Step 2: Extract to Separate Blocks**

I will create `pagos.html` with this structure:

```html
{% extends "base.html" %}

{% block title %}RentasClaras - Envío de Recordatorios{% endblock %}

{% block head_extra %}
<!-- SheetJS library for Excel export -->
<script src="https://cdn.sheetjs.com/xlsx-0.20.1/package/dist/xlsx.full.min.js"></script>
{% endblock %}

{% block styles %}
<style>
    /* ONLY lines 378-2616 from app.py - just the CSS */
</style>
{% endblock %}

{% block body %}
    <!-- ONLY lines 2620-3520 from app.py - just the HTML body content -->
    <!-- NO scripts here -->
{% endblock %}

{# Override bottom_nav since pagos has its own nav in body #}
{% block bottom_nav %}{% endblock %}

{% block scripts %}
<script>
    /* ONLY lines 3542-5973 from app.py - just the JavaScript */
</script>
{% endblock %}
```

**Step 3: Validation Checkpoints**

Before enabling the new template:

1. **Line Count Validation**
   ```bash
   # Count tenant loops - should be EXACTLY 4 (2 card view + 2 table view)
   grep -c "for property_name, tenants in tenants_by_property" templates/pagos.html
   # Expected: 4
   ```

2. **Structure Validation**
   ```bash
   # Count block definitions - should be exactly 5
   grep -c "{% block" templates/pagos.html
   # Expected: 5 (title, head_extra, styles, body, bottom_nav, scripts)
   ```

3. **Render Comparison**
   ```bash
   # Compare output of old vs new template
   curl -s [old_inline] > /tmp/old.html
   curl -s [new_external] > /tmp/new.html
   diff /tmp/old.html /tmp/new.html
   # Expected: No differences (or minimal whitespace only)
   ```

4. **Tenant Count Check**
   ```bash
   # This is the critical check that would have caught the bug
   curl -s [page] | grep -o "tenant-item" | wc -l
   # Expected: 32 (or 64 for card+table if both views)
   # NOT: 128 (which would indicate duplication)
   ```

---

## 📋 Step-by-Step Execution Plan

### Phase 1: Preparation (5 min)
- [ ] Read app.py lines 364-5977 to understand exact structure
- [ ] Identify exact line numbers for each section
- [ ] Create a map of what goes where

### Phase 2: Manual Extraction (20 min)

**Step 2.1: Extract Styles**
```bash
# Extract ONLY the <style> content (lines ~377-2617)
sed -n '377,2617p' app.py > /tmp/pagos_styles.txt
```

**Step 2.2: Extract Body Content**
```bash
# Extract ONLY the body HTML (lines ~2620-3520)
# This is the content BEFORE the first <script> tag
sed -n '2620,3520p' app.py > /tmp/pagos_body.txt
```

**Step 2.3: Extract Scripts**
```bash
# Extract ONLY the JavaScript (lines ~3541-5973)
sed -n '3541,5973p' app.py > /tmp/pagos_scripts.txt
```

**Step 2.4: Assemble pagos.html**
Manually combine the three files with proper Jinja2 block wrappers.

### Phase 3: Validation (10 min)

**Check 1: Structure**
```bash
# Verify block count
grep -c "{% block" templates/pagos.html
# Must be: 6

# Verify endblock count
grep -c "{% endblock" templates/pagos.html  
# Must be: 6
```

**Check 2: No Duplication**
```bash
# Count tenant loops
grep -c "for property_name, tenants in tenants_by_property" templates/pagos.html
# Must be: 4 (NOT 8 or more)

# Count bottom-nav sections
grep -c "bottom-nav" templates/pagos.html
# Should be: 1 or 2 (NOT 4+)
```

**Check 3: Feature Flag Test**
```bash
# Enable external template
export USE_EXTERNAL_PAGOS=true

# Check tenant count matches original
curl -s [page] | grep -o 'data-tenant-id' | wc -l
# Must match original count
```

### Phase 4: Comparison Test (5 min)

```bash
# Save output from inline template
USE_EXTERNAL_PAGOS=false
curl -s http://localhost:5001/ > /tmp/inline_output.html

# Save output from external template  
USE_EXTERNAL_PAGOS=true
curl -s http://localhost:5001/ > /tmp/external_output.html

# Compare (ignore whitespace)
diff -w /tmp/inline_output.html /tmp/external_output.html | head -50
```

---

## 🛡️ Safety Mechanisms

### 1. Feature Flag (Already in Place)
```python
if get_feature_flag("use_external_pagos"):
    return render_template("pagos.html", **template_vars)
else:
    return render_template_string(HTML_TEMPLATE, **template_vars)
```

### 2. Instant Rollback
```bash
# If ANYTHING is wrong:
echo "USE_EXTERNAL_PAGOS=false" >> .env
# Restart app - immediately back to working inline template
```

### 3. Automated Validation Script
I'll create a validation script that runs BEFORE enabling the feature flag:

```python
# validate_pagos_template.py
def validate():
    """Validate pagos.html before enabling"""
    
    with open('templates/pagos.html') as f:
        content = f.read()
    
    # Check 1: Block count
    blocks = content.count('{% block')
    assert blocks == 6, f"Expected 6 blocks, got {blocks}"
    
    # Check 2: No duplicate tenant loops
    loops = content.count('for property_name, tenants in tenants_by_property')
    assert loops == 4, f"Expected 4 tenant loops, got {loops}"
    
    # Check 3: Single bottom-nav (in body, overridden)
    # The body should NOT have its own bottom-nav if base.html has one
    
    print("✅ All validations passed!")
    return True
```

---

## 🎯 Success Criteria

Before declaring the extraction complete:

| Check | Expected | Actual |
|-------|----------|--------|
| HTTP Response | 200 | |
| Tenant count | 32 | |
| Total rent | ~$257,300 | |
| Payment toggles work | Yes | |
| Search works | Yes | |
| Month navigation works | Yes | |
| Visual identical to inline | Yes | |

---

## ⏱️ Timeline

| Phase | Duration | Description |
|-------|----------|-------------|
| Preparation | 5 min | Read and map app.py structure |
| Extraction | 20 min | Manual line-by-line extraction |
| Validation | 10 min | Run all checks |
| Testing | 10 min | Manual UI testing |
| **Total** | **45 min** | |

---

## 📝 Lessons Learned

1. **Never use regex for complex template extraction** - The HTML structure with nested loops and scripts is too complex for simple pattern matching.

2. **Always validate tenant counts** - This would have caught the bug immediately.

3. **Extract to separate files first, then combine** - This prevents overlap issues.

4. **Feature flags are essential** - The instant rollback saved us from a broken production state.

5. **Test with real data** - The duplication was only visible with actual tenant data, not with empty templates.

---

*Document created after the failed extraction attempt on December 29, 2024*
