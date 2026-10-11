# Phone model: reference, accuracy and status

Script: `scripts/phone.py` (procedural, fully editable). QC renders: `scripts/render_phone_qc.py` -> `renders/previews/qc_*/`.

## What is verified and what is not

| Item | Status | Source |
|---|---|---|
| The film's own simulator device is named "iPhone 18 Pro" | verified | `lacrydia-swiftui/Video/README.md` ("iPhone 18 Pro, iOS 27.2") |
| Real Lacrydia screen content, 1206 x 2622 px | verified | 5 real screenshots in `lacrydia-social/docs/screens/tour/` (the 1206 x 2622 size matches a current Pro-size iPhone display) |
| Exact industrial design of the iPhone 18 Pro (frame material, camera plateau, lens layout, colours, button set) | **NOT verified** | No reference photos, CAD or specs exist in the project and I could not obtain reliable ones in this environment. |
| Overall dimensions used (150.0 x 71.9 x 8.75 mm) | taken from the publicly documented iPhone 17 Pro, assumed close for a Pro-size successor | public spec of the prior generation, not confirmed for the 18 Pro |
| Layout used: aluminium-style unibody, full-width camera plateau, three rear lenses in a triangle at the left (back view), flash + LiDAR + mic at the right, glass panel on the lower back, action button + 2 volume buttons left, side button + camera control right, USB-C + speaker holes at the bottom, Dynamic Island on the front | design language of the current Pro generation (17 Pro), used as a restrained plausible baseline | not confirmed for the 18 Pro |

Rule applied: nothing about the 18 Pro is presented as fact. The model is "a current-generation Pro-style iPhone". When reference photos of the
intended device (or a licensed 3D model) are available, replace/adjust these constants at the top of `phone.py`: `W,H,T,R_OUT,BEVEL,PLATEAU_H,LENS_R`, the lens positions
in `build_phone`, and `FINISHES`.

Not modelled on purpose: the manufacturer logo and regulatory print on the back (trademark / not visible at film distance), antenna micro-lines, internal parts.

## Needs your decision
- Which finish is the real 18 Pro finish for the commercial? Presets in `FINISHES`: `silver`, `deep_blue`, `cosmic_orange` (+ it is trivial to add more). Default: `silver`.
- Is a licensed manufacturer 3D model or a set of reference photos available? That would raise accuracy beyond what a procedural model can guarantee.

## Modelling summary (v2)
- Frame: rounded-rectangle extrusion, 1.12 cm outer corner radius, 1.4 mm edge radius (10 segments, weighted normals so large flat faces stay flat).
- Front: black glass slightly proud of the frame, a 1.15 mm black bezel, the display plane (separate object, UV-mapped, rounded corners) = exchangeable screen content.
- Back: aluminium surface + glass panel on the lower back + full-width camera plateau (rounded top corners matching the body radius).
- Lenses (x3): lathe-profiled polished ring with chamfer and inner ledge, black gasket, domed transmissive cover glass, stepped lens barrel behind it (3 tiers), thin-film coated core.
- Flash: diffuser + polished ring. LiDAR: coated dark glass + ring. Mic pinhole.
- Buttons: action, volume up/down (left), side button (right), camera control (right, flush glossy sapphire-like pill). Bottom: USB-C slot + 5 + 5 speaker holes.

## Materials
- Aluminium: metallic, roughness 0.36 modulated by fine noise, two-scale micro bump (bead-blasted look).
- Glass: dielectric IOR 1.52, low roughness, clear-coat; lens covers transmissive.
- Display: black glossy glass with coat + emission from the screen image (so dark UI areas are real deep black).

Status/quality assessment: see `documentation/quality_report.md` (phone section).
