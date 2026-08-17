# Images Directory

Project Compass brand marks used by the Streamlit console.

- `compass_icon.png` — Compass rose (256px). Sidebar HUD, `st.logo`, page favicon.
- `compass_icon_64.png` — Compact rose for tight chrome.
- `compass_wordmark.png` — Rose + COMPASS lockup (transparent).
- `onr_logo.png` — Optional override sidebar logo (recommended: 300x100px).
- `onr_icon.png` — Optional override favicon (recommended: 32x32px).

App copies live in `app-onr-demo/resources/images/` so the Databricks app
package does not depend on the repo-root `resources/` tree.

## Default Behavior

If images are not found, the app falls back to an inline SVG rose and the
compass emoji as the page icon. The sidebar HUD still renders the word
**Compass** next to the icon.

## Image Guidelines

- Use PNG format for best compatibility
- Keep file sizes under 100KB
- Use transparent backgrounds where possible
- Navy (`#0b1f3a`) + amber (`#f59e0b`) so the mark holds on the blue sidebar
