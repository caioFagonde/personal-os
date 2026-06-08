# Tranche 04 Visual Reference Brief

The target UX is a cinematic, console-like Personal OS shell inspired by:
- Steam Big Picture Mode
- floating profile/status selectors
- glassmorphic social/message overlays
- horizontal content carousels
- readable HUD/status surfaces
- fast keyboard/controller-friendly navigation

## Key visual goals

1. Command Center as cockpit
   - The root dashboard should feel like a central operating cockpit, not a CRUD dashboard.
   - Use large focused cards, status zones, launchable modules, and horizontal module rails.
   - Prioritize "what do I do now?" over "show every table."

2. Big Picture navigation
   - Use horizontal carousels for modules, recent actions, daily rituals, intelligence briefings, and active work.
   - Focused item should be larger and brighter.
   - Non-focused items should remain visible but subdued.
   - Keyboard navigation.
   - Non-focused items should remain visible but subdued.
   - Keyboard navigation should be obvious.

3. Floating cards
   - Replace flat white cards with dark translucent glass surfaces.
   - Use blur, thin borders, soft shadows, subtle gradients.
   - Cards must remain legible against backgrounds.

4. Clean typography
   - No giant titles that overflow.
   - Use consistent hierarchy:
     - small uppercase eyebrow
     - large but bounded title
     - readable subtitle
     - action row
   - No white-on-white or pale-on-white surfaces.

5. Sidebar
   - Sidebar should feel like a system rail.
   - It should support collapsed/focus mode.
   - Active item must be visually obvious.
   - The shell must not have horizontal scroll at normal desktop sizes.

6. Mobile
   - The same UX should compress to a mobile command deck.
   - Primary actions: Capture, Tasks, Sync, Study, Zettel, Pair Device, Notifications.
   - Avoid dense tables on mobile; prefer cards and bottom sheets.

7. Feedback
   - Every long action needs loading state.
   - Every empty state needs an explanation and next action.
   - Every config error needs a setup action.
   - No raw backend exceptions in UI.

8. Assets
   - Do not copy third-party game or film imagery.
   - Use generated SVG/gradient backgrounds, abstract aurora fields, blurred shapes, icon glyphs, and local illustrations.
