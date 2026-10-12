# Creative direction

**Idea.** A camera roll is a pile. Lacrydia is a place. (The app's own line, from `OVERVIEW.md` in the Lacrydia repo.)
The film is built as one physical journey: a single photograph in glass becomes a pile of photographs on black glass,
the pile settles into the Tree, and the Tree is the app. The people you share with appear at the very end, in the app's own
words: *Private by default. Shared with the people you choose.*

**What is shown is real.** Only features that exist in the product are shown: the Tree (branches *My Life / Travel / Nature /
Friends / Cars* are the app's own onboarding branches), private-by-default with sharing, stories and the feed. The two app
screens are unretouched screenshots (`docs/screens/tour/2.png`, `4.png`); the logo is the real mark rebuilt from its SVG polygons;
the wordmark is the brand's own artwork. No statistics, no invented screens, no claims beyond the app's own copy.

**Visual language.** Obsidian black, deep midnight-blue shadows, cool silver highlights, soft white light. Light is the main
character: every shot is a controlled studio set (key softbox, narrow strip rims, a travelling sweep strip, a cool fill, gradient
reflection flags). The darkest areas stay deep but not crushed; highlights roll off through a filmic curve; skin tones are
untouched. Glass is real glass (Cycles refraction, bevelled edges, acid-etched mark), not a blur filter.

**Motion language** (one system, `scripts/lib/motion.py`): every camera and light move is a clamped cubic spline that starts and
ends at rest; reveals use a small family of cubic-bezier curves (inout / out / in / soft). No bounce, no springs; overshoot appears
nowhere. Match cuts are carried by light: the sweep strip, a thin line leaving a photograph, nine slits sliding in (the brand's own
logo-reveal rule: ease-out, one after another).

**Typography.** Inter Display (the brand face, SIL OFL), few words, only where they add something:
"A camera roll is a pile." / "Lacrydia is a place." / "Private by default." / "Shared with the people you choose." /
LACRYDIA (the real wordmark artwork) / "Your images. Your world." (the brand's tagline).

**Sound.** Entirely synthesised for this film. A dark, slow ambient bed in D major colours (Dsus2 → Bm9 → Gmaj7 → Em9 → Dmaj9);
every important visual event has its own cue: sub swell and bowed-glass resonance on the macro, a soft tonal accent each time a
photograph wakes (pitch follows where the scanner is), a harmonic pulse for every connection line that draws, a tactile settle when the
Tree completes, a screen-wake sweep, nine ascending glass tones for the nine slits and a long tonal resolution on the mark.
Silence and space are used deliberately: the first second is nearly silent; there is no stock music, no impact boom.
