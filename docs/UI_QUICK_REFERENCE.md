# UI Quick Reference Guide

## Responsive Breakpoints

```css
/* Mobile Portrait */
@media (max-width: 576px) { }

/* Mobile Landscape / Small Tablets */
@media (min-width: 577px) and (max-width: 768px) { }

/* Tablets */
@media (min-width: 769px) and (max-width: 991px) { }

/* Desktop */
@media (min-width: 992px) { }

/* Large Desktop */
@media (min-width: 1400px) { }

/* Touch Devices */
@media (hover: none) and (pointer: coarse) { }
```

## Essential CSS Snippets

### Touch-Friendly Button
```css
.btn {
  min-height: 44px;
  min-width: 44px;
  padding: 12px 16px;
  font-size: 16px; /* Prevents iOS zoom */
}
```

### Responsive Card
```css
.card {
  -webkit-border-radius: 10px;
  -moz-border-radius: 10px;
  border-radius: 10px;
  padding: 1rem;
  margin-bottom: 1rem;
  -webkit-box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  -moz-box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

@media (max-width: 576px) {
  .card {
    padding: 0.75rem;
    margin-bottom: 0.75rem;
  }
}
```

### Scrollable Table
```css
.table-responsive {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  width: 100%;
}

.table {
  width: 100%;
  font-size: 0.9rem;
}

@media (max-width: 576px) {
  .table {
    font-size: 0.85rem;
    white-space: nowrap;
  }
}
```

### Smooth Transition
```css
.element {
  -webkit-transition: all 0.3s ease;
  -moz-transition: all 0.3s ease;
  -o-transition: all 0.3s ease;
  transition: all 0.3s ease;
}
```

## HTML Template Basics

### Essential Meta Tags
```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="X-UA-Compatible" content="IE=edge">
  <title>Page Title</title>
</head>
```

### Bootstrap Integration
```html
<!-- CSS -->
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">

<!-- JavaScript -->
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
```

### Responsive Container
```html
<div class="container">
  <div class="row">
    <div class="col-12 col-md-6 col-lg-4">
      <!-- Content -->
    </div>
  </div>
</div>
```

## Common Patterns

### Mobile-First Form
```html
<form>
  <div class="mb-3">
    <label for="input1" class="form-label">Label</label>
    <input type="text" class="form-control" id="input1" 
           style="font-size: 16px;" required>
  </div>
  <button type="submit" class="btn btn-primary w-100 w-md-auto">
    Submit
  </button>
</form>
```

### Responsive Navigation
```html
<nav class="navbar navbar-expand-lg">
  <div class="container-fluid">
    <a class="navbar-brand" href="#">Brand</a>
    <button class="navbar-toggler" type="button" 
            data-bs-toggle="collapse" data-bs-target="#nav">
      <span class="navbar-toggler-icon"></span>
    </button>
    <div class="collapse navbar-collapse" id="nav">
      <!-- Nav items -->
    </div>
  </div>
</nav>
```

### Responsive Card Grid
```html
<div class="row">
  <div class="col-12 col-sm-6 col-lg-4 mb-3">
    <div class="card">
      <div class="card-body">
        <!-- Content -->
      </div>
    </div>
  </div>
</div>
```

## JavaScript Helpers

### Detect Mobile
```javascript
function isMobile() {
  return window.innerWidth <= 576;
}
```

### Detect Touch Device
```javascript
function isTouchDevice() {
  return (('ontouchstart' in window) ||
     (navigator.maxTouchPoints > 0) ||
     (navigator.msMaxTouchPoints > 0));
}
```

### Responsive Event Handler
```javascript
window.addEventListener('resize', function() {
  if (window.innerWidth <= 576) {
    // Mobile layout
  } else {
    // Desktop layout
  }
});
```

## Testing Checklist

### Quick Test
- [ ] Open in Chrome DevTools mobile view
- [ ] Test on iPhone (Safari)
- [ ] Test on Android (Chrome)
- [ ] Test all breakpoints (320px, 576px, 768px, 1024px)
- [ ] Test landscape orientation
- [ ] Test touch interactions
- [ ] Test keyboard navigation

### Viewport Sizes
```
iPhone SE:        320px × 568px
iPhone 12:        390px × 844px
iPhone 12 Pro Max: 428px × 926px
iPad:             768px × 1024px
iPad Pro:         1024px × 1366px
Desktop:          1920px × 1080px
```

## Common Issues & Fixes

### Issue: Text too small on mobile
```css
/* Fix: Use relative units and minimum sizes */
body {
  font-size: 16px; /* Base size */
}

@media (max-width: 576px) {
  body {
    font-size: 14px;
  }
}
```

### Issue: Inputs zoom on iOS
```css
/* Fix: Use 16px font size */
input, textarea, select {
  font-size: 16px;
}
```

### Issue: Table overflow
```css
/* Fix: Add horizontal scroll */
.table-wrapper {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}
```

### Issue: Buttons too small for touch
```css
/* Fix: Minimum touch target size */
.btn {
  min-height: 44px;
  min-width: 44px;
  padding: 12px 16px;
}
```

## Browser-Specific Fixes

### Safari-specific
```css
/* Smooth scrolling on iOS */
.scrollable {
  -webkit-overflow-scrolling: touch;
}

/* Font smoothing */
body {
  -webkit-font-smoothing: antialiased;
}
```

### Firefox-specific
```css
/* Font smoothing */
body {
  -moz-osx-font-smoothing: grayscale;
}
```

## Performance Tips

1. **Use transform for animations** (GPU accelerated)
```css
.element {
  transform: translateX(10px);
  /* Instead of: left: 10px; */
}
```

2. **Minimize reflows**
```javascript
// Bad: Multiple reflows
element.style.width = '100px';
element.style.height = '100px';

// Good: Single reflow
element.style.cssText = 'width: 100px; height: 100px;';
```

3. **Debounce resize events**
```javascript
let resizeTimer;
window.addEventListener('resize', function() {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(function() {
    // Resize logic here
  }, 250);
});
```

## Color Contrast

### WCAG AA Compliance
- Normal text: 4.5:1 contrast ratio
- Large text: 3:1 contrast ratio
- Interactive elements: 3:1 contrast ratio

### Check Tools
- Chrome DevTools (Lighthouse)
- [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/)

## Accessibility Quick Tips

1. **Always include alt text**
```html
<img src="image.jpg" alt="Descriptive text">
```

2. **Use semantic HTML**
```html
<header>, <nav>, <main>, <article>, <aside>, <footer>
```

3. **Keyboard accessible**
```html
<button onclick="doSomething()">Click Me</button>
<!-- Don't use: <div onclick="doSomething()">Click Me</div> -->
```

4. **Focus indicators**
```css
button:focus {
  outline: 2px solid #00d4ff;
  outline-offset: 2px;
}
```

## Resources

- Bootstrap Docs: https://getbootstrap.com/docs/5.3/
- MDN Web Docs: https://developer.mozilla.org/
- Can I Use: https://caniuse.com/
- WCAG Guidelines: https://www.w3.org/WAI/WCAG21/quickref/

## Quick Commands

### Test in DevTools
```
Ctrl/Cmd + Shift + M  - Toggle device toolbar
Ctrl/Cmd + Shift + C  - Inspect element
F12                   - Open DevTools
```

### Common Screen Sizes
```
Mobile:  320-576px
Tablet:  577-991px
Desktop: 992px+
```

---

For complete documentation, see:
- [Responsive Design Guide](RESPONSIVE_DESIGN.md)
- [Browser Compatibility](BROWSER_COMPATIBILITY.md)
