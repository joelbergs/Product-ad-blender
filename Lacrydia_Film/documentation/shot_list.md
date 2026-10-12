# Shot list and edit (24 fps, 44.5 s)

Single source of truth: `config/film.json` (shot starts/durations/fades) and `scripts/lib/choreo.py` (timing of every
animated event; the sound design reads the same tables, so picture and sound cannot drift apart).

| Shot | Film time | Module | Camera | What happens | Light |
|---|---|---|---|---|---|
| **A** Extreme macro | 0.0 - 5.0 | `shot_a` | 100 mm macro, f/2.8, 0.25 m, slides down the left edge of the glass panel | black -> a horizontal strip of light travels down the polished bevel; the brand mark, acid-etched into the glass, catches the light and is the first brand element | soft rim strips fade up very slowly; the sweep is the character |
| **B** Three-quarter orbit | 5.0 - 11.5 | `shot_b` | 85 -> 100 mm, ~1.5 m, 70 degree orbit (-48 to +22), el 5-9 | the photograph inside the glass wakes (a figure on a mountain: one memory) while the camera circles the panel and a reflection card sweeps across the glass | key softbox, two rim strips, top strip, cool fill, sweep strip |
| **C** Low hero | 11.5 - 15.5 | `shot_c` | 30 mm, camera 3-5 cm above the obsidian, looking up | the panel is monumental, rim-lit; two more photographs wake in the depth; focus travels from the first memory to the next | sweep strip outlines the silhouette |
| **D** Overhead: the pile | 15.5 - 22.0 | `shot_table` T 0-6.5 | 40 mm straight down, slow descent and 2.5 degree turn | a camera roll is a pile: photographs lie scattered on the obsidian; a soft line of light scans across and each print wakes as it reaches it | scanner strip + overhead softbox |
| **E** Extreme detail | 22.0 - 25.5 | `shot_table` T 6.5-10 | 100 mm macro, f/2, grazing, focus rack | the root photograph (tram in the forest) in extreme detail; a thin illuminated line leaves its edge | gradient flags only, rims off |
| **F** The Tree | 25.5 - 34.0 | `shot_table` T 10-18.5 | crane: from 0.3 m low to 1.4 m, 20 -> 71 degrees elevation, 62 -> 38 mm | photographs glide into place, connection lines draw on and pulse, labels appear (My Life, Travel, Nature, Friends, Cars: the app's own branch names): a place, not a pile | rim strips return, floor reflections of the whole structure |
| **G** The real app | 34.0 - 38.5 | `shot_g` | 90 mm, ~1.0 m, orbit -34 -> -3 degrees | a bezel-less glass device carries the genuine app screens (Tree, then sharing) | rims + reflection cards |
| **H** Brand | 38.5 - 44.5 | `shot_h` | 85 mm, settles into a locked-off frame at 3.7 s | the nine slits of the mark slide in one after another (the brand's own motion rule), the wordmark and the line come in below | rim strips + soft key |

Transitions are motivated by light: shots A, B, C, D, G dip through darkness (the picture is lit *on* and *off*, exposure
ramps in linear light); D -> E -> F are hard cuts inside one continuous physical space (the same photographs, the same table).
