# Citation Popup Implementation - Frontend Changes

## Status
Backend changes: COMPLETE ✅
Frontend changes: IN PROGRESS

## Backend Changes (COMPLETED)

1. ✅ `tools/citation_formatter.py` - Added `get_citations_as_json()` method
2. ✅ `tools/gemini_query_engine.py` - Modified to return `citations` array in result
3. ✅ `web_app.py` - Updated API to include `citations` in JSON response

## Frontend Changes Needed (templates/index.html)

### Step 1: Add Citation Popup HTML Structure

Find the closing `</body>` tag and add BEFORE it:

```html
<!-- Citation Popup Container -->
<div id="citation-popup" class="citation-popup">
    <div class="citation-header"></div>
    <div class="citation-body"></div>
</div>
```

### Step 2: Add Citation Popup CSS

Find the `<style>` section (around line 50-200) and locate the existing `.citation` class.

**REPLACE the existing citation CSS:**
```css
.citation {
    font-size: 11px;
    color: #667eea;
    font-weight: 600;
    cursor: pointer;
    display: inline-block;
    margin: 0 2px;
}
```

**WITH this NotebookLM-style CSS:**
```css
/* Superscript Citation Numbers */
.citation {
    color: #667eea;
    font-weight: 600;
    cursor: pointer;
    text-decoration: none;
    padding: 1px 3px;
    border-radius: 3px;
    transition: background 0.2s;
    font-size: 0.75em;
    vertical-align: super;
    line-height: 0;
    position: relative;
}

.citation:hover {
    background: rgba(102, 126, 234, 0.15);
}

/* Citation Popup Tooltip */
.citation-popup {
    position: fixed;
    background: white;
    border: 2px solid #667eea;
    border-radius: 12px;
    padding: 16px;
    box-shadow: 0 10px 40px rgba(0,0,0,0.25);
    max-width: 450px;
    min-width: 300px;
    z-index: 10000;
    display: none;
    font-size: 13px;
    line-height: 1.5;
}

.citation-popup.active {
    display: block;
}

.citation-popup .citation-header {
    font-weight: 700;
    color: #667eea;
    margin-bottom: 12px;
    font-size: 14px;
    border-bottom: 1px solid #e0e0e0;
    padding-bottom: 8px;
}

.citation-popup .citation-body {
    color: #333;
}

.citation-popup .citation-detail {
    margin: 6px 0;
    display: flex;
    gap: 8px;
}

.citation-popup .citation-detail strong {
    color: #555;
    min-width: 80px;
    flex-shrink: 0;
}

.citation-popup .citation-detail span {
    color: #333;
    flex: 1;
}
```

### Step 3: Update JavaScript - Add Global Citation Storage

Find the `<script>` section and add at the TOP (before any functions):

```javascript
// Global citation storage for popups
let currentCitations = {};
```

### Step 4: Update formatAnswer() Function

Find the `formatAnswer` function (around line 700-750) and REPLACE the citation formatting section.

**FIND this code:**
```javascript
// Convert citations [1], [2], etc.
formatted = formatted.replace(/\[(\d+)\]/g, '<span class="citation">[$1]</span>');
```

**REPLACE WITH:**
```javascript
// Store citations for popup access
currentCitations = {};

// Convert [1] to superscript with data attributes
formatted = formatted.replace(/\[(\d+)\]/g, '<sup class="citation" data-citation="$1">$1</sup>');
```

### Step 5: Add Citation Popup JavaScript Functions

Add these functions at the END of the `<script>` section (before the closing `</script>` tag):

```javascript
// ===== CITATION POPUP FUNCTIONS =====

function attachCitationHandlers() {
    document.querySelectorAll('.citation').forEach(el => {
        el.addEventListener('mouseenter', showCitationPopup);
        el.addEventListener('mouseleave', hideCitationPopup);
    });
}

function showCitationPopup(event) {
    const citNum = parseInt(event.target.dataset.citation);
    const citation = currentCitations[citNum];

    if (!citation) {
        console.warn('Citation not found:', citNum);
        return;
    }

    const popup = document.getElementById('citation-popup');
    const header = popup.querySelector('.citation-header');
    const body = popup.querySelector('.citation-body');

    // Build popup content based on citation type
    if (citation.type === 'asset_data') {
        header.textContent = `[${citation.number}] Asset Data`;

        let bodyHTML = '';
        if (citation.source_file) {
            bodyHTML += `<div class="citation-detail"><strong>Source:</strong><span>${citation.source_file}</span></div>`;
        }
        if (citation.sheet_name) {
            bodyHTML += `<div class="citation-detail"><strong>Sheet:</strong><span>${citation.sheet_name}</span></div>`;
        }
        if (citation.field) {
            bodyHTML += `<div class="citation-detail"><strong>Field:</strong><span>${citation.field}</span></div>`;
        }
        if (citation.filter) {
            bodyHTML += `<div class="citation-detail"><strong>Filter:</strong><span>${citation.filter}</span></div>`;
        }
        if (citation.count !== undefined) {
            bodyHTML += `<div class="citation-detail"><strong>Records:</strong><span>${citation.count.toLocaleString()}</span></div>`;
        }
        if (citation.asset_ids && citation.asset_ids.length > 0) {
            const idsDisplay = citation.asset_ids.slice(0, 5).join(', ');
            const remaining = citation.count > citation.asset_ids.length ? ` +${citation.count - citation.asset_ids.length} more` : '';
            bodyHTML += `<div class="citation-detail"><strong>Asset IDs:</strong><span>${idsDisplay}${remaining}</span></div>`;
        }

        body.innerHTML = bodyHTML;

    } else if (citation.type === 'iso_standard') {
        header.textContent = `[${citation.number}] ${citation.standard || 'ISO Standard'}`;

        let bodyHTML = '';
        if (citation.section) {
            bodyHTML += `<div class="citation-detail"><strong>Section:</strong><span>${citation.section}${citation.title ? ' - ' + citation.title : ''}</span></div>`;
        }
        if (citation.pages) {
            bodyHTML += `<div class="citation-detail"><strong>Pages:</strong><span>${citation.pages}</span></div>`;
        }
        if (citation.quote) {
            const shortQuote = citation.quote.length > 150 ? citation.quote.substring(0, 150) + '...' : citation.quote;
            bodyHTML += `<div class="citation-detail"><strong>Excerpt:</strong><span><em>"${shortQuote}"</em></span></div>`;
        }

        body.innerHTML = bodyHTML;

    } else if (citation.type === 'calculation') {
        header.textContent = `[${citation.number}] Calculation`;

        let bodyHTML = '';
        if (citation.description) {
            bodyHTML += `<div class="citation-detail"><strong>Description:</strong><span>${citation.description}</span></div>`;
        }
        if (citation.formula) {
            bodyHTML += `<div class="citation-detail"><strong>Formula:</strong><span><code>${citation.formula}</code></span></div>`;
        }
        if (citation.sources && citation.sources.length > 0) {
            bodyHTML += `<div class="citation-detail"><strong>Sources:</strong><span>${citation.sources.join(', ')}</span></div>`;
        }

        body.innerHTML = bodyHTML;
    }

    // Position popup near cursor (with bounds checking)
    const rect = event.target.getBoundingClientRect();
    let left = rect.right + 10;
    let top = rect.top;

    // Show popup to measure it
    popup.style.left = left + 'px';
    popup.style.top = top + 'px';
    popup.classList.add('active');

    // Adjust if off-screen
    const popupRect = popup.getBoundingClientRect();

    if (popupRect.right > window.innerWidth) {
        left = rect.left - popupRect.width - 10;
        popup.style.left = left + 'px';
    }

    if (popupRect.bottom > window.innerHeight) {
        top = window.innerHeight - popupRect.height - 20;
        popup.style.top = top + 'px';
    }

    if (top < 0) {
        popup.style.top = '10px';
    }
}

function hideCitationPopup() {
    const popup = document.getElementById('citation-popup');
    popup.classList.remove('active');
}
```

### Step 6: Update sendMessage() to Pass Citations

Find the `sendMessage()` function and locate the section that handles successful responses.

**FIND this code:**
```javascript
} else {
    // Regular answer
    addMessage('assistant', formatAnswer(data.answer));
}
```

**REPLACE WITH:**
```javascript
} else {
    // Regular answer with citations
    // Store citations globally for popup access
    if (data.citations && Array.isArray(data.citations)) {
        currentCitations = {};
        data.citations.forEach(cit => {
            currentCitations[cit.number] = cit;
        });
    }

    addMessage('assistant', formatAnswer(data.answer));

    // Attach popup handlers after DOM update
    setTimeout(() => attachCitationHandlers(), 100);
}
```

## Testing Checklist

After making all changes:

1. Restart the Flask server:
   ```bash
   # Kill existing server (Ctrl+C)
   py web_app.py
   ```

2. Open browser to http://localhost:5000

3. Ask a query that will generate citations, for example:
   - "How many poor condition assets do we have?"
   - "What does ISO 55001 say about asset management?"

4. Verify:
   - [ ] Citations appear as superscript numbers (not [1])
   - [ ] Hovering shows elegant tooltip with source details
   - [ ] Popup positions correctly near the citation
   - [ ] Popup hides when mouse leaves
   - [ ] Multiple citations work correctly
   - [ ] Mobile responsive (test if needed)

## Expected Result

**Before:**
```
Poor assets [1] need attention.

━━━━━━━━━━━━━━━
REFERENCES
━━━━━━━━━━━━━━━
[1] Asset Data...
```

**After:**
```
Poor assets¹ need attention.

[Hover ¹ shows elegant popup:]
┌────────────────────────────────┐
│ [1] Asset Data                 │
│ ────────────────────────────── │
│ Source: Asset register Part 1  │
│ Sheet: Sheet1                  │
│ Field: Condition               │
│ Filter: Condition = Poor       │
│ Records: 312                   │
│ Asset IDs: A-001, A-002, ...   │
└────────────────────────────────┘
```

## Files Modified Summary

1. `tools/citation_formatter.py` - Added `get_citations_as_json()` ✅
2. `tools/gemini_query_engine.py` - Return citations array ✅
3. `web_app.py` - Include citations in API response ✅
4. `templates/index.html` - Add popup HTML, CSS, JavaScript ⏳

## Troubleshooting

**Popup not showing:**
- Check browser console for JavaScript errors
- Verify citations array is in API response (F12 -> Network tab)
- Ensure `currentCitations` is being populated

**Citations not superscript:**
- Check CSS loaded correctly
- Verify regex replacement in `formatAnswer()`

**Popup positioning wrong:**
- Check `position: fixed` in CSS
- Verify bounds checking logic

---

**Created**: 2026-01-31
**Version**: 1.0
**Status**: Backend Complete, Frontend Pending
