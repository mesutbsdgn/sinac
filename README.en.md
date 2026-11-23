<div align="center">

<img src="assets/sinac-logo.svg" width="120" alt="Sınaç logo">

# Sınaç

### Tests your study notes: are they correct, do they teach, are they fit to publish?

![License](https://img.shields.io/badge/license-usage%20rights-lightgrey) ![Format](https://img.shields.io/badge/format-Claude%20skill-8A63D2) ![Model](https://img.shields.io/badge/model-independent-brightgreen) ![Language](https://img.shields.io/badge/language-T%C3%BCrk%C3%A7e%20%2B%20English-e30a17) ![Tests](https://img.shields.io/badge/tests-261%20tests%20%2B%20211%20counterexamples-brightgreen) ![test](https://github.com/mesutbsdgn/sinac/actions/workflows/test.yml/badge.svg)

</div>

Türkçe: [README.md](README.md)

The name comes from the Turkish verb *sınamak* ("to test"), formed the same way as its sibling skill Durulaç. It tests the
document, and it also covers the most important dimension of its own scale: the student testing themselves. Sınaç is a
Claude skill that audits lecture notes, topic explanations, guides and student PDFs against an evidence-based scale.

It detects the document's **academic field** and its **visual or verbal format** on its own: a medical note is not judged
by a language-learning scale, and a visual anatomy atlas is not judged by a plain-text scale. Every finding comes with a
**line number** and a rule ID, and the verdict has three states.

**Language note:** the documents may be in Turkish or English, and field detection and the patient-safety rules work in
both. The tool's own messages (warnings, suggestions, checklists) are in Turkish.

## Contents

- [Verdict](#verdict)
- [An example](#an-example)
- [Scale](#scale)
- [Three layers](#three-layers)
- [Health checks](#health-checks)
- [32 fields](#32-fields)
- [Examples from other fields](#examples-from-other-fields)
- [Field detection and two languages](#field-detection-and-two-languages)
- [Usage](#usage)
- [Installation](#installation)
- [How it was tested](#how-it-was-tested)
- [Evidence](#evidence)
- [Sibling skill: Durulaç](#sibling-skill-durulaç)
- [Limits](#limits)
- [Version history](#version-history)
- [License](#license)

## Verdict

Every audit returns one of three results:

| Verdict | Meaning | Exit code |
|---|---|---|
| ⛔ **Blocked from publishing** | A defect that harms patient safety or breaks the document was found (BLOCKER/ERROR below) | 1 |
| ◐ **Audit incomplete** | No blocker, but content accuracy (`denetim:`) or the target (`hedef:`) was not verified by hand | 3 |
| ✓ **Fit within the stated scope** | No blocker, manual fields filled in. This does not mean the content is correct | 0 |

Every finding has one of three levels (the tool prints them as ENGEL, HATA and UYARI):

| Level | Meaning | Affects the verdict |
|---|---|---|
| **ENGEL** (blocker) | Patient safety | Yes, blocks publishing |
| **HATA** (error) | A format defect that breaks the document | Yes, blocks publishing |
| **UYARI** (warning) | Fix list | No, given as a list |

## An example

Input, `paracetamol-note.md` (an English note; the dose arithmetic is wrong and the note mentions a "5.0 mg" dose as a
what-not-to-write example):

```markdown
---
hedef: Year 3 student calculates paediatric paracetamol dose
denetim:
---

# Paracetamol: dosing in children

## 1. Dose

Oral paracetamol is given at 15 mg/kg every 6 hours.

Worked example: for a 20 kg child, 20 kg × 15 mg/kg = 3000 mg per dose.

The adult tablet is 1,000 mg; never write 5.0 mg for a child's dose.

## 2. Self-test

1. What single dose does a 12 kg child receive?
```

Command (exit code 1):

```bash
python3 scripts/ogretim_denetim.py paracetamol-note.md --yil 2026
```

Output (this is real output; only the long manual checklist is shortened, as marked):

```text
⛔ paracetamol-note.md: YAYINA ENGEL VAR · 10/12 (6/8 boyut ölçüldü) · PDF ölçülmedi
  Alan: Tıp · tespit, destek orta; ipucu: dose, mg/kg · biçim: sozel · belge dili: en · grup: saglik
  (alan yanlışsa frontmatter'a `alan: …` yaz ya da --alan ver)
  | Boyut | Puan |
  |---|---|
  | Doğruluk | 0 |
  | Hedefle uyum | 2 |
  | Seviye | 2 |
  | Ezber ve kavrama | 2 |
  | Okunaklılık | ölçülmedi |
  | Sıra ve akış | 2 |
  | Kendini sınama | 2 |
  | Verimlilik | ölçülmedi |
  ⛔ ENGEL · satır 12 · Doğruluk: Doz hesabı tutmuyor («20 kg × 15 mg/kg = 3000 mg» → doğrusu 300 mg) → Hesabı yeniden yap; sonuç nottaki sayıyla aynı olmalı  [doz_aritmetigi]
  ⚠ UYARI · satır 10 · Doğruluk: Kiloya göre doz zaman birimi belirsiz (15 mg/kg) → 'mg/kg/gün' mü 'mg/kg/doz' mu yaz; sıklığı ve en yüksek dozu ekle  [doz_kg_belirsiz]
  ⚠ UYARI · satır 12 · Doğruluk: Kiloya göre doz zaman birimi belirsiz (15 mg/kg) → 'mg/kg/gün' mü 'mg/kg/doz' mu yaz; sıklığı ve en yüksek dozu ekle  [doz_kg_belirsiz]
  ⚠ UYARI · satır 14 · Doğruluk: Yanlış doz yazımı öğretici örnek olarak işaretli (5.0 mg) → Doğrusunun hemen yanında olduğundan emin ol  [tip_doz_yazimi]
  ☐ elle bekleyen: Doğruluk (frontmatter denetim: / hedef:)
  ℹ Betik doz YAZIMINI denetler, dozun klinik doğruluğunu denetlemez: güncel kaynakla karşılaştır
  … (health manual checklist and teaching ☐ items; shortened here, printed in full in the real output)
```

How to read it (the messages are in Turkish):

- Line 12: the dose calculation does not hold. 20 kg × 15 mg/kg is 300 mg, not 3000 mg. This is a BLOCKER, so the note
  cannot be published.
- Line 14: "5.0 mg" is a trailing-zero dose, but the sentence says "never write", so it is treated as a teaching example of a
  wrong form. That is a warning ("make sure the correct form is right next to it"), not a blocker.
- "1,000 mg" is correctly read as a thousands separator in an English sentence and is not flagged. In a Turkish
  sentence the comma would be a decimal mark.
- Lines 10 and 12: "15 mg/kg" does not say per day or per dose (the tool asks for the interval and a maximum dose).

## Scale

8 dimensions, each scored 0 (error), 1 (warning) or 2 (clean). A dimension that cannot be measured (efficiency without a
PDF, fit to target without `hedef:`) is not scored; the output says so, for example "11/12 (6/8 dimensions measured)".

| Dimension | Example automatic checks |
|---|---|
| Accuracy | dose writing and dose arithmetic, patient identity, national ID number, foreign-alphabet mix-ups, TODO, repealed law, unsourced authority |
| Fit to target | manual (frontmatter `hedef:`) |
| Level | undefined abbreviations, density of grammar terms |
| Memorisation and comprehension | long sentences, foreign text without pronunciation, century notation, number-unit spacing |
| Legibility | font size range in a PDF, blank pages, images without alt text, map elements |
| Order and flow | heading numbers, page references, worked examples |
| Self-testing | a closed-book test section, question-answer coverage |
| Efficiency | page cap, half-empty page ratio |

When a PDF is supplied, font size and page layout are measured, and the PDF text is also scanned for patient identity
and drug safety (a finding that is not in the Markdown is marked "in the PDF"; the other checks run on the Markdown).

## Three layers

| Layer | What it does |
|---|---|
| 1. Common core (every field) | Structure and legibility checks, **patient identity** (name, record number, full date of birth) and **numbers that pass the Turkish national ID checksum** (BLOCKER when labelled or in a person context, warning otherwise) |
| 2. Risk scan (field-independent) | If drugs or doses appear in the text, the health safety checks run even when the document is a history note |
| 3. Field profile | The checks of each of the 32 fields; in mixed documents, the field of each section is added too |

## Health checks

Checks that stop publishing:

| Check | Level | Example |
|---|---|---|
| Dose writing | BLOCKER | "5.0 mg", ".5 mg", "5,0 mg" in a Turkish sentence |
| Dose calculation that does not hold | BLOCKER | "20 kg × 5 mg/kg = 1000 mg" |
| Unit conversion that does not hold | BLOCKER | "Glucose 90 mg/dL = 50 mmol/L" |
| Patient name, record number, full date of birth | BLOCKER; warning only without a case context (a biography) | A lower-case name with an explicit label and an ISO-format date of birth are both caught |

Dose writing is also searched in bold text, code, table cells (even when the unit is in the column header), HTML, common
LaTeX forms (`5{,}0`, `\SI{}{}`, `\mathrm{mg}`) and full-width digits. "5.0 mg/kg", "5.0-10 mg" and "40.0 MG" are caught.
In an English sentence "1,000 mg" is a thousands separator. A level measurement such as "PSA 4.0 ng/mL", and "25.0 mL"
in a science worksheet with no drug name, are not counted.

Checks that give warnings:

| Check | Level | Example |
|---|---|---|
| Error-prone abbreviations from ISMP | warning | U, IU, cc, q.d., μg, SC, TIW, D/C, OD/OS/OU, ml, "1:1000" |
| Run-together dose | warning | "10mg", "propranolol20 mg" |
| mg/kg without a time unit | warning | "15 mg/kg" |
| No maximum dose for a child | warning | Weight-based dose given, no ceiling |
| "As needed" instruction without a dose range | warning | — |
| Lettered pregnancy category | warning | — |
| Reference range without a source | warning | — |
| Guideline whose currency needs checking, DSM-IV, misspelled species name | warning | — |

For medicine and the seven health sub-fields an 11-item shared health checklist is added (not for psychology).

## 32 fields

| Group | Fields |
|---|---|
| Health (most detailed) | medicine; dentistry, nursing and midwifery, pharmacy, veterinary, nutrition, physiotherapy, emergency medicine; psychology |
| Numerical and science | mathematics, statistics, science, physics, chemistry, biology, earth sciences, agriculture, engineering, computing, architecture |
| Social and humanities | law, economics and business, history, geography, social studies, theology, literature, philosophy, arts and music, education |
| Language and general | foreign language (fr, en, de, es, it), general |

The field profiles are in `references/ogretim-alanlari.json` (32 profiles).

## Examples from other fields

| Field | Check |
|---|---|
| Science | SI unit writing; a safety note in a lab worksheet |
| Statistics | "p = 0,000" writing |
| Computing | Use of Python 2 |
| Law | A repealed statute: not counted when applied to a past event (Turkish Law No. 6101, art. 1); a court decision without a citation |
| Theology | A hadith without a source |
| Literature, history, philosophy, law, theology, arts | A quotation without a source |
| Geography | A map without a legend, scale, north arrow or source |

Several of the field checks are specific to Turkish law and Turkish-language material and are kept short here; see the
Turkish README and `references/ogretim.md` for details.

## Field detection and two languages

Since v2.1.0 field detection is **language-aware**: a document may be Turkish, English or mixed.

- **Unit language guess:** the body is split into units (a paragraph, a list item, a table row). The language of each unit
  (`tr`, `en`, `fr`) is guessed from Turkish-specific letters and stop words; when the signal is too weak, the unit falls
  back to the document's language. The output carries `belge_dili` (document language) and `grup` (field group).
- **Language-aware matching:** Turkish word and phrase lists are matched only in Turkish units (with suffix chains),
  English lists only in English units (whole word and plural). French units do not count toward the field score; code
  blocks count only toward computing.
- **Field lexicon:** per field, Turkish and English words, phrases (weight 2) and abbreviations. In total: 2355 Turkish
  words (718 before, all of them a Turkish and English mix), 1499 Turkish phrases, 2680 English words, 1536 English
  phrases and 374 abbreviations.
- **Field groups:** health, numerical-science, social-humanities, language-general. If the best field is below the
  threshold but the health group passes it, the field becomes `tip` (medicine), so the health checks and the manual
  checklist apply.
- **Number format depends on language:** in an English unit "1,000 mg" is a thousands separator (no dose-writing blocker);
  in Turkish the comma is a decimal mark.
- **Other new rules:** cholesterol (÷ 38.67) and triglyceride (÷ 88.5) conversion; dose arithmetic in table rows and in
  prose (weight × mg/kg = dose); lab conversion in prose. A teaching example of a wrong form ("Do not write 5.0 mg") is a
  warning, not a blocker. A full name next to an age pattern ("a 58-year-old woman, Jane Doe") is a blocker in a case
  context and a warning otherwise.

How the lexicon was built: DeepSeek V4.1 Flash wrote the Turkish lists; Gemini 4 Neon wrote the English lists and the
core words of each field. They then criticised each other's lists (Gemini reviewed the Turkish list, DeepSeek the English
one; 416 + 283 items were removed). A local filter followed: general academic words, items found in three or more fields,
and abbreviations that occur as ordinary words or clash with a unit were dropped, and general clinical words that do not
tell health sub-fields apart were removed from the health sub-fields. Published field word lists (MAWL, CSAVL, EAWL;
nursing, pharmacy, law and engineering lists) were not copied, for copyright and access reasons; only their principles
(frequency plus dispersion, excluding general words) were used.

### Measurement

Measured with `scripts/altin_olc.py`; the expectations were written before the script was run. "Group correct" means the
group is right and the field is not "general".

| Set | Written by | Docs | Version | Field correct | Group correct | Verdict correct | Missed BLOCKER | False BLOCKER |
|---|---|---|---|---|---|---|---|---|
| Development (`tests/altin`) | Sonnet 5.5 | 40 (20 tr, 20 en) | v2.0.1 | 14 (tr 9, en 5) | 22 (tr 14, en 8) | 38 | 2 | 1 |
| | | | v2.1.0 | 28 (tr 15, en 13) | 38 (tr 19, en 19) | 40 | 0 | 0 |
| Unseen 1 (`tests/gorulmemis-gemini`) | Gemini 4 Neon | 20 (10/10) | v2.0.1 | 15 (tr 10, en 5) | — | 17 | — | — |
| | | | v2.1.0 first pass (before the rule fix) | 17 | 20 | 18 | 3 | 2 (1 doc) |
| | | | v2.1.0 final | 17 | 20 | 20 | 0 | 0 |
| Unseen 2 (`tests/gorulmemis-deepseek`) | DeepSeek V4.1 Flash | 15 (7 tr, 8 en) | v2.0.1 | 4 (6 of them "general") | — | 10 | — | — |
| | | | v2.1.0 first pass | 8 | 14 | 11 | 4 | 0 |
| | | | v2.1.0 final | 8 | 14 | 15 | 0 | 0 |

**Honesty notes:**

- The development set was used during development; it is not the real generalisation measure.
- The two unseen sets were used **on the first pass** to find rule gaps, and the gaps were fixed afterwards. So the
  "final" rows are no longer unseen; they are regression sets. The real generalisation measure is the **"first pass"**
  rows: verdict 18/20 on the Neon set and 11/15 on the DeepSeek set, with 3 and 4 missed blockers respectively.
- Most of the remaining field errors are confusions between health sub-fields (nursing, pharmacy and medicine are mixed
  up; since all of them get the same health checks, this does not matter for safety) and mixed documents (health plus
  statistics, physics plus chemistry).
- The DeepSeek set has 15 documents (its fourth batch was cut off at the output limit). DeepSeek wrote "denetime:" in the
  frontmatter of every document; it was corrected to "denetim:" before measuring.
- All three sets were written by models; there is still no gold set labelled by teachers or experts.

**French corpus** (368 real lecture notes, French with Turkish explanations): documents recognised as `dil` (language)
went from 340 to 357, and "general" from 19 to 5. No document gained a blocker, and the single false blocker of v2.0.1 (a
fictional character's date of birth) is gone. Speed: a 1.9 MB real document went from about 4.4 s to about 3.2 s; a short
note takes about 0.2 s.

### v2.1.1 test and fix (23 November 2026)

After release, v2.1.0 was tested on newly written documents and did poorly: in 22 documents written by a fresh agent,
11 of the 22 expected serious findings were missed and 5 documents got a false ENGEL (blocker). v2.1.1 fixes these.
The fix took four rounds; after each round a set **never seen before** was measured. The "first pass" column is the
result on that set before the code was adjusted to it, and is the real measure of generalisation.

| Set (22 docs each, 11 tr + 11 en) | Written by | Expected ENGEL/HATA | v2.1.0: missed / false ENGEL (docs) | First pass during the fix | v2.1.1 final |
|---|---|---|---|---|---|
| `tests/sinama-sonnet` (main set of the test report) | Sonnet 5.5 | 22 | 11 / 5 (5) | development set | 0 / 0 |
| `tests/sinama-claude` (15 counterexample docs) | Claude | 11 | 4 / 4 (3) | development set | 0 / 0 |
| `tests/sinama-neon1` | Gemini 4 Neon | 27 | 9 / 0 | after round 1: 2 / 2 (2) | 0 / 0 |
| `tests/sinama-sonnet2` | Sonnet 5.5 | 21 | 10 / 3 (3) | after round 2: 5 / 5 (4) | 0 / 0 |
| `tests/sinama-neon2` | Gemini 4 Neon | 25 | 9 / 2 (2) | after round 3: 1 / 2 (1) | 0 / 0 |

Honesty notes: the zeros in the last column are not evidence of generalisation, because every set was used to find gaps
after its first pass and is now a regression set. On the last unseen set the first pass missed 1 of 25 expected findings
and gave a false ENGEL in 1 document; expect a similar error rate on a new document. In round 2 the new dose rule
flagged correct calculations (fixed in rounds 3 and 4). The test was run by the session that develops Sınaç, so it is
not fully independent; the documents were written by agents that never saw the code, and expectations were locked with
SHA-256 before the script ran. French corpus (368 real notes): 0 documents with more ENGELs, 0 changed verdicts.
Speed: quadratic growth on a single long line is gone (56 KB line 20 s → 0.65 s); four synthetic 370 KB – 0.9 MB stress
inputs still take 2.4–5.6 s; the real 1.9 MB note takes about 3.2 s (unchanged).

## Usage

```bash
python3 ~/.claude/skills/sinac/scripts/ogretim_denetim.py lecture-note.md   # finds the field itself
python3 scripts/ogretim_denetim.py note.md --pdf note.pdf --alan tip        # PDF measurement, force the field
python3 scripts/ogretim_denetim.py note.md --json --yil 2026                # machine-readable; fixed evaluation year
```

In Claude, in plain words or by name: "Sınaç, audit this pharmacology note", "Does this PDF teach?", "Is my law lecture note
up to date?"

**Silencing a false alarm** (a reason is required; a silencing without a reason does not lift a blocker):

```markdown
<!-- sinac: yoksay tip_doz_yazimi — this page explains ISMP's wrong-writing examples -->
Drug 5.0 mg <!-- sinac: yoksay — teaching example of a wrong form; the correct one is below -->
```

## Installation

```bash
git clone https://github.com/mesutbsdgn/sinac.git ~/.claude/skills/sinac
```

Python 3.9+, standard library only, no network. For PDF measurement, optional poppler (`pdftotext`, `pdfimages`,
`pdftoppm`).

## How it was tested

**Tests:** 261 tests (including 211 counterexamples and 8 gold/test sets, 178 documents), all passing.

| File | Count | Scope |
|---|---|---|
| `test_ogretim_denetim.py` | 61 tests | Audit rules |
| `test_ozellikler.py` | 38 tests | Real generated PDFs: font size, vector drawing, blank page, PDF content; `--duzelt` (fix), encoding, silencing, masking, ReDoS |
| `test_f3.py` | 89 tests | Unit language guess, language-aware matching, lexicon, field groups, new rules |
| `test_karsi_ornekler.py` | 1 test, 211 counterexamples | Regression set |
| `test_sinama.py` | 71 tests | v2.1.1: unit doses, dose arithmetic in prose and tables, lab pairing, patient identity, teaching examples, speed |
| `test_altin.py` | 1 test, 8 sets, 178 documents | Verdict, missed BLOCKER and false BLOCKER are locked |

GitHub Actions runs these tests on Python 3.10 and 3.13 (the Ubuntu 26.04 image has no 3.9); it was also tested locally on
Python 3.9.6.

Review rounds:

| Round | Model | What it tested | Result |
|---|---|---|---|
| Independent review (22 Nov 2026) | GPT-6.1 Sol, Qwen4 Max Preview | Reviewed v1.0 at high effort, read-only | Of the counterexamples in the reports, 32 were run in the script and all 32 reproduced; fixed in v2.0 and added to the regression set (`scripts/tests/karsi_ornekler.json`) |
| Fable 5.2 test (same day, v2.0 candidate) | Fable 5.2 | Wrote 53 realistic documents (28 health) | Found a verdict-changing defect in 35, gave 3/10 for publication readiness. All critical and high findings were reproduced, fixed and added to the set as 55 records. Every one of the 131 records in the set names its source ("Sol 5", "Qwen K2", "Fable K3"); a few edge cases whose source is "TC checksum", "Patient age", "Cyrillic" were added by Claude |
| Gemini 4 Argon review (same day, last v2.0 candidate) | Gemini 4 Argon | Reviewed the code by reading | Gave 7.5/10. Of its 25 counterexamples, 20 were real output (3 did not reproduce, 2 partly); all were fixed and added as 23 records (154 in total) |
| Argon second round | Gemini 4 Argon | Verdict, silencing and `--duzelt` sections | 6.5/10; 7 of 9 claims were real output and were fixed |
| GPT-6.2 Astra test (last candidate) | GPT-6.2 Astra | 44 realistic documents on a copy, expectations written beforehand | 4/10; the verdict differed in 18 documents, Claude reproduced all of them, and all were real |
| Astra second round | GPT-6.2 Astra | 56 new documents (English health note, OCR, long table, LaTeX, law, code) | Again 4/10; the verdict differed in 23 documents, Claude reproduced 22 and all were fixed. All 117 documents Astra wrote over the two rounds now give the expected verdict |

Detailed findings of the rounds are in the [version history](#version-history) (v2.0.0 changes, Turkish README).

Other tests:

- **Deliberate breakage:** when the patient name, decimal sentence splitting, Markdown cleaning and blank-page threshold are
  deliberately broken, the tests turn red.
- **PDF calibration:** the word-box to font-size ratio was measured per typeface: Helvetica 0.925, Times 0.900, Courier
  0.786. That is why the script estimates a font size range, not a single size.
- **Speed** (22 Nov 2026, development machine, Python 3): a 1.9 MB real French lecture note took about 4.4 s in v2.0.1 and
  about 3.2 s in v2.1.0.

## Evidence

Three quoteproof research runs were done: 23 topics, 872 findings, 567 of them automatically verified in their source.

- **Sources opened by hand:** the critical facts behind each rule were opened in their source separately. They include
  ISMP, FDA, NHMRC, PEP 8, python.org, the Merck Veterinary Manual and bpac NZ. On the legislation side, Turkish Law
  No. 6098 art. 647, No. 6100 art. 450, No. 6102 art. 1533 and No. 6101 art. 1 were opened.
- **Sources that could not be opened:** facts whose source could not be opened were not made a BLOCKER or ERROR rule.

Details: [`docs/kanitlar.md`](docs/kanitlar.md); scale and verdict model: [`references/ogretim.md`](references/ogretim.md).

## Sibling skill: Durulaç

Sınaç does not simplify language; that is the job of its sibling skill
[Durulaç](https://github.com/mesutbsdgn/turkce-ai-durulac). If both are installed, Durulaç first simplifies the Turkish
explanation, then Sınaç measures.

## Limits

- It checks writing and structure; it does not prove that a dose, a diagnosis, a legal interpretation or a historical fact
  is correct.
- It is not medical, pharmaceutical, veterinary or legal advice.
- Field detection is lexicon-based; it can be wrong for health sub-fields (nursing, pharmacy, medicine) and for mixed
  documents. Correct it with `alan:` or `--alan`.
- English support covers field detection and the health safety rules; the warning and suggestion messages are in Turkish.
- **Open work:** the regression and gold sets consist of documents written by models; there is still no gold set of real
  lecture notes labelled by independent teachers and experts.
- **Measurement validity is untested:** that the 8 dimensions tell teaching quality apart has not been tested against
  teacher ratings or student outcomes; the total score is only an indicator.

## Version history

| Version | Date | Change |
|---|---|---|
| v2.1.1 | 23 Nov 2026 | Fixes from the test report: unit/kg doses, dose arithmetic in prose and tables, lab-conversion pairing, patient-identity variants, false ENGELs on historical figures and teaching examples, speed. See "v2.1.1 test and fix" |
| v2.1.0 | 22 Nov 2026 | Language-aware field detection (Turkish and English), field groups, new health rules. Changes below |
| v2.0.1 | 22 Nov 2026 | CI: Python 3.10 and 3.13 (the GitHub Ubuntu 26.04 image has no 3.9); code unchanged |
| v2.0.0 | 22 Nov 2026 | After the GPT-6.1 Sol, Qwen4 Max, Fable 5.2, Gemini 4 Argon (two rounds) and GPT-6.2 Astra (two rounds) reviews. See the Turkish README for the change list |
| v1.0.0 | 22 Nov 2026 | First release. Split out of Durulaç's `+ogretim` mode (v1.7–1.9) as a separate skill and named Sınaç |

<details>
<summary>Changes in v2.1.0</summary>

- **Field detection:** unit language guess (tr, en, fr; falls back to the document language when the signal is weak);
  Turkish lists only in Turkish units, English lists only in English units; French units do not count toward the field
  score; code blocks count only toward computing. The output carries `belge_dili` and `grup`.
- **Lexicon:** per field `sozcukler`, `obekler`, `sozcukler_en`, `obekler_en`, `kisaltmalar`; model generation, cross review
  and a local filter. Totals: 2355 Turkish words, 1499 Turkish phrases, 2680 English words, 1536 English phrases, 374
  abbreviations.
- **Field groups:** health, numerical-science, social-humanities, language-general; a health document below the threshold
  becomes `tip`.
- **New rules:**
  - "1,000 mg" as a thousands separator in an English unit;
  - cholesterol and triglyceride conversion (PubChem: cholesterol C27H46O 386.7 g/mol, CID 5997; triolein 885.4 g/mol, CID 5497163);
  - dose arithmetic in table rows and in prose; lab conversion in prose;
  - a teaching example of a wrong form is a warning, not a blocker;
  - a full name next to an age pattern is a blocker in a case context.
- **Measurement and tests:** 190 tests (211 counterexamples, 3 gold sets, 75 documents); the two unseen sets were first used
  to find gaps and then became regression sets. In the French corpus `dil` recognition went from 340 to 357.

</details>

## License

Usage-rights licence: [LICENSE](LICENSE). Copyright © 2026 mesutbsdgn.
