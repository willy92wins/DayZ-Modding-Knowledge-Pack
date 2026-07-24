# DayZ UI Development

Source skill: `C:\Users\<you>\.agents\skills\dayz-ui-development\SKILL.md:44-330`
Extraction date: 2026-05-14
Evidence level: skill-sourced summary. Verify exact widget/event signatures against engine source before implementation and record exact facts in project `verified-apis.md`.

## Layout Rules

- Every widget, including leaf widgets, needs an explicit child block.
- Frame/panel widgets are structure only; visible backgrounds need an image-style widget setup.
- Every widget should set exact-position and exact-size flags consistently.
- Brace counts must balance before in-game testing.
- Widget names must stay unique within the layout.
- Externalize visible text through `stringtable.xml` keys for translatability.

## Script Rules

- Null-check game/workspace access around widget creation and teardown.
- Null-check every widget lookup and cast.
- Vanilla handlers need explicit handler setup; Dabs MVC handles part of that lifecycle.
- Avoid creating views from RPC/early-init contexts where workspace may be unavailable; pre-create at a safe lifecycle point and show/hide later.
- Lock input on open and release on close and destructor.

## Dabs MVC Rules

- Do not combine command binding with a manual click override that calls the parent click path; that can double-fire.
- Property change notification should target the property that changed. Empty/all-binding refresh is expensive.
- Watch for circular references when collection items point back to controllers.
- Production Dabs uses widget-keyed maps; do not ban them based on stale assumptions.

## Event/Widget Notes

- Event signatures must be verified from the local engine source before code is written.
- Known high-risk asymmetry: mouse enter/leave callbacks do not necessarily have matching parameter shapes.
- Button children can be awkward to find by name; store child refs explicitly when needed.
- For visible scripted color backgrounds, ensure an image source exists before setting color.

## Color And Input

- DayZ may darken UI colors by default; project patterns may normalize widget/text light values at startup.
- Very low alpha values can be effectively invisible.
- Layout color floats and script ARGB integer values use different ranges.
- ESC/back handling may require intercepting input in mission/menu code when focus is locked.

## Localization

- `stringtable.xml` belongs at addon root.
- Key IDs do not include `#`; references do.
- Keep a consistent project prefix for grepability.
- Raw text in `.layout` works visually but fails translation workflows.

## Common Failure Patterns

- Missing child block crashes/hangs layout parser.
- Widget not clickable because pointer ignore flag is on the widget or an ancestor.
- Click handler not firing because vanilla handler setup is missing.
- Text overlaps after dynamic visibility changes; recalculate layout or use proper spacers.
- Scroll content does not scroll because the direct child is not a spacer.
- Colors are unexpectedly dark or transparent due to LV/alpha behavior.

## Related

- [`AI/20_Knowledge/dayz-enforce-script-reference.md`](dayz-enforce-script-reference.md)
- Project exact widget APIs: `AI/10_Projects/<PROJECT>/verified-apis.md`
- [[dayz-enforce-script-reference]] — APIs de widgets, RPC y lifecycle que el código de UI invoca.
- [[dayz-mod-implementation-checklists]] — checklist client/server antes de cablear cada feature de UI.
- [[skill-extraction-index]] — de qué skill salió esta nota y cuál es su par durable.
- [[20_Knowledge/lessons-learned|lessons-learned]] — gotchas transversales (Edit truncation, OneDrive) que muerden al escribir layouts.
