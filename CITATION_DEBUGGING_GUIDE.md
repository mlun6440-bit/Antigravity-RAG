# Citation Popup Debugging Guide

## Current Status

Citation popups are **not appearing** in the main web application, despite all code being present in [templates/index.html](templates/index.html).

## Quick Test

1. **Open the test page**: [test_citations.html](test_citations.html) was just created
2. **Hover over the blue superscript numbers** (1, 2, 3)
3. **Check if popups appear**

### Test Results:

- ✅ **If popups WORK** in test page → Issue is with the main app's citation loading/rendering
- ❌ **If popups DON'T WORK** in test page → Browser compatibility or CSS issue

---

## Debugging Steps for Main Web Application

### Step 1: Check Browser Console

1. Open the web application at `http://localhost:5000`
2. Press **F12** to open DevTools
3. Click the **Console** tab
4. Ask a question that triggers ISO citations (e.g., "What are the risk management requirements in ISO 55001?")
5. Hover over citation numbers in the response
6. **Look for these debug messages:**

```
[Citations] Loaded X citations: {1: {...}, 2: {...}}
[Citations] Attached handlers to X citation elements
[Citation Popup] Showing citation: X
[Citation Popup] Citation data: {...}
[Citation Popup] Popup activated at position: {left: X, top: Y}
```

### Step 2: Diagnose Based on Console Output

#### Scenario A: No "[Citations] Loaded" message
**Problem:** Citations not being received from API
**Check:**
- Network tab → Check `/query` API response
- Verify `citations` array exists in response JSON
- Check [web_app.py](web_app.py) lines 114-121

**Fix:** Backend not sending citations properly

---

#### Scenario B: "[Citations] Loaded" appears, but "[Citations] Attached handlers" shows 0 elements
**Problem:** Citation elements not found in DOM
**Check:**
- Right-click on a citation number → "Inspect Element"
- Verify HTML structure: `<sup class="citation" data-citation="1">1</sup>`
- Check if `formatAnswer()` function is converting `[1]` to `<sup>` tags

**Fix:** Citation conversion regex issue in [templates/index.html:793](templates/index.html#L793)

---

#### Scenario C: Handlers attached, but "[Citation Popup] Showing citation" doesn't appear on hover
**Problem:** Event handlers not firing
**Check:**
- Hover over citation → cursor should change to pointer
- Check CSS for `pointer-events: none` conflicts
- Verify event listeners in Elements tab → Event Listeners

**Fix:** CSS `pointer-events` blocking mouse events

---

#### Scenario D: "[Citation Popup] Showing citation" appears, but "[Citation Popup] Citation data" shows null/undefined
**Problem:** Citation number mismatch
**Check:**
- Compare `currentCitations` object keys with citation numbers in DOM
- Verify `data-citation` attribute matches citation number

**Fix:** Citation numbering mismatch between backend and frontend

---

#### Scenario E: All debug messages appear, but popup still not visible
**Problem:** CSS display issue
**Check:**
- Inspect `#citation-popup` element in DevTools
- Verify `display: block` when active
- Check `z-index: 10000` is high enough
- Look for parent elements with `overflow: hidden`

**Fix:** CSS conflict hiding popup

---

## Code Locations

### Frontend (templates/index.html)

| Line Range | Component | Purpose |
|------------|-----------|---------|
| 192-209 | `.citation` CSS | Citation number styling |
| 212-229 | `.citation-popup` CSS | Popup container styling |
| 520 | `currentCitations` | Global citation storage |
| 626-644 | Citation loading | Receive citations from API |
| 793 | Citation conversion | Convert `[1]` to `<sup>` tags |
| 820-826 | Handler attachment | Attach mouseenter/leave events |
| 828-843 | `showCitationPopup()` | Display popup on hover |
| 935-938 | `hideCitationPopup()` | Hide popup on mouse leave |
| 942-945 | Popup HTML container | DOM element for popup |

### Backend

| File | Line Range | Purpose |
|------|------------|---------|
| [tools/citation_formatter.py](tools/citation_formatter.py) | 58-84 | Create ISO citation objects |
| [tools/gemini_query_engine.py](tools/gemini_query_engine.py) | 346-358 | Include citations in API response |
| [web_app.py](web_app.py) | 114-121 | Send citations to frontend |

---

## Common Issues & Fixes

### Issue 1: Citations appear as `[1]` instead of superscript
**Cause:** Regex conversion not working
**Fix:** Check line 793 in index.html:
```javascript
formatted = formatted.replace(/\[(\d+)\]/g, '<sup class="citation" data-citation="$1">$1</sup>');
```

### Issue 2: Popup appears but is positioned off-screen
**Cause:** Positioning calculation issue
**Check:** Console logs for "Popup activated at position"
**Fix:** Verify popup bounds checking (lines 917-932)

### Issue 3: Multiple popups appear stacked
**Cause:** Event handlers attached multiple times
**Fix:** Add check before attaching handlers:
```javascript
el.removeEventListener('mouseenter', showCitationPopup);
el.removeEventListener('mouseleave', hideCitationPopup);
el.addEventListener('mouseenter', showCitationPopup);
el.addEventListener('mouseleave', hideCitationPopup);
```

### Issue 4: Popup doesn't hide when mouse leaves
**Cause:** `hideCitationPopup()` not being called
**Fix:** Verify `mouseleave` event is attached (line 823)

---

## Testing Checklist

- [ ] Test page ([test_citations.html](test_citations.html)) works correctly
- [ ] Browser console shows "[Citations] Loaded X citations"
- [ ] Browser console shows "[Citations] Attached handlers to X citation elements"
- [ ] Hovering over citation shows "[Citation Popup] Showing citation: X"
- [ ] Popup element has class "active" when hovering (inspect in DevTools)
- [ ] Popup element has `display: block` (check computed styles)
- [ ] Popup is positioned within viewport bounds
- [ ] Cursor changes to pointer when hovering over citation
- [ ] Popup disappears when mouse leaves citation

---

## Next Steps

1. **Run the test page** to verify basic functionality
2. **Check browser console** in main app while testing citations
3. **Report findings** using the scenarios above
4. **Share console output** if issue persists

Once we identify which scenario matches your situation, we can apply the specific fix needed.
