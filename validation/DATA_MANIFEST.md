# DATA_MANIFEST — Arc /data corpus (verified 2026-07-04)

**Bottom line:** 35 sources, all URL-verified this session. 11 commit, 21 fetch-at-build, 3 link-only. 2 need a one-time manual browser download (CISA, ACMA). Zero fabricated URLs, zero dead links. Both demo runs (rectifier / DC undervoltage / thermal shutdown) are fully grounded. Biggest gap: RF antenna/VSWR family — do not inject RF faults beyond GPS-timing.

Rights key: **commit** = file goes in the public repo. **fetch-at-build** = script downloads at build time, repo holds URL + hash only. **link-only** = cite URL, never ingest.

---

## 1. Corpus at a glance

| ID | Title | Publisher | Family | Rights | Visual | Grounding use (one line) |
|----|-------|-----------|--------|--------|--------|--------------------------|
| S1 | EN 300 132-2 V2.8.1 — -48V DC power interface | ETSI | PWR | fetch-at-build | high | THE voltage-threshold source for demo run #1 (DC undervoltage) |
| S2 | ES 202 336-2 — DC power monitoring model | ETSI | PWR | fetch-at-build | high | Rectifier/battery monitoring points the Watchdog ingests |
| S3 | X.733 — Alarm reporting function | ITU-T | ALL | fetch-at-build | med | Alarm schema: 5 event types, 6 severities, probable causes |
| S4 | EN 300 019-1-3 V2.4.1 — Environmental classes | ETSI | ENV | fetch-at-build | high | HVAC failure → out-of-class temperature (demo run #2) |
| S5 | 3GPP TS 32.111-2 — Alarm IRP | 3GPP/ETSI | ALL | fetch-at-build | med | Standardized mobile-network alarm feed fields |
| S6 | 3GPP TS 28.532 V18.6.0 — 5G fault supervision | 3GPP/ETSI | ALL | fetch-at-build | med-high | getAlarmList REST semantics for Watchdog polling |
| S7 | ES 202 336-5 — Diesel genset monitoring model | ETSI | PWR | fetch-at-build | high | Genset-failure alarm points (start fail, fuel, mains-return) |
| S8 | X.721 — Management information definitions | ITU-T | ALL | fetch-at-build | low-med | OID registry for probable-cause enum values |
| S9 | G.8272 (07/25) — PRTC timing clocks | ITU-T | RF | fetch-at-build | med | GPS-timing-loss root-cause citation |
| S10 | M.3100 — Generic network info model | ITU-T | ALL | link-only | low | Transport probable-cause citation backup (Word-in-Zip, no PDF) |
| V1 | Vertiv NetSure NCU manual UM1M830BNA (282 pp) | Vertiv | PWR, ENV | fetch-at-build | high | Real severity semantics, LVD, BTRM, battery-test alarms for both runs |
| V2 | Eltek Smartpack2 Master Controller guide | Eltek | PWR, ENV | fetch-at-build | high | Real alarm names, 57.00V limit example, door alarm, LVD events |
| V3 | Eltek Smartpack S Controller guide | Eltek | PWR, ENV | fetch-at-build | high | Corroborating controller: relay wiring, battery/load disconnect |
| V4 | Vertiv NetSure 2100 -48VDC manual | Vertiv | PWR | fetch-at-build | med-high | Rectifier Comms Fail / Rectifier Lost alarms + clearing procedure |
| V5 | Vertiv NCU M830B/D datasheet | Vertiv | PWR | fetch-at-build | med | Controller model numbers + capability counts for Inventory |
| V6 | ELTEK-DISTRIBUTED-MIB | Eltek via LibreNMS | PWR | fetch-at-build | low | Real SNMP alarm OIDs for injected traps (both runs) |
| V7 | SP2-MIB (Smartpack2/eNexus) | Eltek via LibreNMS | PWR | fetch-at-build | low | Modern trap set incl. alarmGeneratorTrap, batteryTemperatures |
| V8 | LibreNMS eltek-webpower.yaml | LibreNMS (GPL-3.0) | PWR | **commit** | low | OID→equipment map + value encodings (divisor 100) for realistic telemetry |
| V9 | Nokia AirScale Radio Units Description | Nokia (reseller-hosted) | ENV, RF | link-only | high (capped) | Radio thermal limits (45C indoor max) — quote numbers, never ingest |
| I1 | FCC T-Mobile June 2020 outage report | FCC PSHSB | TRA, RF | **commit** | high | Gold-standard multi-cause RCA chain for ranked-causes eval |
| I2 | FCC CenturyLink Dec 2018 outage report | FCC PSHSB | TRA | **commit** | high | Equipment-internal root cause of network-wide symptom |
| I3 | FCC AT&T Feb 2024 outage report | FCC PSHSB | TRA | **commit** | med | Change-management failure + remediation recommendations |
| I4 | CRTC/Xona Rogers 2022 outage exec summary | CRTC | TRA | fetch-at-build | low-med | "14 hours to find root cause" — the pitch foil for Arc |
| I5 | FCC Hurricane Michael report (18-339) | FCC PSHSB | PWR, TRA, ENV | **commit** | high | Grid loss → genset/fuel → dispatch-asset chain (COWs, generators) |
| I6 | FCC DIRS status report 2018-10-13 | FCC | PWR, TRA | **commit** | high | Per-county outage tables — mass-alarm regional context |
| I7 | NIST Jan 2016 GPS UTC anomaly paper | NIST | RF | **commit** | high | GPS-timing-loss ground truth; constellation-vs-local misdiagnosis trap |
| I8 | CISA Nashville bombing case study | CISA/SAFECOM | ENV, PWR, TRA | **commit** (manual DL) | med-high (unread) | Physical event → power loss → flooding → service collapse cascade |
| I9 | ACMA Optus Nov 2023 investigation report | ACMA | TRA | fetch-at-build (geo-blocked) | med (unread) | Failed-emergency-call impact quantification + vendor-default finding |
| O1 | Lumen Service Level Agreement | Lumen | ALL | fetch-at-build | high | SLA clocks + credit percentages for Cost agent penalty math |
| O2 | FIST 3-6 Storage Battery Maintenance | US Bureau of Reclamation | PWR | **commit** | high | Battery failure modes + field-tech validation checklist |
| O3 | OSHA CPL 02-01-056 tower hoist directive | OSHA | RF, ENV | **commit** | med | Safety prerequisites Dispatch cites before tower work |
| O4 | UFC 3-540-07 Generator O&M | US DoD (WBDG) | PWR | **commit** | high | Genset PM schedule (Table 6-1) + ATS/load-test procedures |
| O5 | TelExpress Eaton APR48-3G listing | TelExpress | PWR | link-only | low | $769.04 real rectifier spare price for Cost agent |
| O6 | CALNET 3 Cat-5 SLA (Level 3 / State of CA) | CA STPD / Lumen | TRA, PWR | fetch-at-build | high | 14 stop-clock conditions + CAT 1 penalty exposure |
| O7 | NSRC NOC documentation deck (CC BY-NC 3.0) | NSRC | ALL | fetch-at-build | med | Site-inventory/per-port record schema for synthetic tickets |

---

## 2. Coverage by fault family

### Power/energy — CORE OF DEMO. Fully covered.
- **Detection:** V6, V7 (real trap OIDs: alarmMajorLowBattVolt, alarmACmains, alarmMajorRectifier, alarmLVD1open, alarmGeneratorTrap), V8 (OID→value encoding), S2 (monitored points), S3/S8 (severity + probable-cause schema), V1/V2/V3 (controller alarm tables).
- **Diagnosis:** S1 (normal range -40.5 to -57.0 VDC — the citable undervoltage floor), O2 (battery failure modes: sulfation, connection resistance, over-discharge), V4 (dead/removed rectifier alarm signatures), S7 + V7 (genset), I5 (grid-loss → backup chain at scale).
- **Remediation/cost:** V4 (rectifier replacement + alarm-clearing procedure), O2 (equalize/SG procedures), O4 (genset PM + ATS tests), O5 ($769.04 part price), O1/O6 (SLA credits), I5/I6 (dispatch assets: generators, COWs, fuel).
- **Gaps:** none material. Thinnest sub-branch is blown fuse/tripped breaker — covered only by V6 alarmDistributionBreakerOpen + V4 breaker alarm-contact note. Adequate for demo.

### Environment/physical — demo run #2 covered; remediation thin.
- **Detection:** S3 (probable causes verbatim: temperature unacceptable, heating/ventilation/cooling system problem, humidity unacceptable, enclosure door open, fire detected, flood detected, leak detected), V2/V3 (Door alarm log rows), V1 (BTRM + battery high-temp), V5 (SMTEMP 8-sensor module).
- **Diagnosis:** S4 is the load-bearing doc — class 3.1 climatogram + the verbatim 3.1E note tying climate-control failure to out-of-class conditions. CAUTION: quote the full note; 3.1E is a condition label, NOT a separate class. V9 supplies the radio-side limit (45C max indoor) but is link-only — quote figures with URL citation, never ingest pages.
- **Remediation/cost:** I8 (cascade narrative, unread — see section 5), O3 (roof/tower access), I5 (post-storm restoration).
- **GAPS (flagged):**
  1. No ingestable radio thermal-spec doc — V9 is rights-capped (page footers say "Nokia confidential", reseller-hosted pre-release draft). Best next lead: a Nokia/Ericsson official public datasheet; interim fallback is S4's class tables, already in corpus.
  2. No HVAC maintenance/repair manual at all. Nothing in the unverified lists covers this. Best next lead: a WBDG-hosted UFC HVAC O&M volume (same public-release channel as O4) — one targeted fetch.
  3. Smoke/fire grounded only by the X.733 probable cause. Acceptable — not in the injected runs.

### RF/radio — WEAKEST FAMILY. Detection OK, diagnosis partial.
- **Detection:** S3 (loss of signal, degraded signal, timing problem), S5/S6 (alarm feed fields).
- **Diagnosis:** GPS-timing branch is solid: I7 (real 2016 constellation incident, -13.7 us error, teaches upstream-vs-local disambiguation) + S9 (PRTC spec — landing page verified, PDF unread, the 100 ns figure is UNCONFIRMED; do not cite it until the PDF is fetched). I1 covers RF symptoms of transport causes.
- **Remediation/cost:** O3 (tower-access constraints for antenna work), O1 (SLA clocks).
- **GAPS (flagged):** no verified doc for VSWR / return loss / feeder-antenna faults or sleeping cells. The unverified lists contain nothing for this family. Best next leads: (a) fetch and read the S9 PDF (URL already verified, free); (b) a publicly hosted antenna-line app note (CommScope/RFS) as public-doc-copyrighted fetch-at-build. **Decision: do not inject RF faults beyond GPS-timing-loss in the demo.**

### Transport — diagnosis-rich via incidents; vendor-doc thin. Low priority (not in demo runs).
- **Detection:** S3 (loss of signal/frame), S6 (getAlarmList), S10 (link-only probable-cause backup).
- **Diagnosis:** best incident coverage of any family: I1 (routing misconfig cascade), I2 (vendor-equipment packet storm), I3 (untested change), I4 (14-hour blind diagnosis), I9 (vendor-default router self-isolation, partial).
- **Remediation/cost:** O1 + O6 (SLA clocks, stop-clock logic, CAT 1 penalties), I3/I4 recommendation lists.
- **Gap:** no microwave-backhaul or site-router/switch vendor manual; fiber-cut grounding is incident-report-only. Accept for hackathon.

---

## 3. Key real numbers — fault-injection seed table

Use these exact values in injected signals. Every number was read first-hand on-page this session unless flagged.

| # | Family | Value | Meaning | Source |
|---|--------|-------|---------|--------|
| 1 | PWR | -48 VDC nominal, positive earthed | Plant nominal voltage | S1 §4.1 |
| 2 | PWR | **-40.5 to -57.0 VDC** | Normal service voltage range — undervoltage = below -40.5 | S1 §4.2 |
| 3 | PWR | 24-cell lead-acid | Battery basis for -48V — links undervoltage to degraded battery | S1 §4.1 NOTE 2 |
| 4 | PWR | OID 1.3.6.1.4.1.12148.9.3.2.{i}, divisor 100 | Battery voltage: inject 4320 to signal 43.20 V | V8 |
| 5 | PWR | 0=not present, 1=normal, 2=alarm, 4=disabled | Rectifier status OID .12148.9.5.5.2.1.2.{i} states | V8 |
| 6 | PWR | INTEGER { normal(0), alarm(1) } | Alarm object syntax: alarmMajorLowBattVolt, alarmACmains, alarmMajorRectifier, alarmLVD1open | V6 |
| 7 | PWR | 57.00 VDC, hysteresis 0.10 VDC, delay 5 s | Worked MajorHigh over-voltage alarm example | V2 p24 |
| 8 | PWR | Critical = "endangers the power systems continued function"; Major = "reduces the power systems functionality" | Severity semantics, verbatim | V1 p16 |
| 9 | PWR | 1.75 V/cell | Absolute over-discharge floor | O2 §3.4.9 |
| 10 | PWR | 2.15 / 2.17 VPC | Float voltage (lead-antimony / lead-calcium) | O2 Figs 6-7 |
| 11 | PWR | SG >0.010 below full-charge, or cell >0.04 V below string average | Equalize-charge triggers (degraded-battery detection logic) | O2 §3.4.3 |
| 12 | PWR | <100 micro-ohms | Healthy connection resistance; above = investigate | O2 §3.5.5 |
| 13 | PWR | 100 F max | Electrolyte temperature ceiling during charge | O2 p24 |
| 14 | PWR | Monthly SG test; battery load test max 2/yr; ATS transfer test monthly per NFPA 110 | Genset/battery PM cadence (missed-PM root causes) | O4 §5-2.10/5-2.11.4 |
| 15 | PWR | **$769.04** | Eaton APR48-3G 1800W rectifier spare (92% eff., -40 to +70 C) — timestamp at build | O5 |
| 16 | ENV | Class 3.1 = temperature-controlled (IEC 3K3); "there is no separate class 3.1E" | HVAC-failure exceptional condition, verbatim note | S4 §4.1 Fig 1 |
| 17 | ENV | 45 C max indoor; 55 C outdoor shade; 50 C in sun; -40 C min | AirScale radio operating limits (cite URL, link-only) | V9 pp16/20 |
| 18 | ENV | -20 to +60 C | Site controller operating range | V3 p16 |
| 19 | ENV | 29 g/m3 | Class 3.2 absolute-humidity ceiling | S4 §4.2 |
| 20 | RF/ALL | cleared, indeterminate, critical, major, minor, warning | The 6 perceived severities, verbatim definitions | S3 §8.1.2.3 |
| 21 | RF/ALL | communications, QoS, processing error, equipment, environmental | The 5 event types | S3 §8.1.1 |
| 22 | RF | A0 = -13696.03 ns; 15 of 30 satellites; 2016-01-25 22:00 UTC | Real GPS timing anomaly magnitude + trigger | I7 |
| 23 | RF | 100 ns PRTC bound — **UNCONFIRMED, do not cite yet** | Pending S9 PDF read | S9 (flagged) |
| 24 | TRA | Notify: Critical 15 min / Incident 30 min; response 4 h | SLA clocks the Watchdog races | O1 §6.2/6.3 |
| 25 | TRA | TTR: High <4 h, Medium <12 h, Low <24 h | Time-to-resolve by severity | O1 Table 6.4.1 |
| 26 | TRA | 100 / 99.999 / 99.99 / 99.9 / 99.5 % | Availability tiers Platinum-Managed → Bronze | O1 Table 2.1 |
| 27 | TRA | CAT 1 = >=5 circuits or >=500 Mbps down; restore <=1-3 h; penalty 100% TMRC + 10 days ADUC | Catastrophic-outage penalty math for Cost agent | O6 §5.2.8.2 |
| 28 | TRA | Stop-clock #5 POWER: "trouble caused by a power problem outside of the responsibility of the Contractor" | SLA timer pauses — Dispatch logic, verbatim | O6 Table 5.5.7 |
| 29 | TRA | 23,621 failed 911 calls; >=41% call failure; 12+ h | T-Mobile 2020 impact magnitudes | I1 |
| 30 | TRA | ~37 h; 22M customers; 886 undelivered 911 calls | CenturyLink 2018 magnitudes | I2 |
| 31 | TRA | 125M devices; 92M calls blocked; 25,000 failed 911; misconfig at 2:42 AM | AT&T 2024 magnitudes | I3 |
| 32 | TRA | ~14 hours to pinpoint root cause; 12M+ customers | Rogers 2022 — Arc's pitch number | I4 |
| 33 | PWR/TRA | FL Bay County: 327 sites, 229 out, 70.0% | Mass-outage table row for regional context | I6 |
| 34 | TRA | 2,145 failed 000 calls; $12M AUD penalty — partial verification | Optus 2023 impact (see section 5) | I9 |

Retrieval caution: I1 never uses "OSPF" or "IMS" — index and query with the full phrases "Open Shortest Path First" and "IP Multimedia Subsystem".

---

## 4. Fetch plan

### A. Commit directly (11 files — public-domain US gov works + GPL project content)

```
docs.fcc.gov/public/attachments/DOC-367699A1.pdf          (I1)
docs.fcc.gov/public/attachments/DOC-359134A1.pdf          (I2)
docs.fcc.gov/public/attachments/DOC-404150A1.pdf          (I3)
docs.fcc.gov/public/attachments/DOC-357387A1.pdf          (I5)
docs.fcc.gov/public/attachments/DOC-354533A1.pdf          (I6)
tf.nist.gov/general/pdf/2886.pdf                          (I7)
usbr.gov/power/data/fist/fist3_6/fist3-6.pdf              (O2)
osha.gov/sites/default/files/enforcement/directives/CPL_02-01-056.pdf  (O3)
wbdg.org/FFC/DOD/UFC/ufc_3_540_07_2018_c1.pdf             (O4 — follows 301 to NIBS S3)
raw.githubusercontent.com/librenms/librenms/master/resources/definitions/os_discovery/eltek-webpower.yaml  (V8)
cisa.gov/sites/default/files/2023-02/22_0602_ecd_dependencies_2020-nashville-bombing_508C.pdf  (I8 — MANUAL BROWSER DOWNLOAD, CISA 403s all scripts; eyeball before commit)
```

### B. fetch-at-build script, in this order (21 URLs — demo-critical first)

1. `https://www.etsi.org/deliver/etsi_en/300100_300199/30013202/02.08.01_60/en_30013202v020801p.pdf` (S1)
2. `https://www.etsi.org/deliver/etsi_en/300001_300099/3000190103/02.04.01_60/en_3000190103v020401p.pdf` (S4)
3. `https://www.vertiv.com/globalassets/products/critical-power/dc-power-systems/UM1M830BNA_NCU_Controller.pdf` (V1)
4. `https://www.vertiv.com/globalassets/products/critical-power/dc-power-systems/um582138000-netsure-2100-user-manual.pdf` (V4)
5. `https://stt-solutions.ie/wp-content/uploads/2016/05/350020-013_UGde_Smartpack2_Master-Ctrller_2v0.pdf` (V2)
6. `https://raw.githubusercontent.com/librenms/librenms/master/mibs/eltek/ELTEK-DISTRIBUTED-MIB` (V6)
7. `https://raw.githubusercontent.com/librenms/librenms/master/mibs/eltek/SP2-MIB` (V7)
8. `https://www.etsi.org/deliver/etsi_es/202300_202399/20233602/01.01.01_60/es_20233602v010101p.pdf` (S2)
9. `https://www.etsi.org/deliver/etsi_es/202300_202399/20233605/01.01.01_60/es_20233605v010101p.pdf` (S7)
10. ITU X.733 PDF via `https://www.itu.int/rec/T-REC-X.733-199202-I/en` (S3)
11. ITU X.721 PDF via `https://www.itu.int/rec/T-REC-X.721-199202-I/en` (S8)
12. ITU G.8272 PDF via `https://www.itu.int/rec/T-REC-G.8272-202507-I/en` (S9 — read it; confirms/kills the 100 ns figure)
13. `https://www.etsi.org/deliver/etsi_ts/132100_132199/13211102/16.00.00_60/ts_13211102v160000p.pdf` (S5)
14. `https://www.etsi.org/deliver/etsi_ts/128500_128599/128532/18.06.00_60/ts_128532v180600p.pdf` (S6 — pin V18.6.0 in citations; V18.7.0 exists)
15. `https://www.tempestns.com/wp-content/uploads/2020/07/Eltek-Smartpack-S-Controller-ug.pdf` (V3)
16. `https://www.vertiv.com/globalassets/products/critical-power/dc-power-systems/ncu_m830b_m830d_datasheet_137198_0.pdf` (V5)
17. `https://assets.lumen.com/is/content/Lumen/lumen-service-level-agreementpdf` (O1)
18. `https://assets.lumen.com/is/content/Lumen/service-level-agreement-calnet-category-5-managed-internet-lvl-3?Creativeid=8fbe98a8-2f95-405a-aa3a-1e12b67ba612` (O6)
19. `https://nsrc.org/workshops/2012/menog-nmm/raw-attachment/wiki/Agenda/documentation.pdf` (O7 — CC BY-NC 3.0, keep attribution line)
20. `https://crtc.gc.ca/eng/publications/reports/xona2024.htm` (I4 — HTML, render to page)
21. `https://www.acma.gov.au/sites/default/files/2024-11/Investigation%20report%20-%20Optus%20outage%201Nov23%20(redacted).pdf` (I9 — geo-blocked from dev network; retry from Paris venue, else manual)

**Script requirements (verified failure modes):**
- etsi.org returns 403 to non-browser clients — send a browser User-Agent (confirmed: 206/application/pdf with UA).
- ITU PDFs download via the `dologin_pub.asp?...!!PDF-E&type=items` pattern, not a direct .pdf path.
- wbdg.org 301-redirects to an NIBS S3 bucket — follow redirects.
- Hash-pin every download (known-good file sizes recorded per entry; local verified copies exist in this session's tool-results dir for pinning).
- Never substitute iTeh preview PDFs — watermarked partial previews, verification-only.
- Re-fetch O5 price at build and timestamp the citation (listings float).

### C. Link-only (3 — cite URL + quoted figure, never ingest)

- S10 M.3100 — free download is Word-in-Zip, no rendered pages; cite by clause.
- V9 Nokia AirScale — "Nokia confidential" footer on a reseller-hosted pre-release draft; riskiest rights item in the set. Quote the 45C figure with URL in the citation trail only.
- O5 TelExpress — commercial product listing; the number is the value.

### Rights rationale (say this to a judge)

Everything in the repo is either a US government work (public domain by statute) or content authored by a GPL-licensed open-source project — assets we unambiguously have the rights to redistribute. Every standard and vendor manual we ground on is freely and publicly downloadable from its publisher, but carries a no-redistribution copyright — so the repo ships a fetch script and hash-pinned URL citations, never the copyrighted bytes; the agents' citation trail points at the public source. Anything with doubtful hosting rights or unusable format is cited by link only, and nothing paywalled was used at all.

---

## 5. Unverified, partial, and flagged (honesty section)

**Nothing dropped; nothing fabricated. Two entries content-unread, six details flagged.**

Partial-verification entries (URLs real and search-confirmed with exact direct links; page content NOT read this session):
1. **I8 CISA Nashville** — cisa.gov returns 403 to WebFetch AND to Python urllib with a full Chrome UA (blocks all non-browser clients). Exact URL + title independently search-confirmed plus CISA's announcement page. Action: one-time manual browser download, human eyeballs it, then commit (public-domain federal work). Until then treat all key facts beyond the announcement summary as unverified.
2. **I9 ACMA Optus** — acma.gov.au unreachable from this network (ECONNRESET / read-timeout on every URL tried, incl. the HTML statement page; likely geo-restriction). Exact URL search-confirmed as top result with matching RCA summary; impact figures corroborated via ACMA's penalty article. Action: retry from the Paris venue network or manual download; if neither works by demo, downgrade to link-only or drop. Filename quirk: says "1Nov23" but the outage was 8 Nov 2023.

Flagged unconfirmed details inside otherwise-verified entries (do not cite until resolved):
- S9 G.8272: the 100 ns PRTC accuracy bound — PDF not read (fetch step 12 resolves this).
- S8 X.721: "Amd.1 (08/2001)" existence — not re-verified; cite the 02/92 edition only.
- S10 M.3100: "Cor.1 (2005-11-13)" — not re-verified.
- S1 EN 300 132-2: numeric abnormal-service-voltage limits — beyond the preview pages read; definition confirmed, numbers not.
- O3 OSHA: Appendix A specifics (e.g. brake-capacity percentages) — unread; cite main-body facts only.
- I9 ACMA: per-entity 000-call breakdown (2,091+42+12) sums to the corroborated 2,145 total but was not independently line-verified.

Known corrections already baked into this manifest: TS 28.532 V18.7.0 supersedes V18.6.0 (URL pinned); EN 300 019-1-3 "no separate class 3.1E" must be quoted in full; both Eltek MIBs downgraded commit → fetch-at-build (vendor-authored content inside a GPL repo); Nokia downgraded to link-only; I1 requires full-phrase retrieval keywords; NCU datasheet dimensions are M830B-specific; O5 page spec table (220/240V input) overrides its URL slug.


---

## WAVE 2 — Six Deep Veins (verified corpus)

**Decision in five lines:** 59 unique sources verified live this session across open-data, PD manuals, RF/timing, transport, runbooks, cost/impact. **29 are commit-safe now** (US-gov PD, MIT, CC-BY, IETF), **23 fetch-at-build**, **7 link-only**. Category grades all A-/A; zero invented URLs. Commit blockers: strip 2 IEEE tables + 3 vendor photos from TM 5-693 before push; ENISA minus cover image; O*NET needs CC-BY attribution line. The demo's rectifier/DC-undervoltage/thermal run is fully grounded: FIST 3-6 sec 6.4 + TM 5-693 Tables 4-1..4-7 (causes/fixes), NASA battery + NAB (telemetry shapes), EAGLE-I (grid-loss timing), Flatpack2 + CSB prices (cost lines).

Families: **PWR** power/energy · **ENV** environment/physical · **RF** RF/radio · **TRN** transport. Visual value = worth to VultronRetriever (rendered pages).

---

### 1. Corpus at a glance

#### Vein 1 — Open datasets

| Title | Publisher | Family | Rights action | Visual | Grounding use |
|---|---|---|---|---|---|
| EAGLE-I Electricity Outages 2014–2025 | ORNL / US DOE | PWR | commit slices; full files fetch-at-build | L (demo charts H) | Real county grid-loss windows → alarm timing + grid-vs-rectifier discrimination |
| NASA PCoE Li-ion Battery Aging | NASA Ames (PHM mirror) | PWR | commit | L | Measured capacity-fade → synth degraded -48V discharge profile |
| NAB machine_temperature_system_failure | Numenta | ENV, PWR | commit | L | Real thermal-anomaly shapes, 3 labeled anomalies → HVAC→thermal-shutdown run |
| ITU/KDDI PS-032 + PS-015 failure data | KDDI / ITU Challenge | TRN | fetch-at-build (no license) | L | Labeled IP-core/5GC failure classification eval for transport root cause |
| Loghub — BGL + Thunderbird | LogPAI | ENV, TRN | fetch-at-build | L | Real syslog formats/bursts; BGL alert labels for Watchdog ingest realism |
| Telecom Italia Milan CDR grid | TIM / Harvard Dataverse | RF | fetch-at-build (ODbL) | L (heatmap H) | Real per-cell diurnal traffic + neighbor structure → sleeping-cell logic |
| SMD Server Machine Dataset | NetMan / Tsinghua | TRN, ENV | commit | L | Labeled anomalies + contributing-dimension labels → root-cause attribution scoring |

#### Vein 2 — Public-domain manuals (power/environment core)

| Title | Publisher | Family | Rights action | Visual | Grounding use |
|---|---|---|---|---|---|
| TM 5-693 UPS Selection/Maintenance | US Army (WBDG) | PWR | commit — strip IEEE Tables 2-2, 3-1 + vendor Figs 4-1/4-2/4-4 | VH | Corrective-action matrices Tables 4-1..4-7: rectifier/battery/inverter symptom→fix |
| TM 5-685 / NAVFAC MO-912 Auxiliary Generators | Army + Navy | PWR | commit | H | Genset troubleshooting tables (diesel 3-5, generator 4-2, switchgear 5-1..5-3) |
| UFC 3-540-07 Generator O&M (2018/C1 2019) | US DoD | PWR | commit | M-H | Current O&M doctrine: safety-step ordering, test procedures, intervals |
| UFC 3-520-05 Stationary Batteries (2015/C2 2020) | US DoD | PWR, ENV | commit | M | VRLA ventilation, float charge, battery-room criteria for -48V plant |
| TM 9-6140-200-14 Lead-Acid Batteries | US Army | PWR | commit | H | Field-tech PMCS + verbatim safety warnings for mobile validation checklists |
| TM 5-692-2 C4ISR System Design Features (2005; 2001 archive also verified) | US Army | PWR, ENV | commit | H | 24-chapter site-equipment ontology: UPS, gensets, chilled water, air handling |
| MIL-HDBK-411B Vol I Power & Environment | US DoD (EverySpec) | PWR, ENV | commit | H | Power-disturbance taxonomy + protection devices — what Watchdog alarms mean |
| MIL-HDBK-419A Vol I Grounding/Bonding/Shielding | US DoD (NIBS S3) | ENV, RF, PWR | commit | VH | Grounding/lightning theory for storm-correlated fault chains |
| FAA-STD-019f (Chg 3, 2020) | FAA | ENV, PWR, RF | commit | H | Mandatory lightning/surge/grounding requirements, field-failure pedigree |
| NEETS Module 10 (NAVEDTRA 14182A) | US Navy (Commons) | RF | commit | VH | Transmission-line/SWR physics behind VSWR alarms; 356 diagram-dense pages |
| RUS Bulletin 1751E-302 CO Power | USDA RUS | PWR | fetch-at-build (browser UA required) | unknown | Telecom-native -48V CO power plant spec — body still unread |

#### Vein 3 — RF & timing

| Title | Publisher | Family | Rights action | Visual | Grounding use |
|---|---|---|---|---|---|
| Understanding Cable & Antenna Analysis | Anritsu | RF | fetch-at-build | H | RL/VSWR/DTF semantics, conversion math, cable-loss table |
| S331L Troubleshooting Guide | Anritsu | RF | fetch-at-build | VH | Pass/fail thresholds + fault-signature poster (lightning, corrosion, pinch) |
| ITU-T G.8272 (07/2025) PRTC | ITU-T | RF | fetch-at-build | M-H | PRTC accuracy classes + holdover semantics for GPS-loss alarms |
| ITU-T G.8271.1 (11/2022) time sync limits | ITU-T | RF, TRN | fetch-at-build | H | Time-error budgets → GPS loss becomes a truck-roll countdown |
| Microsemi Rubidium Holdover WP | Microsemi/Microchip | RF | fetch-at-build — footer says Proprietary, never commit | H | Quartz-vs-Rb holdover hours → dispatch deadline after GNSS loss |
| Kaelus PIM Testing Guidelines | Kaelus | RF | fetch-at-build | H | PIM = "sweeps pass but sector noisy" cause + tap/flex validation |
| arXiv:1501.03935 sleeping cells | arXiv | RF | link-only (non-CC) | L-M | Citable definition/method for alarm-invisible outage |
| O-RAN SC OAM fault.rst | O-RAN SC (LF) | RF, TRN | commit (CC-BY-4.0) | L-M | Committable real 5G alarm severities + FM flow → Watchdog schema |
| o-ran-fm→VES fault mapping | O-RAN SC wiki | RF, TRN | fetch-at-build | M | Field-level O-RU alarm payload shape for Watchdog emit/parse |
| arXiv:2311.02390 self-healing survey | arXiv | RF | fetch-at-build (CC BY-NC-SA) | L | Citation backing the self-healing pitch framing |

#### Vein 4 — Transport

| Title | Publisher | Family | Rights action | Visual | Grounding use |
|---|---|---|---|---|---|
| RFC 5880 BFD | IETF | TRN | commit | M-H | Fastest backhaul-down signal; detection-time math, flap vs hard failure |
| RFC 5357 TWAMP | IETF | TRN | commit | M | How delay/loss probes measure — citation for synthetic telemetry |
| RFC 3393 IPDV (jitter) | IETF | TRN | commit | L-M | Formal jitter definition; thresholds delegated to SLAs |
| RFC 2544 benchmarking | IETF | TRN | commit | M | Post-repair link validation procedure for the field tech |
| ITU-T G.8032 ring protection | ITU-T | TRN | fetch-at-build | H (in PDF) | Why one fiber cut may NOT down a site (protection switch) |
| ITU-T G.8013/Y.1731 Ethernet OAM | ITU-T | TRN | fetch-at-build | H (in PDF) | Standard behind CC-loss / frame-loss / delay backhaul alarms |
| ITU-T G.826 error performance | ITU-T | TRN | fetch-at-build | M | ES/SES vocabulary of microwave/SDH alarm matrices |
| ITU-T Y.1541 IP QoS objectives | ITU-T | TRN | fetch-at-build | H (in PDF) | Carrier-neutral "out of spec" yardstick per QoS class |
| Verizon Global Latency/PDR SLA | Verizon | TRN | link-only | M | Real carrier SLOs to score alarms as SLA-breaching |
| Lumen master SLA (12 pp) | Lumen | TRN | fetch-at-build | VH | Availability tiers, TTR clocks, credit math — cost + deadline engine |
| FCC CenturyLink 2018 outage report | FCC PSHSB | TRN | commit | M (Infinera schematic) | Real 37-h transport catastrophe: cascade precedent + impact numbers |
| AFL Fiber Reliability (Bellcore data) | AFL / Southern Telecom | TRN | fetch-at-build | H | Only real fiber-cut rates + MTTR distributions found |
| Ericsson Microwave Outlook 2025 | Ericsson | TRN | fetch-at-build | H | Microwave-backhaul prevalence; rain-fade vs equipment context |
| Cambium LINKPlanner guide | Cambium | TRN | fetch-at-build — PLAUSIBLE only | claimed H, unverified | Fade-margin math for "rain fade, self-clears" vs "dispatch" |

#### Vein 5 — Runbooks & process

| Title | Publisher | Family | Rights action | Visual | Grounding use |
|---|---|---|---|---|---|
| FAA Order 6000.15E NAS maintenance | FAA (govinfo) | all 4 | commit | M | Real operator restoration-order + response-time + log discipline |
| FIST 3-6 Storage Battery Maintenance | US Bureau of Reclamation | PWR | commit | H | CORE OF DEMO: rectifier-charger troubleshooting 6.4, under/overvoltage 8.4, battery troubles 3.5.7 |
| FIST 4-1B Maintenance Scheduling | US Bureau of Reclamation | PWR, ENV | commit | H | PM task+frequency tables → overdue-PM as ranked cause; dispatch follow-ups |
| OSHA 3877 Tower Best Practices | OSHA + FCC | RF, ENV | commit | L-M | Cited safety steps whenever remediation requires tower work |
| OSHA CPL 02-01-056 hoist directive | OSHA | RF, ENV | commit | L | Regulatory citation web for tower-access dispatch constraints |
| 47 CFR 4.9 outage-report thresholds | FCC (via Cornell LII) | all 4 | commit regulation text | L (→ severity matrix) | THE real severity ladder + escalation clocks for the Orchestrator |
| CENIC NOC Escalation List | CENIC | TRN | link-only (PII on page) | M | Real 5-level ladder + 15-min timer — copy structure, anonymized |
| Motorola R56 (2005, BLM copy) | Motorola | PWR, ENV, RF | fetch-at-build — explicit no-duplication clause, NEVER commit | VH | Industry site bible: ~100 pp grounding diagrams, HVAC design, site ontology |
| Carleton NOC incident flowchart | Carleton ITS | TRN | fetch-at-build | H | One-page human NOC flow Arc automates — retrieval page + pitch evidence |

#### Vein 6 — Cost & impact

| Title | Publisher | Family | Rights action | Visual | Grounding use |
|---|---|---|---|---|---|
| O*NET 49-9052 wage data | USDOL (O*NET) | all 4 | commit (CC BY 4.0, attribute) | L-M | Labor $/hr for every truck-roll cost line |
| Eltek Flatpack2 2kW rectifier listing | WirelessUnits | PWR | link-only | L | Real $1,329.79 swap price for the demo's rectifier run |
| CSB TPL121000 battery listing | Tech Battery Solutions | PWR | link-only | L | Real $314.95/unit; min order 4 = exactly one -48V string |
| Truck-roll cost benchmark | SightCall blog | all 4 | link-only | L | $150–500 direct / >$1,000 loaded — headline avoided cost |
| Climb-vs-drone inspection cost | AeroDeploy | RF, ENV | link-only | L | $800–1,500/climb — price interventions, not just severity |
| FCC DA 21-1439 T-Mobile consent decree | FCC | TRN | commit | L-M | $19.5M penalty exposure for one unresolved routing fault |
| ENISA Telecom Security Incidents 2024 | ENISA | all 4 | commit (CC BY 4.0; drop Shutterstock cover) | H | EU user-hour denominators + root-cause priors (cable cuts 23%) |
| Uptime Institute Outage Analysis 2025 | Uptime Institute | PWR | fetch-at-build (all rights reserved) | H | 54% of outages >$100K; power = #1 cause = Arc's demo family |

---

### 2. Key real numbers (per-number source)

#### RF thresholds

| Value | Meaning | Source |
|---|---|---|
| 15 dB RL | Common cable+antenna system pass limit | https://dl.cdn-anritsu.com/en-us/test-measurement/files/Technical-Notes/White-Paper/11410-00427F.pdf |
| 15.5 dB RL / VSWR 1.40 | Sweep pass criterion at antenna passband edges | https://dl.cdn-anritsu.com/en-us/test-measurement/files/Manuals/Troubleshooting-Guides/11410-00674B.pdf |
| RL 20 dB = 1% reflected; 10 dB = 10% | Reflected-power semantics; 10 dB ≈ 10% coverage shrink | both Anritsu docs above |
| Antenna 15–25 dB; line+load 30–40 dB | Expected RL by termination | https://dl.cdn-anritsu.com/en-us/test-measurement/files/Manuals/Troubleshooting-Guides/11410-00674B.pdf |
| DTF: open/short 0–5, antenna 15–25, connector 30–40 dB | Typical DTF amplitudes for fault ID | same |
| Fault Res.(m) = 150·vp/ΔF(MHz); Dmax = (points−1)·res | DTF localization math | https://dl.cdn-anritsu.com/en-us/test-measurement/files/Technical-Notes/White-Paper/11410-00427F.pdf |
| LDF4-50A: vp 0.88, 0.073 dB/m @1 GHz | Cable-loss reference row | same |
| +43 dBm (20 W) two tones | IEC 62037 PIM test power | https://www.kaelus.com/getmedia/05e10142-8100-4312-9fa5-c8fff9411fe1/PIM-Testing-Guidlines.pdf.aspx?ext=.pdf |
| 2.2–3.0 dB per dB; −5–10 dB per order; flex ±25 mm | PIM slope; IM5/7/9 falloff; dynamic test motion | same |

#### Timing (GPS-loss countdown)

| Value | Meaning | Source |
|---|---|---|
| PRTC-A 100 ns / PRTC-B 40 ns to UTC | Locked-mode accuracy classes | https://www.itu.int/rec/dologin_pub.asp?lang=e&id=T-REC-G.8272-202507-I!!PDF-E&type=items |
| ±2 ns | 1PPS cable-delay compensation tolerance | same |
| max\|TE_L\| ≤ 1100 ns at ref point C; MTIE plateau 580 ns (275<τ≤10000 s); dTE_H < 200 ns | Network limit for ±1.5 µs class-4 (5G TDD) apps | https://www.itu.int/rec/dologin_pub.asp?lang=e&id=T-REC-G.8271.1-202211-I!!PDF-E&type=items |
| 150 ns | Assumed end-application (fronthaul) TE budget | same |
| Quartz 24 h holdover: <750 ns only 90%, <400 ns only 50% | Post-GNSS-loss drift, precision quartz | https://ww1.microchip.com/downloads/aemDocuments/documents/FTD/ProductDocuments/WhitePaper/Premier_Holdover_Performance_with_Microsemi_Rubidium_Technology.pdf |
| Rb: 400 ns/24 h spec; 178 ns measured avg | Rubidium holdover, 10-unit study | same |

#### Transport SLAs & performance

| Value | Meaning | Source |
|---|---|---|
| ≥1 s (1,000,000 µs) tx interval when session not Up; Detect Time = mult × interval | BFD semantics | https://www.rfc-editor.org/rfc/rfc5880 |
| 41 / 104 octets | TWAMP min test packet (unauth / auth+encrypted) | https://www.rfc-editor.org/rfc/rfc5357 |
| 64/128/256/512/1024/1280/1518 B; ≥60 s trials | RFC 2544 validation regime | https://www.rfc-editor.org/rfc/rfc2544 |
| RTT: NA 45, EMEA 30, NY–London 90, LA–Tokyo 160, APAC 125, LatAm 140, Japan 30 ms | Verizon latency SLAs | https://www.verizon.com/business/terms/global_latency_sla/ |
| PDR 99.5% (NA + transatlantic), 99% (EMEA/APAC/LatAm/Japan); jitter ≤1 ms US; MOS ≥3.8 | Verizon delivery/jitter/voice SLAs | same |
| Availability: Bronze 99.5 → Platinum Managed 100% | Lumen tiers (Table 2.1) | https://assets.lumen.com/is/content/Lumen/lumen-service-level-agreementpdf |
| Latency intra-NA <45, intra-EU <35, transatlantic <95, transpacific <235 ms; jitter <3 ms; PDR 99.95% | Lumen POP-POP targets | same |
| Notify: Critical 15 min, Incident 30 min; TTR High <4 h / Med <12 h / Low <24 h | Lumen ops clocks | same |

#### Fiber & microwave field data

| Value | Meaning | Source |
|---|---|---|
| 2.130 vs 0.085 vs 0.081 failures/1000 km/yr | Buried vs OPGW vs ADSS (aerial >25× better) | https://www.southern-telecom.com/content/dam/southern-telecom/pdfs/AFL-Reliability.pdf |
| Excavation = 80% of direct-buried failures; 86% of dig-ins sever all fibers | Cause distribution | same |
| Permanent repair mean 13.8 h, median 8.0 h; restoration mode 4–6 h | Fiber-cut MTTR — dispatch expectation setting | same |
| 75% of live 5G networks use microwave backhaul; 2030 split fiber 51/microwave 49 | Microwave is mainstream failure surface | https://www.ericsson.com/en/reports-and-papers/microwave-outlook |

#### Regulatory & ops clocks

| Value | Meaning | Source |
|---|---|---|
| ≥900,000 user-minutes AND ≥30 min (or ≥667 OC3-min, or any 911/988 facility, or MSC failure) | FCC reportable-outage threshold = Arc severity ladder | https://www.law.cornell.edu/cfr/text/47/4.9 |
| 120 min notify / 72 h initial / 30 d final; 911 facilities ≤30 min + 2 h follow-up; VoIP 240 min / 24 h | NORS escalation timers | same |
| 15 min per level, 5 levels | Real NOC escalation timer (CENIC) | https://cenic.org/network/operations/noc-escalation |
| Rigging SF 10; hoist derated ×2 for personnel; proof test 125% for 5 min | Tower-hoist safety constants | https://www.osha.gov/sites/default/files/enforcement/directives/CPL_02-01-056.pdf |

#### Prices & labor

| Value | Meaning | Source |
|---|---|---|
| $35.73/hr median; $74,330/yr | Telecom line installer/repairer wage (SOC 49-9052) | https://www.onetonline.org/link/summary/49-9052.00 |
| $1,329.79 | Eltek Flatpack2 HE 48V/2000W rectifier (pn 241115.105), new | https://wirelessunits.com/eltek-flatpack2-high-efficiency-rectifier-48v-2000w/ |
| $314.95/unit; min 4 units (~$1,260/string, derived) | CSB TPL121000 12V 100Ah; 4×12V = one -48V string | https://www.techbatterysolutions.com/csb-tpl-121000-telecom-power-12v-100ah-battery/ |
| $150–500 direct; >$1,000 fully loaded | Truck-roll cost per dispatch | https://sightcall.com/blog/how-to-reduce-truck-rolls/ |
| $800–1,500/climb vs $350–600/drone; 1 vs 4–6 towers/day | Tower inspection economics (vendor figures) | https://aerodeployuav.com/drone-inspection-cost-vs-traditional/ |

#### Incident impact (pitch ammunition)

| Value | Meaning | Source |
|---|---|---|
| $19,500,000; 12 h 13 min; >23,000 failed 911 calls | T-Mobile 2020 settlement — fiber link + routing flaw | https://docs.fcc.gov/public/attachments/DA-21-1439A1.pdf |
| ~37 h; 22M customers/39 states; 886 failed 911 calls; 4 malformed packets | CenturyLink 2018 — one Denver switching module | https://docs.fcc.gov/public/attachments/DOC-359134A1.pdf |
| 188 incidents; 1,743M user-hours (2024); system failures 60%; cable cuts 23%; natural phenomena 605M user-hours | EU annual telecom incident stats | https://www.enisa.europa.eu/sites/default/files/2025-07/ENISA_Telecom_Security_Incidents_2024_en_1.pdf |
| 54% of significant outages > $100K; 1 in 5 > $1M; power = 54% of impactful-outage causes | Cost-of-downtime anchor | https://uptimeinstitute.com/uptime_assets/d7c049ef5b02a6e0a15540a3e5cb8fbf742c7fa54a1af6caeaaab32b7c15d443-GA-2025-05-annual-outage-analysis.pdf |

#### Power/battery constants

| Value | Meaning | Source |
|---|---|---|
| EOL = 30% capacity fade (2 Ah → 1.4 Ah) | NASA battery run-to-failure endpoint | https://catalog.data.gov/dataset/li-ion-battery-aging-datasets |
| FIST 3-6: Table 1 voltage ranges p.14; rectifier troubleshooting sec 6.4 p.79; under/overvoltage sec 8.4 p.91 | -48V plant reasoning anchors | https://www.usbr.gov/power/data/fist/fist3_6/fist3-6.pdf |
| TM 5-693: corrective-action Tables 4-1..4-7 pp.4-19..4-23; battery inspection Tables 5-2..5-5 | Symptom→fix matrices for the demo run | https://www.wbdg.org/FFC/ARMYCOE/COETM/tm_5_693.pdf |

---

### 3. Open datasets — license as read, format/size, exact scenario fed

**EAGLE-I (ORNL/DOE)** — https://doi.org/10.6084/m9.figshare.24237376
License as read: CC BY 4.0 (figshare API license field, name + CC URL). Format: one CSV/year, county FIPS × 15-min customers-out; 2014 = 78 MB up to 2025 = 1.40 GB (17 files, API-confirmed). Feeds: **grid-loss injection** — Watchdog samples "commercial power fail" onset/duration from real county outage windows; **grid-vs-rectifier discrimination eval** — Correlation checks site alarm against concurrent county outage; no county outage + DC undervoltage = site-local rectifier fault. Commit filtered slices only; full years fetch-at-build (GB scale).

**NASA PCoE Battery Aging (Saha & Goebel 2007)** — https://data.phmsociety.org/nasa/
License as read: US-gov work, no explicit license; PHM mirror terms = liability disclaimer + acknowledgement request (put line in NOTICE). Format: MATLAB-style archives, 18650 cells, charge/discharge/EIS cycles to 30% fade. Feeds: **degraded-backup-battery run** — scale measured fade curves into a -48V plant discharge profile during grid loss; early sag = degraded bank, the quantitative evidence behind Root-Cause's ranked cause and the eval's ground truth.

**NAB machine_temperature_system_failure.csv (Numenta)** — https://github.com/numenta/NAB
License as read: MIT (raw LICENSE.txt fetched). Format: single CSV in-repo; realKnownCause category (7 datasets), 3 documented anomalies (planned shutdown, hard-to-detect failure, catastrophic failure). Feeds: **HVAC-failure → thermal-shutdown run** — anomaly shapes drive injected cabinet-temperature telemetry; labeled windows = detection eval with no hand labeling.

**ITU/KDDI PS-032 + PS-015** — https://github.com/ITU-AI-ML-in-5G-Challenge/ITU-ML5G-PS-032-KDDI-naist-lsm
License as read: NONE stated anywhere → never commit. Format: 4 tar.gz (train/eval data + labels) at ieice.org/~rising/AI-5G/dataset/theme1-KDDI/ (sizes unpublished, not byte-verified); PS-015 = 73 GB behind ITU portal login. Feeds: **transport root-cause eval** — labeled route-information-failure classification for the site-router/backhaul family. Keep SMD/Loghub as demo-day fallback if the IEICE host dies.

**Loghub BGL + Thunderbird (LogPAI)** — https://zenodo.org/records/3227177
License as read: Zenodo metadata CC BY 4.0, but repo README says "freely available for research or academic work" — mixed signals, treat as research-use, fetch-at-build only. Format: BGL.tar.gz 62.9 MB (4,747,963 lines, 214.7 days, alert-labeled incl. hardware/temperature/power); Thunderbird.tar.gz 2.0 GB. Feeds: **Watchdog ingest realism** — real syslog line formats and burst patterns; BGL alert labels = labeled ingestion eval. Pull BGL only (small, labeled). Closest open substitute for an SNMP-trap corpus (none exists).

**Telecom Italia Milan (Big Data Challenge)** — https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/EGZHFV
License as read: ODbL 1.0 (Dataverse native API terms; attribution + share-alike). Format: 61 daily .txt files, ~277–376 MB each, 2013-11-01→2014-01-01, per-grid-cell SMS/call/internet activity. Feeds: **sleeping-cell / cell-down scenario** — zero out one grid cell while neighbors keep real diurnal shapes; Correlation must localize the dark cell. Share-alike: fetch 2–3 days at build, ship only derived plots/samples with ODbL notice, raw stays out of the repo.

**SMD (OmniAnomaly)** — https://github.com/NetManAIOps/OmniAnomaly
License as read: repo MIT; dataset ships inside repo, MIT-by-inclusion (minor ambiguity acknowledged). Format: plain-text matrices, 28 machines × 38 metrics, 708,405 train / 708,420 test points, 4.16% anomaly ratio, plus interpretation_label (contributing dimensions per anomaly). Feeds: **root-cause attribution eval** — inject an anomaly window, score whether Root-Cause ranks the truly contributing metrics first. This is the only dataset in the corpus that scores attribution, not just detection. Commit a per-machine subset with MIT notice.

---

### 4. Per-family gaps still open, with best next lead

**Power/energy** (strongest family — manuals + runbooks + 2 datasets + real prices):
- No real -48V *plant-level* telemetry; NASA is cell-level 18650. Lead: synthesize plant discharge from NASA fade curves + FIST 3-6 Table 1 voltage ranges — closes by synthesis, no new source needed.
- RUS 1751E-302 body unread (the one telecom-native CO power spec). Lead: build-time fetch with browser User-Agent; then siblings 1751F-810 (electrical protection) and 1751E-320.
- No vendor rectifier alarm-code matrix (Eltek spec page dead; Delta manual behind terms gate). Lead: accept Delta filecenter terms in a real browser once; fallback = TM 5-693 Tables 4-1..4-7 already committed.

**Environment/physical** (thinnest family):
- No HVAC troubleshooting matrix at TM 5-693 depth. Lead: **TM 5-692-1** (maintenance procedures companion) — direct URL confirmed at wbdg.org/FFC/ARMYCOE/COETM/ARCHIVES/tm_5_692_1_2001.pdf, unfetched; read its rights page before commit.
- No labeled humidity/water-intrusion/door/smoke dataset; NAB is one temperature sensor. Lead: none verified open — synthesize from NAB shapes + BGL temperature/power alert-labeled lines; label as synthetic.
- R56 HVAC ch 3.8 is the best design text but uncommittable. Already handled: fetch-at-build from the BLM URL.

**RF/radio:**
- No open per-cell KPI dataset with *labeled* outages (Milan CDR is a traffic proxy). Lead: inject outage into Milan grid, cite arXiv:1501.03935 for method legitimacy.
- No GNSS jamming/interference event dataset found open. Lead: none — ground the countdown in G.8272 holdover + Microsemi numbers instead; say so in the report.
- No committable sweep traces (Anritsu copyrighted). Lead: NEETS Modules 11 (microwave) and 16 (test equipment) — same PD class as Module 10, same Commons/maritime.org pattern, unfetched.

**Transport:**
- KDDI is unlicensed + single fragile host. Lead: mirror tarballs at build start; fallback SMD/Loghub already in tree.
- In-PDF numbers unextracted: G.8032 50 ms switch target, Y.1541 class tables, G.826 ES/SES definitions. Lead: ITU dologin_pub direct-PDF pattern proven this session on G.8272/G.8271.1 — apply to all three at build.
- Cambium ITU-R P.530/P.837 rain-fade math still snippet-sourced (guide PDF >10 MB fetch cap). Lead: full download of the wp-content PDF at build; drop the entry if unconfirmed.
- No open real fiber-cut incident feed (FCC NORS is confidential; ENISA aggregates). Lead: AFL rates + ENISA priors are the ceiling — accept and label.

---

### 5. Unverified / dropped

**Dropped:**

| Item | Reason |
|---|---|
| eltek.com Flatpack2 spec page | DEAD — 301 to delta-emea.com then 404 (brand absorbed by Delta); struck from rectifier entry |
| Delta filecenter Flatpack2 manual | 302 to terms-of-use gate; content unretrievable — do not cite |

**Unverified (kept, labeled — do not treat as confirmed):**

| Item | Status / what was tried |
|---|---|
| RUS 1751E-302 content (36-pp claim, tables) | Official URL WebSearch-confirmed; body 403s all automated fetch — verify on first browser-UA download |
| KDDI tarballs (bytes + license) | wget URLs from official challenge repo; HEAD denied by sandbox; NO license text — never commit |
| NASA battery S3 zip (bytes) | Direct download link on PHM page; curl denied by sandbox both sessions |
| Loghub license | Zenodo CC BY 4.0 vs README "research or academic" — conservative fetch-at-build stands |
| SMD data license | MIT-by-inclusion inference, no separate data license |
| Cambium guide content (ITU-R P.530/P.837) | PDF responds publicly but >10 MB fetch cap; docs portal is login-gated — PLAUSIBLE only |
| G.8032 50 ms protection-switch target | Inside-PDF claim; metadata page verified only |
| MIL-HDBK-419A "812 pp / 2 vols"; Vol II | Only Vol I fetched (5 MB) |
| UFC 3-520-05 body ref to MIL-HDBK-411B | Front matter read only |
| fcc.gov CenturyLink $16M / T-Mobile $17.5M pages | Title-confirmed only; fcc.gov HTML timed out previously |
| Asentria $150–600, eBay Flatpack2, wholesalebatteries EnerSys | Search-seen only, never fetched |
| Uptime 2026 edition | Press coverage only |
| TM 5-692-1 companion volume | Direct link confirmed; PDF + rights page unread — check before commit |
| ecfr.gov canonical 47 CFR 4.9 / armypubs canonical TM 5-685 | Bot-walled / not attempted; both verified via Cornell LII and WBDG respectively |
| CENIC 24×7 staffing; OSHA 3877 program elements 6–7 | Not in fetched page text / past pages read |
| Microsemi 8 h/16 h holdover values | Chart-read approximations, not text-stated |

**Corrections already applied to entries above (trust the tables here, not earlier drafts):** Verizon EMEA is in the 99% delivery group; CenturyLink full restoration 11:36 pm Dec 28; NAB realKnownCause = 7 datasets; Milan = 61 files; TM 5-692-2 has ≥24 chapters; MIL-HDBK-419A must be cited at its NIBS S3 URL (wbdg.org path serves an HTML shell); Kaelus URL UUID fixed; O*NET is CC BY 4.0, not bare PD; TM 5-693 needs IEEE tables + vendor-photo pages stripped pre-commit.


---

## WAVE 3 — Multilingual + missed veins + gap fills

51 entries, all URL-verified this session. Family codes: PWR power/energy · ENV environment · RF radio · TRA transport. Rights: **commit** (safe in public repo) · **fetch** (fetch-at-build, never commit) · **link** (link-only).

### 1. Corpus at a glance

| Title | Publisher | Lang | Family | Rights | Visual | Grounding use |
|---|---|---|---|---|---|---|
| **A. French open data + power docs** | | | | | | |
| [Enedis — Fréquence moyenne de coupure BT](https://opendata.enedis.fr/datasets/frequence-moyenne-de-coupure-par-client-bt) | Enedis | FR | PWR | commit | Med (tables) | Real French grid-outage baseline rates for Cost/Impact |
| [ANFR — installations radioélectriques >5W](https://www.data.gouv.fr/datasets/donnees-sur-les-installations-radioelectriques-de-plus-de-5-watts-1) | ANFR / data.gouv.fr | FR | RF, TRA | commit | Low (CSV) | Demo site = a REAL Paris cell site; coords feed Dispatch |
| [INRS ED 6120 — charge des batteries au plomb](https://www.inrs.fr/media.html?refINRS=ED+6120) | INRS | FR | PWR, ENV | fetch | High (hazard-zone diagrams) | FR hydrogen/explosion safety steps for battery work orders |
| [RTE — Bilans sûreté 2021–2024](https://www.rte-france.com/donnees-publications/publications/bilans-surete) | RTE | FR (+EN) | PWR | fetch | High (incident curves) | Authentic French grid-loss failure chains for Root-Cause |
| [Schneider Cahier Technique n°199 — qualité de l'énergie](https://sti.eduscol.education.fr/sites/eduscol.education.fr.sti/files/ressources/techniques/3361/3361-ct199.pdf) | Schneider (eduscol mirror) | FR | PWR | fetch | Very high (curves, one-lines) | Voltage-dip/outage root causes; top bilingual beat candidate |
| [ARCEP — Mon Réseau Mobile](https://www.data.gouv.fr/datasets/mon-reseau-mobile) | ARCEP | FR | RF, TRA | commit | Med (CSV/maps) | Cell-down impact scoring (users/service lost at demo site) |
| [Saft Tel.X battery documentation](https://saft4u.saft.com/en/product/telx-nickel-battery-grid-telecom-networks) | Saft | EN/FR/IT/PT/ES/RU | PWR | fetch | High (discharge tables) | Degraded-battery specs from a French maker; multilingual docs |
| [Legrand — Guide NF C 15-100 (rév. 2024)](https://assets.legrand.com/editorial/legrandfr/outils/documentations-et-guides/legrand-guide-norme-nf-c-15-100.pdf) | Legrand | FR | PWR | fetch | High (tables, pictograms) | FR breaker/earthing vocabulary + norm citations (residential caveat) |
| **B. EU regulators + resilience** | | | | | | |
| [ENISA Telecom Security Incidents 2024](https://www.enisa.europa.eu/sites/default/files/2025-07/ENISA_Telecom_Security_Incidents_2024_en_1.pdf) | ENISA | EN | PWR, ENV, TRA | commit (CC BY 4.0) | High (charts) | THE impact stats + root-cause priors (see table 2) |
| [CIRAS statistics tool](https://ciras.enisa.europa.eu/) | ENISA | EN | multi | link | Interactive | Pitch screenshot; public view showed managers-only notice — recheck |
| [BEREC BoR (25) 36 — network resilience workshop](https://www.berec.europa.eu/system/files/2025-03/BoR%20%2825%29%2036%20Report_Workshop%20on%20Network%20Resilience.pdf) | BEREC | EN | PWR, ENV, TRA | fetch | Low (prose) | Recovery playbooks: A1 Slovenija flood, 1-day roaming deal |
| [BNetzA Strategiepapier Resilienz (2022)](https://www.bundesnetzagentur.de/DE/Fachthemen/Telekommunikation/Resilienz/Strategiepapier_Resilienz.pdf?__blob=publicationFile&v=1) | BNetzA + BSI | DE | PWR, ENV | fetch | Med (mapping matrix) | "Power loss = biggest threat" verbatim; German retrieval beat |
| [Arcep — Réseaux du futur note n°2, résilience (mai 2025)](https://www.arcep.fr/uploads/tx_gspublication/reseaux-du-futur_note-synthese_resilience-des-reseaux_mai2025.pdf) | Arcep | FR | PWR, ENV, TRA | fetch | Med-high (map, matrix, case boxes) | Ciaran 90%-power stat, FR reporting thresholds; the FR content beat |
| [Ofcom Connected Nations 2024](https://www.ofcom.org.uk/siteassets/resources/documents/research-and-data/multi-sector/infrastructure-research/connected-nations-2024/connected-nations-uk-report-2024.pdf?v=386497) | Ofcom | EN | PWR, TRA, RF | fetch (browser UA) | Med (unseen — bot-blocked) | UK incident volume 1,523/yr for Impact pitch |
| [Ofcom Mobile RAN power resilience (Feb 2025)](https://www.ofcom.org.uk/siteassets/resources/documents/consultations/category-1-10-weeks/272921-resilience-guidance-and-mobile-ran-power-back-up/associated-documents/mobile-ran-power-resilience-technical-report-cfi-update.pdf?v=390945) | Ofcom | EN | PWR | fetch (browser UA) | Med (unseen) | Battery-backup economics; 999-call stats |
| **C. Vintage Bell System / public domain** | | | | | | |
| [BSP Div 157 — Storage Batteries archive](https://www.telecomarchive.com/docs/bsp-archive/157/) | AT&T via telecomarchive | EN | PWR | fetch | High (Tables A–K, forms) | Battery float/discharge/replacement criteria, sulfation diagnosis |
| [BSP Div 167 — Power Plants archive](https://www.telecomarchive.com/docs/bsp-archive/167/) | AT&T/Lucent/Lineage | EN | PWR | fetch | High (~280 scanned manuals) | −48V plant alarms + Galaxy plant user guides |
| [BSP Div 169 — Rectifiers archive](https://www.telecomarchive.com/docs/bsp-archive/169/) | AT&T | EN | PWR | fetch | High (trouble/voltage tables) | Rectifier fault-symptom-to-voltage diagnosis |
| [PacTel Power Maintenance Notes 1964](https://www.telephonecollectors.info/index.php/browse/bsps-bell-system/index-documents/5456-telephone-power-maintenance-notes-pactel-jan64-bsp-sd-ref-ocr-r2) | PacTel via TCI | EN | PWR | fetch | High (OCR chart tables) | Plant-type ontology + BSP/SD cross-index |
| [BSTJ 1977 — No. 4 ESS System Power (+ collection)](https://archive.org/details/bstj56-7-1099) | AT&T / archive.org | EN | PWR | fetch | High (block diagrams) | First-principles −48V architecture citations |
| [TM 11-430 Storage Batteries (1942)](https://archive.org/details/TM11-430) | US War Dept | EN | PWR | **commit** (PD) | High (tables/figures) | Committable lead-acid troubles-and-remedies |
| [Pagé, Storage Batteries Simplified (1917)](https://archive.org/details/storagebatterie01paggoog) | Henley / archive.org | EN | PWR | **commit** (PD) | High (plates) | Sulfation first principles; 1917→1985 continuity beat |
| [REA TE&CM Vol. 5 (1980)](https://archive.org/details/telecommunicatio05unit) | USDA REA | EN | TRA | **commit** (gov) | Med-high (line diagrams) | T-carrier span-line + noise-investigation procedures |
| [Montillot, Téléphonie pratique (1893)](https://gallica.bnf.fr/ark:/12148/bpt6k97860277) | BnF Gallica | FR | PWR | link | High (414 engravings) | 1893 French telephony beat; Gallica bot-blocked, browser-check first |
| [Systat vintage rectifier manuals (Lorain, La Marche, Marconi)](https://www.systatnow.com/misc-rectifier) | Systat | EN | PWR | link | High (schematics) | Non-AT&T rectifier symptoms + float/equalize setpoints |
| **D. Datasets + logs** | | | | | | |
| [LogHub](https://github.com/logpai/loghub) | LOGPAI | EN | TRA | fetch | None (raw logs) | Authentic log lines for Watchdog injector (19 datasets) |
| [gCastle PCIC 2021 alarm datasets](https://github.com/gcastle-hub/dataset) | Huawei Noah's Ark | EN | TRA, RF | **commit** (MIT) | Low (CSV) | Ground-truth causal graphs to SCORE Correlation/Root-Cause |
| [ARCEP historiquePannes](https://github.com/ARCEP-dev/historiquePannes) | ARCEP + 4 FR operators | FR | RF, PWR, TRA | fetch | Med (map viewer) | LIVE French site-down CSVs — demo can open on a real outage |
| [RIPE Atlas daily dumps](https://data-store.ripe.net/datasets/atlas-daily-dumps/) | RIPE NCC | EN | TRA | fetch | None | Real latency/loss/jitter distributions for backhaul injector |
| [GNSS Jammertest 2024 dataset](https://zenodo.org/records/15911359) | Univ. Gustave Eiffel | EN | RF | link (GPL) | Low | GPS-timing degradation ground truth |
| [FGI-JSDR Jammertest 2023](https://www.maanmittauslaitos.fi/en/research/research/gnss-specialists/fgi-gnss-jamming-and-spoofing-dataset-repository-fgi-jsdr) | FGI Finland | EN | RF | link | Low | Backup GNSS jamming corroboration |
| [Comprehensive Network Logs](https://zenodo.org/doi/10.5281/zenodo.10492769) | Zenodo | EN | TRA | **commit** (CC-BY) | None | 17-format ingest seed; provenance unverified — label it so |
| [Telecom Italia Milan grid (Nature sdata2015.55)](https://www.nature.com/articles/sdata201555) | TIM / Dataverse | EN (IT data) | RF, TRA | fetch (ODbL share-alike) | Low (heatmaps derivable) | Sleeping-cell traffic baseline + users-affected scoring |
| **E. Multilingual vendor + gov (DE/IT/ES)** | | | | | | |
| [BENNING TEBECHOP SE rectifiers](https://www.benning.de/files/benning/global_content/downloads/10166872_tebechop_se_de.pdf) | BENNING | DE | PWR | fetch | High (spec tables, block diagram) | Rectifier module specs, EN 300132-2 ripple, n+r redundancy |
| [BBK PiB-13 Notstromversorgung (2024)](https://www.bbk.bund.de/SharedDocs/Downloads/DE/Mediathek/Publikationen/PiB/PiB-13-notstromversorgung-unternehmen-behoerden.pdf?__blob=publicationFile&v=10) | BBK | DE | PWR | fetch | Med-high (Ja/Nein checklists) | Genset-failure remediation playbook; 72h fuel-cell autonomy |
| [STULZ Modular-Line DX manual](https://repository.stulz.com/91E4A1B0/Modular-Line+DX-10-0802-d.pdf) | STULZ | DE | ENV | fetch | High (cause/remedy tables pp.57–72) | HVAC alarm dictionary: airflow loss, refrigerant low-pressure, compressor |
| [Riello Sentinel Dual SDU 5000-10000 manual](https://www.riello-ups.it/uploads/file/872/1872/0MNSDU5K0RUITUB__MAN_SDU_5000-10000_IT_.pdf) | Riello | IT | PWR | fetch | Very high (wiring diagrams, icon tables) | UPS/battery fault validation from panel-observable evidence |
| [ISCOM — sicurezza delle reti nelle infrastrutture critiche](https://www.mimit.gov.it/images/stories/recuperi/Comunicazioni/pub_003_ita.pdf) | ISCOM / MIMIT | IT | TRA, PWR | fetch | Med (prose) | Grid→telecom interdependency narratives for Correlation |
| [REE — Incidente 28 abril 2025 (Iberian blackout)](https://d1n1o4zeyfu21r.cloudfront.net/WEB_Incidente_SistemaElectricoPeninsularEspanol_18junio2025.pdf) | Red Eléctrica | ES | PWR, TRA | fetch | High (400kV voltage charts, timeline) | Nationwide-grid-loss alarm-storm backdrop, minute-by-minute |
| **F. Gap fill 1 — radio thermal specs (FCC exhibits)** | | | | | | |
| [Baicells NeutrinoE224 user manual (FCC)](https://fcc.report/FCC-ID/2AG32PBS42020/7861844.pdf) | Baicells / fcc.report | EN | ENV, RF | fetch | High (54 spec tables, LED matrix) | **THE 45°C indoor thermal threshold** — replaces link-only V9 |
| [Baicells Nova-436Q install guide (FCC)](https://fcc.report/FCC-ID/2AG32MBS3100196N/4816753.pdf) | Baicells | EN | ENV, PWR, RF | fetch | Very high (mount/grounding diagrams) | Outdoor −40..+55°C contrast; +42–60V DC window; VSWR LED |
| [Baicells Nova430i quick guide (FCC)](https://fcc.report/FCC-ID/2AG32PBS3101S/5310036.pdf) | Baicells | EN | ENV, PWR | fetch | High (cabling schematic) | PoE++ power chain = second failure surface; 2nd outdoor datapoint |
| [Baicells Nova436Q datasheet](https://baicells.com/download/Nova436Q%20Datasheet.pdf) | Baicells | EN | ENV | fetch (TLS caveat) | Spec one-pager | Vendor corroboration of −40..+55°C; drop to link if TLS fails |
| **G. Gap fill 2 — named RAN alarm dictionaries** | | | | | | |
| [Ruckus LTE Alarms + Event List (online docs)](https://docs.cloud.ruckuswireless.com/LTE/GUID-E1EEA9B6-9DFA-44AE-9211-FD3821AA1D85.html) | RUCKUS/CommScope | EN | RF, ENV, TRA | fetch | Med (HTML tables) | Named CBRS alarms w/ ID, cause, action (IDs 101–914) |
| [Ruckus LTE AP Management User Guide 2019.01](https://docs.cloud.ruckuswireless.com/LTE/ruckuscloud-201901-lte-onlinehelp.pdf) | RUCKUS/CommScope | EN | RF, ENV, TRA | fetch | High (alarm chapter pp.163–184) | 30 named alarms in one ingest PDF with page numbers |
| [Alcatel-Lucent 5620 SAM Alarm Reference R10.0](https://documentation.nokia.com/cgi-bin/dbaccessfilename.cgi/3HE06980AAAETQZZA01_V1_5620%20SAM%20Release%2010.0%20R5%20Alarm%20Reference.pdf) | ALU/Nokia | EN | RF, TRA | fetch | High (510+ alarm tables, ch.21) | THE per-alarm cause→action matrix: eNodeB, microwave, site router |
| **H. Gap fill 3 — transport equipment docs** | | | | | | |
| [SAF Tehnika Integra FODU manual (FCC)](https://fcc.report/FCC-ID/W9Z-INTEGRA5G8/6829870.pdf) | SAF Tehnika | EN | TRA, PWR | fetch | High (threshold matrix p.88) | Microwave alarm semantics, Set/Reset log, CLI diagnostics |
| [Cambium PTP 820 User Guide R10.9](https://www.cambiumnetworks.com/wp-content/uploads/2019/09/PTP-820-User-Guide_phn-3963_008v001.pdf) | Cambium | EN | TRA | fetch (browser UA) | High | Microwave radio config + troubleshooting paths |
| [Cambium PTP 820 MIB Reference R10.9](https://www.cambiumnetworks.com/wp-content/uploads/2019/09/PTP-820-Series-MIB-Reference-Guide_phn-3974_008v001.pdf) | Cambium | EN | TRA | fetch (browser UA) | High (alarm tables Ch.7 p.51) | Transport alarm dictionary w/ corrective actions |
| [Cisco ASR 920 System Messages](https://www.cisco.com/c/dam/en/us/td/docs/routers/asr920/syslogs/ASR920-SysMsgs.pdf) | Cisco | EN | TRA | fetch (browser UA) | Med-high | Real syslog grammar (%LINK-3-UPDOWN) for site-router failure |
| [Cisco ASR 920 Troubleshooting Aids](https://www.cisco.com/c/en/us/td/docs/routers/asr920/hardware/installation/guide-20SZ-M/b-asr-920-20SZ-M/troubleshooting_aids.pdf) | Cisco | EN | TRA, ENV, PWR | fetch (browser UA) | High (LED/alarm tables) | Router-level remediation + env voltage/temp thresholds |

Local verified copies already on disk (copy into fetch cache, do NOT commit): Ruckus 2019.01 PDF, ALU 5620 SAM PDF, SAF Integra PDF — paths in session tool-results dir `...\4bbefac1-...\tool-results\` (webfetch-1783165628533-3phu5v.pdf, webfetch-1783165657568-ol9mo8.pdf, webfetch-1783165391943-0i640u.pdf).

### 2. Key real numbers (session-verified, cite these exactly)

| Stat | Value | Year | Source |
|---|---|---|---|
| **★ BEST IMPACT-PITCH STAT: EU telecom user-hours lost** | **1,743 MILLION user-hours across 188 incidents (a record year, +20.5% vs 156 in 2023)** | 2024 | [ENISA 2024 report](https://www.enisa.europa.eu/sites/default/files/2025-07/ENISA_Telecom_Security_Incidents_2024_en_1.pdf) — CC BY 4.0, read page-by-page |
| Power cuts as incident cause | 11% of ALL EU incidents; 21 incidents; 252M user-hours | 2024 | ENISA, Fig 10/26 |
| Power supplies hit by natural phenomena | 44% of natural-phenomena incidents (vs 25% in 2023); backup power 12% | 2024 | ENISA p.20 |
| System failures share | 60% of incidents (113; 548M user-hours) | 2024 | ENISA |
| Cumulative EU incidents | 1,930 (2012–2024) | 2024 | ENISA / CIRAS |
| **Best root-cause-validation stat (and it's French): Storm Ciaran** | 90% of down mobile sites = electricity shortage; 10% = antenna desorientation/access | Nov 2023 | [Arcep note, p.20](https://www.arcep.fr/uploads/tx_gspublication/reseaux-du-futur_note-synthese_resilience-des-reseaux_mai2025.pdf) |
| Storm Alex dispatch constraints | 85 km roads swept away, 12 bridges destroyed; sites restarted on grid return | 2020 | Arcep note, p.18 |
| EU climate-caused losses | 168M user-hours (vs 41M in 2021) | 2022 | ENISA 2022, cited Arcep note p.17 |
| UK incident volume | 1,523 resilience incidents Sep 2023–Aug 2024 (+26% vs 1,209) | 2024 | [Ofcom Connected Nations 2024](https://www.ofcom.org.uk/siteassets/resources/documents/research-and-data/multi-sector/infrastructure-research/connected-nations-2024/connected-nations-uk-report-2024.pdf?v=386497) |
| UK battery-backup economics | ~£1bn for up-to-4h emergency-service access (2025 update of £0.9–1.8bn/1h 2023 estimate) | 2025 | [Ofcom RAN power report](https://www.ofcom.org.uk/siteassets/resources/documents/consultations/category-1-10-weeks/272921-resilience-guidance-and-mobile-ran-power-back-up/associated-documents/mobile-ran-power-resilience-technical-report-cfi-update.pdf?v=390945) |
| Emergency-call dependence | 41.9M 999/112 calls in 2023; 79% from mobile | 2023 | Ofcom RAN power report (NOT Connected Nations — misattribution corrected) |
| Iberian blackout | "un cero en el sistema eléctrico español" at 12:33:24 | 28 Apr 2025 | [REE incident report](https://d1n1o4zeyfu21r.cloudfront.net/WEB_Incidente_SistemaElectricoPeninsularEspanol_18junio2025.pdf) |
| German regulator verdict | "Ausfall der Energieversorgung [ist] die größte Bedrohung für die Netze" | 2022 | [BNetzA Strategiepapier p.10](https://www.bundesnetzagentur.de/DE/Fachthemen/Telekommunikation/Resilienz/Strategiepapier_Resilienz.pdf?__blob=publicationFile&v=1) |
| French reporting thresholds | Outage >4h affecting ≥100k subs → COGIC; emergency numbers >2h → report; 70% of FR antenna sites towerco-held | 2025 | Arcep note, Annexe 2 + fn.7 |
| Demo run #2 thermal threshold | Indoor radio operating limit −5°C to +45°C (outdoor contrast: −40..+55°C) | 2023 | [Baicells NeutrinoE224 FCC manual, Sec 1.4.6 p.6](https://fcc.report/FCC-ID/2AG32PBS42020/7861844.pdf) |

Note: ENISA's own report is internally inconsistent on faulty-software user-hours (515M exec summary vs 524M Fig 10/Ch.6). Cite 524M with the figure reference.

### 3. The bilingual demo beat (French page ← English query)

Pick one of these two. Both are session-verified page-by-page.

1. **INRS ED 6120, hazard-zone diagram page** ([PDF](https://www.inrs.fr/dam/inrs/CataloguePapier/ED/TI-ED-6120.pdf)). English query: *"hydrogen explosion risk when charging lead-acid batteries — safety steps"*. Why it wins: it lands INSIDE the demo's degraded-battery remediation path (not a bolt-on), the retrieved page is a French national-safety-institute diagram with explosive-atmosphere zones — visually unmistakable as "not English, still nailed it" — and the stakes are safety-critical, which judges feel. The Remediation agent puts French safety prescriptions into an English work order, citation trail shows the French page image.
2. **Schneider Cahier Technique n°199, voltage-dip pages** ([PDF](https://sti.eduscol.education.fr/sites/eduscol.education.fr.sti/files/ressources/techniques/3361/3361-ct199.pdf)). English query: *"root causes of voltage dips and short interruptions"*. Why: highest visual density in the FR corpus (curves, tables, one-line diagrams — exactly what a visual late-interaction retriever is in-distribution for), and it grounds the −48V/AC-input anomaly ranked cause in the flagship power scenario.

Honorable mention if content beats visuals: **Arcep note mai 2025, p.20 Ciaran box** — English query *"why do cell sites go down after a storm"* returns a French regulator page saying 90% of down sites were power shortage. That single French sentence IS Arc's power-first ranking argument, from the regulator headquartered in the judging city. Prose-in-a-box, less schematic — use it in the pitch narration even if not as the retrieval beat.

### 4. Critic gaps — honest closure status

| Gap | Status | Detail |
|---|---|---|
| 1. Demo run #2's 45°C threshold stood on link-only "Nokia confidential" reseller draft (V9) | **CLOSED** | Baicells NeutrinoE224 FCC exhibit, Sec 1.4.6 p.6: indoor radio, −5..+45°C, downloaded + read page-by-page. ACTION: swap V9's citation now; optionally cite Nova-436Q (−40..+55°C outdoor) in the same answer to show indoor/outdoor reasoning. Residual: NO rights-clean doc states auto-shutdown/derating behavior — demo copy must say "exceeds the manufacturer's rated 45°C maximum," not "documented auto-shutdown at 45°C." Nokia FCC vein is dead (all user manuals filed confidential). Multilingual bonus not achieved (all 4 entries EN). |
| 2. No named RAN alarm dictionary (only X.733/3GPP frameworks) | **CLOSED** | ALU 5620 SAM Alarm Reference ch.21: 510+ eNodeB alarms with probable cause → remedial action, verbatim entries extracted (ENBEquipmentDown 1360; IK4006080 VSWR → "replace the RFM"; IK4001002 TMA → "reset, then replace"). Plus Ruckus: 30 named CBRS alarms (Temperature Critical 101, LTE Radio OpState Disabled 105, Loss of Sync Sources 108). Watchdog recipe: Ruckus names for AP layer, IK4006xxx/ENBEquipmentDown for macro layer. Residual: no French RAN dictionary; Huawei (login-walled) and Baicells (TLS-broken) veins dead. |
| 3. Transport family had zero vendor equipment docs (no microwave manual, no site-router doc) | **CLOSED, with a verification asterisk** | Detect cell: SAF Integra alarm pages read verbatim (threshold matrix p.88) + Cisco syslog grammar (%LINK-3-UPDOWN confirmed). Remediate cell: Cambium MIB per-alarm corrective actions (Ch.7 p.51 per Cambium's own KB) + Cisco Troubleshooting Aids + SAF CLI commands. Asterisk: SAF is fully verified (PDF in hand); the 4 Cambium/Cisco docs are search-confirmed only — both vendors WAF-block bots (403/404). Italian SIAE multilingual bonus NOT achieved (manuals login-gated). |

### 5. Unverified / dropped

**Dropped (do not cite):**
- studiecd.dk Schneider catalogue link — HTTP 403, struck.
- Ericsson/Huawei alarm docs on scribd/pdfcoffee/idoc.pub — rights-unusable mirrors, dropped per hard constraint.
- winncom.com Nova436Q datasheet mirror (403 + reseller-hosted), img.baicells.com CDN copy (expired TLS cert).
- Nokia AirScale FCC user manuals (2AD8U/VBN grantees) — filed confidential, no PDFs exist. Vein dead; don't send anyone back.

**Unverified (needs a browser or a build-time check before citing):**
- Moncloa "28-A" government blackout report — no direct URL confirmed.
- Baicells CloudCore + BaiBLN config guides — baicells.com TLS handshake fails from harness; Wayback snapshot exists but archive.org blocked here.
- SIAE ALFOplus2 ANATEL manual (fccid.io 403); no public Italian microwave alarm manual found at all.
- Cambium PTP 820G guide phn-3965 (404 to bots), Cisco IOS XE 3.18S alarm chapter (title-only match).
- Gallica page-level download (bot-blocked; Internet Archive mirror of Montillot may be a committable alternative — check its rights mark).

**Sub-claims stripped from surviving entries (entry stays, number doesn't):** PCIC "35,000 events/8 months" (unpinned to any primary source); LogHub "48k downloads" and "23 datasets" (README says 19); network-logs "18 CSVs"/"53.8MB" (17 CSVs, size not shown); Telecom Italia "100×100 grid" (garbled extraction — ~235m cell size is the confirmed number); ANFR "5 tables"/"weekly updates"; RTE "Article 28" basis; ENISA cover photo is © Shutterstock (strip cover if committing strictly); BBK "85 samples/74 plants" chart; STULZ "A/G/GE unit types"; REE "0.2Hz" oscillation figure (page-unsighted); Ofcom per-MNO battery variation.

**Build-day fetch warnings:** Ofcom, Cisco, Cambium, fccid.io all 403 plain HTTP clients — the fetch-at-build script MUST send a real browser user-agent. web.archive.org is not reachable from this harness as fallback. Use https for STULZ. Pair the REE CloudFront URL with the ree.es press-note landing page in case the CDN object rotates.
