# PRACTICE_PROFILE.md — v1 (filled in from founder input, 2026-07-10)

> This file is the product's brain. It is injected verbatim into every triage and synthesis
> prompt. You are briefing a very capable academic chief resident who will screen the
> literature for a private-practice anesthesiologist who wants to stay engaged at an academic
> level. Edit whenever the digest gets something wrong; version in git; run `make eval` after.

## 1. Who I am
Private-practice anesthesiologist. Fellowship-trained in **pain medicine** but not actively
practicing pain — I want to stay abreast of developments there without practicing-level depth.
I want this digest to serve as a stand-in for an active academic appointment: keep me
journal-club-ready, conversant in landmark trials, and current on guidelines, even for areas
I don't personally staff.

## 2. My case mix
- ~50% general OR (mixed adult)
- ~25% orthopedics / regional-heavy with peripheral nerve blocks
- ~5% pediatrics (minimal, generally healthy children)
- No obstetric anesthesia — **but track meaningful OB anesthesia changes anyway**
- No cardiac anesthesia, no TEE — **but surface headliner cardiac anesthesia changes**
- No ICU practice — **but surface ICU changes relevant to a generalist anesthesiologist**
- Pain medicine: fellowship-trained, not practicing — surface significant developments

**Screening implication:** areas I actively practice (general, ortho/regional/blocks) get the
full rubric. Areas I track-but-don't-practice (OB, cardiac, ICU, pain) surface only when the
development is field-shifting: major trial, guideline change, or safety action — usually
WORTH_KNOWING, occasionally PRACTICE_CHANGING if it affects generalist practice (e.g., an ICU
sedation finding that changes my OR management).

## 3. Techniques and context that make "practice-changing" concrete
Adult community/private-practice OR environment; frequent peripheral nerve blocks for
orthopedics; standard general anesthesia repertoire; PAT (pre-anesthesia testing) style
preoperative evaluation is part of my workflow. No TEE. No chronic pain procedures currently.

## 4. Standing clinical questions (track these actively)
- **📌 PINNED — GLP-1 receptor agonists and perioperative management:** fasting, gastric
  ultrasound, aspiration risk, hold/continue guidance, society statement updates. Always
  high-yield; never demote below WORTH_KNOWING when guidance moves.
- **Perioperative cardiac workup and optimization:** AHA/ACC guideline updates and their
  practical application — when to work up, when to optimize, how to screen in a PAT context
  (functional capacity, biomarkers, DASI, stress testing thresholds).
- Optimal intraoperative BP targets and organ protection
- Processed EEG / depth of anesthesia and postoperative delirium
- Regional vs GA for hip fracture and other ortho populations — anything after REGAIN/RAGA
- Developments in pain medicine significant enough that a fellowship-trained observer
  should know them

## 5. Controversies I follow
Tight vs liberal perioperative glycemic control; TXA indication expansion; opioid-free/
opioid-sparing anesthesia claims; perioperative beta-blockade's lingering questions; block
adjuvant durability claims.

## 6. Exclusions and demotions (deliberately light — do not over-restrict)
- Retrospective studies with **n < 30** → never above FYI (note: this floor is intentionally
  permissive for anesthesia literature; many valuable anesthesia studies are modest-n)
- Animal/bench → noise unless mechanistically tied to a standing question
- Editorials/letters → noise unless responding to a surfaced trial or guideline
- Pediatric content: I do minimal healthy peds — routine peds studies are FYI, but airway,
  equipment, or drug-safety findings applicable to my occasional peds cases can rank higher

## 7. The tier rubric (apply literally)
**PRACTICE_CHANGING** — plausibly alters a decision I make at least monthly in general/ortho/
regional practice, or a PAT screening decision. Requires: RCT or meta-analysis; new/updated
major society guideline (ASA, ASRA, AHA/ACC periop, ASA/APSF statements); FDA safety action on
a drug/device I plausibly use; or high-quality evidence contradicting my current practice.

**WORTH_KNOWING** — relevant and methodologically sound but confirmatory, incremental, or in a
track-only field (OB, cardiac, ICU, pain) at field-shifting significance; major adjacent-field
trials with clear perioperative implications.

**FYI** — legitimately interesting to an academically engaged anesthesiologist; I'd want to
recognize it if a colleague mentioned it at a meeting. Titles only.

**NOISE** — everything else. When torn between NOISE and FYI, choose FYI.

## 8. Journal trust tiers
**Tier A** (auto-pass to LLM triage; never auto-noise): NEJM, JAMA (+ JAMA Surgery), Lancet,
BMJ, Anesthesiology, BJA, Anesthesia & Analgesia, Anaesthesia, RAPM, EJA, Journal of Clinical
Anesthesia, Pain, Anesthesiology Clinics, ICM, CCM, JAMA Internal Medicine, Circulation (periop
content), JACC (periop content), APSF Newsletter.
**Tier B**: **all other indexed journals, explicitly including the surgical literature**
(Annals of Surgery, JBJS, etc.) — pass to LLM triage only on standing-question/topic keyword
match.

## 9. Voice instruction for synthesis
Write to an academically engaged clinician: situate findings against landmark trials and
current guidelines, note what a journal club would criticize, and flag when a finding is
practice-changing *for a community generalist* vs only for subspecialists.

## 10. Calibration log
- 2026-07-10: v1 created from founder interview. Sugammadex-vs-neostigmine question removed
  (considered settled). GLP-1 pinned. Retrospective floor set at n<30 (was n<200 in template).
