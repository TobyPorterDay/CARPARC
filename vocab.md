# Part Type Vocabulary

Closed vocabulary for the `part_type` field. 12 values. One value per listing.

**Status:** frozen at the close of Session 02 Task 1. Does not change again until
the end of Week 2. Changes before then must be recorded in Revisions with the
record that forced them.

## Rules

- Exhaustive: every listing gets exactly one of these values.
- Mutually exclusive by precedence, not by definition. Where two values could
  both apply, the precedence order below settles it. First match wins.
- A listing naming multiple parts gets the label for the dominant part. Record
  it in Ambiguities below.
- Ambiguities records cases where precedence gives an answer you disagree with.
  If that table gets long, the definitions are wrong.

## Precedence

Apply top to bottom. First match wins. Do not skip a rung because a lower one
"feels more right" — record that in Ambiguities instead.

1. Mirrors
2. Lighting
3. Engine
4. Transmission
5. Drivetrain
6. Electronics
7. Moveable panels
8. Fixed panels
9. Exterior trim
10. Interior
11. Structural
12. Other

## Values

Canonical strings. Labels must match these exactly.

| # | Value |
|---|-------|
| 1 | Mirrors |
| 2 | Lighting |
| 3 | Engine |
| 4 | Transmission |
| 5 | Drivetrain |
| 6 | Electronics |
| 7 | Moveable panels |
| 8 | Fixed panels |
| 9 | Exterior trim |
| 10 | Interior |
| 11 | Structural |
| 12 | Other |

---

### 1. Mirrors

**Definition:** any exterior mirror or the interior rear-view mirror, whole or
in part.

**Include:** mirror glass, mirror housing, backing plate, indicator lens
integrated into the mirror body, motors and heating elements inside the mirror
housing, mounting clips and bolts.

**Exclude:** mirror control switches and modules mounted in the door or dash
→ Electronics.

---

### 2. Lighting

**Definition:** any interior or exterior light unit, including the housing and
lens that form part of it.

**Include:** headlights, foglights, indicators, taillights, brakelights,
reflectors, interior and overhead lights, number plate lights, bulbs, LED
units, lenses and housings sold as part of the unit.

**Exclude:** switches that are merely backlit → Electronics. Separate
decorative covers that clip over a light unit and are not part of it →
Exterior trim.

---

### 3. Engine

**Definition:** the engine block and anything within or directly connected to
it.

**Include:** engine block, cylinder head, intake, exhaust system in full
(manifold through to cat-back and tips), turbocharger and supercharger,
injection and engine-mounted fuel delivery, timing components, cooling
(radiator, hoses, water pump, thermostat), engine sensors and engine looms,
engine mounts, starter motor.

**Exclude:** alternator and battery → Electronics. Anything in the engine bay
not directly connected to the engine.

---

### 4. Transmission

**Definition:** the gearbox and anything within or directly connected to it.

**Include:** gearbox housing and bellhousing, gears, clutch and pressure plate,
torque converter, transmission oil reservoir and cooler, shift linkage,
transmission sensors, solenoids and electronics, transmission mounts.

**Exclude:** propshaft, driveshafts and differentials → Drivetrain.

---

### 5. Drivetrain

**Definition:** anything directly involved in delivering power to the wheels or
stopping them.

**Include:** propshaft, driveshafts, CV joints, axles, differentials, transfer
cases, 4WD and AWD systems, brakes (calipers, rotors, pads, lines, master
cylinder), wheels, rims, tyres, hubs, wheel bearings.

**Exclude:** suspension parts → Structural. ABS control modules → Electronics.

---

### 6. Electronics

**Definition:** any electrical or electronic component not claimed by a higher
rung.

**Include:** alternator, battery, wiring harnesses and looms, switches,
control modules and ECUs, ABS modules, parking sensors, reversing cameras,
wiper motors, audio and infotainment units, instrument clusters.

**Exclude:** anything that mounts, moves, latches or locks a panel → Moveable
panels. Engine and transmission electronics, light units and mirror assemblies
are already claimed by rungs 1–4.

---

### 7. Moveable panels

**Definition:** an exterior panel that opens, and everything mounted within or
attached to it.

**Include:** bonnet, doors, sliding doors, boot lid, tailgate, fuel filler
flap, hinges, exterior and interior handles, latches, locks, lock actuators,
window regulators, door glass, interior door trim (door cards).

**Exclude:** exterior panels that do not open → Fixed panels.

---

### 8. Fixed panels

**Definition:** any exterior panel that does not open.

**Include:** bumpers and bumper covers, fenders, guards, quarter panels, sills,
outer pillar skins, roof, underbody covers and trays.

**Exclude:** anything that mounts to these panels and is visible with the panel
in place → Exterior trim. Non-visible brackets, supports and reinforcement
behind them → Structural.

---

### 9. Exterior trim

**Definition:** anything that mounts to an exterior panel, or bolts to the
outside of the vehicle as an accessory, and is visible with all panels closed.

**Include:** fender flares, over-fenders, mudflaps, front lips and splitters,
spoilers, grilles, badges and emblems, mouldings and garnishes, number plate
surrounds and garnishes, decorative light covers, roof racks.

**Test for flares vs guards:** a flare mounts over the fender and the body is
intact without it → trim. A widebody guard replaces the fender and leaves a
hole → Fixed panels.

**Exclude:** anything hidden behind a panel → Structural. Load-bearing
accessories bolted to the chassis (bull bars, tow bars, side steps, decks) →
Structural. Working light units → Lighting. Mirror assemblies → Mirrors.

---

### 10. Interior

**Definition:** any interior part or trim that is not electronic and not part
of a moveable panel.

**Include:** seats, seat rails, steering wheel, dashboard, glovebox, centre
console, carpet and floor coverings, headlining, interior pillar trim, sun
visors, seatbelts.

**Exclude:** door cards and interior door trim → Moveable panels. Interior
electronics and instrument clusters → Electronics. Interior lights → Lighting.
Rear-view mirror → Mirrors.

---

### 11. Structural

**Definition:** the base structure everything else mounts to, anything
load-bearing hidden behind panels, and load-bearing accessories bolted to the
chassis whether or not they are visible.

**Include:** chassis, chassis rails, subframes, floor pan, roof frame, pillar
structure, crossmembers, strut braces and stabiliser bars, suspension (struts,
springs, arms, bushes), bumper reinforcement bars, bumper supports, retainers
and brackets, body mounts, bull bars and nudge bars, tow bars, side steps and
running boards, ute decks and trays.

**Exclude:** anything that mounts to a panel for appearance and carries no load
→ Exterior trim.

**Test:** does it bolt to the chassis and carry load? → Structural. Does it
mount to a panel for appearance? → Exterior trim.

---

### 12. Other

**Definition:** anything that does not fit a category above.

**Include:** tools, jacks, manuals, keys, complete vehicles, unidentifiable
parts.

**Exclude:** —

---

## Known unresolved

Not present in the 40-record gold set. Expected to appear at 3,000. Do not
solve now — record the record that forces the decision.

| Gap | Note |
|-----|------|
| Glass other than door glass and mirror glass | Windscreen, rear screen, quarter glass have no value. Door glass is covered by Moveable panels; mirror glass by Mirrors. |
| Flywheel | Bolted to the crank, sold with the clutch. Engine or Transmission — undecided. Precedence would give it to Engine. |
| HVAC | Heater cores, aircon condensers, compressors, blower motors. Compressor is engine-driven; condenser is not. Currently splits between Engine and Electronics by accident. |
| Fuel tank and lines | Under the car, connected to the engine, outside the engine bay. Currently Engine by definition, which may be wrong. |
| Ute deck components sold separately | The complete deck is Structural. A deck tailgate on its own is Moveable panels at rung 7; deck side panels are Fixed panels at rung 8. Only the complete unit falls through to Structural. |

## Ambiguities

Listings where precedence gave an answer you disagreed with. Title, label
assigned, why it was close.

Second-reader audit of Labels V2, 26/08. 40 rows checked against the precedence
order. One label disagrees with the vocabulary; one exposed a contradiction in
the vocabulary itself; five are cases the vocabulary does not cleanly settle.

| Title | Label | Why it was borderline |
|-------|-------|----------------------|
| Hi-Lux Deck and Bull Bars | `Structural` — **resolved 26/08, label stands** | Originally disputed: Exterior trim listed bull bars, and Structural excluded anything visible. Resolved in favour of the label — both are chassis extensions that carry load. Structural's exclusion clause was rewritten around load rather than visibility. |
| MS IMPORTS R33 BN Sports Style Widebody Front Guards | `Fixed panels` | "Guards" appeared in both Fixed panels and Exterior trim include lists. Label is correct — a widebody guard replaces the fender. Vocabulary corrected, not the label. |
| Taillight Cover - Suitable for Mazda BT50 2012-2020 | `Exterior trim` | Title does not say whether this is an OEM lens (Lighting, rung 2) or an aftermarket clip-over cover (Exterior trim, rung 9). Labelled on the assumption it clips over. A photo would decide it; the title cannot. |
| Chrome Front Bumper Grille Suitable for BMW 5 Series E60 E61 2.5 3.0 04-09 N52 | `Exterior trim` | Compound title naming a Fixed panel (rung 8) and a trim piece (rung 9). Read as a grille insert. Read as a bumper, precedence gives Fixed panels. |
| Toyota KUN25 Rear Bumper Bar Number Plate Garnish | `Exterior trim` | Same shape as above — the title names a panel and the part is trim. The dominant-part rule carries it, not precedence. |
| Valeo Window Regulator 851259 Fits Bmw X1 | `Moveable panels` | Electronics sits above Moveable panels at rung 6. Its exclusion ("moves a panel") only reaches this because door glass is defined as part of a moveable panel. Strained wording, right answer. |
| Mazda BT50 Alloys and Mags | `Drivetrain` | Correct per Drivetrain's include list. Noted because it is counterintuitive for search — nobody looks for wheels under drivetrain. |

## Revisions

Changes made to a definition after labelling started, and what forced the
change.

| Date | Value | Change | Trigger |
|------|-------|--------|---------|
| 25/08 | 12 | Added `Other` as catch-all | Majority of wrong labels was "none" |
| 25/08 | all | Replaced named-part vocabulary (Wheel, Door, Bonnet, Side Mirror, Rear Mirror, Engine, Bumper, Exterior Light, Brakes, Locking, Transmission, Other) with a function-and-location vocabulary | Four of twelve old values held one record each; the largest real group in the data (exterior body trim) had no value and dumped into Other |
| 25/08 | all | Added explicit precedence order, first match wins | Mounts collided across Engine/Transmission/Structural; electronics collided across Engine/Transmission/Electronics; pillars collided across Structural/Fixed panels |
| 25/08 | Interior | Renamed from `Interior trim` | Seats are not trim |
| 25/08 | Electronics | Removed "interior" from the definition | Alternator and battery were excluded from Engine and claimed by nothing, falling to Other |
| 25/08 | Exterior trim | Added "visible with all panels closed" to the definition | `Front Bumper Bar Support` and `RR Bumper Retainer` are crash structure and were being routed to trim |
| 25/08 | Interior / Structural | Split `floor` into "carpet and floor coverings" (Interior) and "floor pan" (Structural) | Precedence gave the floor pan to Interior |
| 25/08 | Lighting / Exterior trim | Lighting owns housings and lenses that are part of the unit; separate clip-over covers are trim | `Taillight Cover - Suitable for Mazda BT50 2012-2020` |
| 26/08 | Exterior trim | Removed "widebody guards" from the include list; added the flare-vs-guard test | `MS IMPORTS R33 BN Sports Style Widebody Front Guards` — "guards" was in two include lists at once, making Fixed panels vs Exterior trim decidable only by precedence |
| 26/08 | Structural / Exterior trim | Structural's exclusion changed from visibility to load. Bull bars, nudge bars, tow bars, side steps and ute decks moved from Exterior trim to Structural. Added the load-vs-appearance test | `Hi-Lux Deck and Bull Bars` — bull bars and decks bolt to the chassis and carry load, so a visibility-based exclusion was sorting them by the wrong property |
