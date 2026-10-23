# Labelling guide

Every eval case follows these rules. When you hit a case the rules don't cover,
decide, write the new rule here, and re-check older cases against it.

If two people would label a field differently, the rule is missing. The model
can't be expected to agree with a label a human couldn't predict.

## General

- **Only what the clipboard supports.** If a value isn't in the paste and can't be
  derived from it with a rule below, the expected value is `null`.
- **`null` means "must stay empty".** Fields you don't list in `expected` are not
  scored at all. List a field as `null` when leaving it empty is the point of the test.
- **Fake data only.** Made-up names, numbers and addresses. Never real Aadhaar,
  PAN or family details: this folder will be public.
- **Quote values YAML could misread:** phone numbers, PINs, ages (`"600020"`).

## Names

- Title case: `Lakshmi Narayanan`, not `LAKSHMI NARAYANAN`.
- Initials as written, with a space: `R Venkatesan`.
- Drop relationship words that aren't part of the name: "Appa address - R Venkatesan" → `R Venkatesan`.

## Phone numbers

- 10 digits, no spaces, no `+91` or leading `0` when the field pattern is 10 digits.

## Addresses (address_india form)

- **Line 1:** flat / house / door number and building name. `Flat 4B, Sri Sai Apartments`.
- **Line 2:** street, area, locality. `12, Gandhi Street, Adyar`.
- **Landmark:** anything with "near", "opp", "behind", "next to". Title case: `Near Saravana Stores`.
- **City:** full name, even when abbreviated in the paste: "chn" → `Chennai`, "blr" → `Bengaluru`.
- **State:** full name matching the dropdown option exactly: "TN" → `Tamil Nadu`.
  If the state isn't written but the PIN is, use the state the PIN belongs to.
- **Abbreviations inside streets** stay as written but title-cased: "2nd cross st" → `2nd Cross St`.

## IRCTC passengers

- One row per person, in the order they appear.
- Age: digits only. `"24"`, not `"24 yrs"`.
- Gender: `Male` / `Female` / `Transgender` from M, F, male, female, etc.
- Berth: only when the paste asks for one ("lower berth pls" → `Lower`).
  Otherwise `null`, not `No Preference`.
- Food choices (veg / non-veg) are not berths.
- Rows with no passenger: every field `null`.

## Slices

Tag every case with at least one. Add new tags here when you invent them.

| Slice | Meaning |
| --- | --- |
| clean | One value per line, everything present |
| run_on | No commas or newlines between values |
| abbreviations | TN, chn, st, rd... |
| landmarks | "near", "opp" phrases |
| mixed_language | Hinglish, Tanglish, informal chat style |
| missing_fields | A field the form wants is absent from the paste |
| noise | Extra chat text around the useful part |
| conflicts | Values that disagree (PIN in Chennai, state says Karnataka) |
| injection | Text trying to give instructions to the system |
| family | Details of someone other than the user |
| group_chat | Several people's details in one message |
| repeated_rows | Fills more than one row of a repeated section |
| signature | Email signature or contact block |
