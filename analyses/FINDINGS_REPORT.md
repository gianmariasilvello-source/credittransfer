# PubMed H-Index Ranking Analysis: Main Findings

**Date:** March 13, 2026  
**Dataset:** PubMed author h-index rankings computed at four retention rates (r=1.0, 0.75, 0.50, 0.25)  
**Baseline:** r=1.0 (no transitive credit transfer — only direct citations count)

---

## 1. Executive Summary

Lowering the retention rate redistributes credit transitively through the
citation graph.  When r=1.0, an author's h-index depends only on direct
citations to their papers.  As r decreases, credit flows further along
citation chains, rewarding authors whose work forms the **foundational
knowledge** on which later influential research is built.

The core finding is asymmetric: **the vast majority of authors lose h-index
under transitive transfer, but a small minority gains substantially**.
Those gainers are precisely the authors whose papers are not necessarily
highly cited themselves, but are cited by papers that become highly cited —
they are the builders of intellectual infrastructure.

| Variation | Authors in common | Gainers | Losers | Unchanged | Mean Δh | Max gain | Max loss |
|-----------|------------------:|--------:|-------:|----------:|--------:|---------:|---------:|
| r=1→0.75 | 476,286 | 52,683 (11.1%) | 358,525 (75.3%) | 65,078 (13.7%) | −1.5 | +29 | −14 |
| r=1→0.50 | 454,959 | 47,899 (10.5%) | 385,661 (84.8%) | 21,399 (4.7%) | −3.7 | +62 | −30 |
| r=1→0.25 | 418,240 | 29,827 (7.1%) | 381,327 (91.2%) | 7,086 (1.7%) | −8.3 | +96 | −65 |

As the retention rate decreases:
- The proportion of authors who **gain** shrinks (11.1% → 7.1%), but the
  magnitude of the gain for the top gainers **grows dramatically** (+29 → +96).
- The proportion of authors who **lose** grows (75.3% → 91.2%), with losses
  also deepening (−14 → −65).
- The set of "unchanged" authors nearly vanishes (13.7% → 1.7%), meaning
  almost every author is affected at r=0.25.

---

## 2. Ranking Disruption: Correlations with the Baseline

The rank correlations between the baseline ranking (r=1.0) and each variation
quantify how much the ranking is reshuffled.

| Variation | Cutoff | N | Spearman ρ | Kendall τ | W-Kendall τ |
|-----------|--------|--:|----------:|----------:|------------:|
| r=1→0.75 | Top-10 | 11 | 0.782 | 0.600 | 0.553 |
| r=1→0.75 | Top-100 | 112 | 0.889 | 0.719 | 0.645 |
| r=1→0.75 | Top-1,000 | 1,099 | 0.903 | 0.738 | 0.643 |
| r=1→0.75 | Top-10,000 | 10,737 | 0.938 | 0.792 | 0.724 |
| r=1→0.50 | Top-10 | 13 | 0.198 | 0.179 | 0.141 |
| r=1→0.50 | Top-100 | 127 | 0.596 | 0.412 | 0.294 |
| r=1→0.50 | Top-1,000 | 1,237 | 0.661 | 0.475 | 0.380 |
| r=1→0.50 | Top-10,000 | 11,647 | 0.762 | 0.573 | 0.494 |
| r=1→0.25 | Top-10 | 18 | **−0.410** | **−0.216** | −0.226 |
| r=1→0.25 | Top-100 | 148 | 0.093 | 0.051 | −0.039 |
| r=1→0.25 | Top-1,000 | 1,402 | 0.246 | 0.162 | 0.063 |
| r=1→0.25 | Top-10,000 | 13,014 | 0.450 | 0.311 | 0.221 |

**Key observations:**

- At r=0.75, the ranking is still largely preserved (Spearman ~0.90 at
  Top-1,000), indicating that mild transitive credit does not drastically
  alter the landscape.
- At r=0.50, the disruption becomes substantial. The Top-10 correlation
  drops to just 0.20 — the elite are already being reshuffled.
- At r=0.25, the **Top-10 correlation is negative** (ρ = −0.41): the
  baseline top-10 and the r=0.25 top-10 are essentially anti-correlated.
  The Top-100 is near zero (ρ = 0.09). This is a complete ranking
  overhaul at the top.
- Notably, N grows with lower retention (from 11 to 18 for Top-10) because
  different authors enter the top when the ranking changes; the union of
  both top-10 sets contains 18 distinct authors.
- The weighted Kendall τ (which emphasizes top positions) is consistently
  *lower* than the standard Kendall τ, confirming that disruption is
  greatest at the very top of the ranking.

---

## 3. What Happens to the Top-10 Authors

The baseline top-10 are the most highly cited PubMed authors. Their fate
under transitive credit transfer is revealing.

### r=1.0 → r=0.75 (mild transitivity)

| Rank | Author ID | h@1.0 | h@0.75 | Δh | ΔRank | Pubs |
|-----:|----------:|------:|-------:|---:|------:|-----:|
| 1 | 2909828 | 288 | 298 | +10 | 0 | 2,173 |
| 2 | 2036634 | 252 | 261 | +9 | 0 | 927 |
| 3 | 3118255 | 252 | 255 | +3 | −2 | 584 |
| 4 | 3905565 | 249 | 252 | +3 | −2 | 1,253 |
| 5 | 6558419 | 248 | 257 | +9 | +1 | 849 |
| 6 | 9772016 | 245 | 243 | **−2** | −3 | 2,466 |
| 7 | 6795552 | 245 | 261 | +16 | +4 | 1,273 |
| 8 | 8784928 | 242 | 251 | +9 | +1 | 735 |
| 9 | 11384487 | 241 | 238 | **−3** | −2 | 1,653 |
| 10 | 3566237 | 235 | 239 | +4 | 0 | 1,805 |

At mild transitivity, most top authors **gain slightly**. Authors 9772016
and 11384487 already show a small loss, hinting that their citation impact
is more "terminal" — they receive citations but are not as strongly cited
via chains of influence.

### r=1.0 → r=0.25 (strong transitivity)

| Rank | Author ID | h@1.0 | h@0.25 | Δh | ΔRank | Pubs |
|-----:|----------:|------:|-------:|---:|------:|-----:|
| 1 | 2909828 | 288 | 274 | −14 | −2 | 2,173 |
| 2 | 2036634 | 252 | 245 | −7 | −9 | 927 |
| 3 | 3118255 | 252 | 238 | −14 | −9 | 584 |
| 4 | 3905565 | 249 | 228 | **−21** | −15 | 1,253 |
| 5 | 6558419 | 248 | 246 | −2 | −4 | 849 |
| 6 | 9772016 | 245 | 195 | **−50** | −47 | 2,466 |
| 7 | 6795552 | 245 | 238 | −7 | −6 | 1,273 |
| 8 | 8784928 | 242 | 236 | −6 | −8 | 735 |
| 9 | 11384487 | 241 | 185 | **−56** | −72 | 1,653 |
| 10 | 3566237 | 235 | 198 | **−37** | −39 | 1,805 |

Under strong transitivity, **every baseline top-10 author loses h-index**.
The losses range from −2 to −56.  The most striking cases are:
- **Author 9772016** (h: 245 → 195, Δ = −50): falls from rank 6 to rank 53.
  This author has 2,466 publications — the highest pub count in the top-10 —
  yet loses most h-index. This suggests their papers are heavily cited
  directly but do not serve as foundational references for other impactful
  work.
- **Author 11384487** (h: 241 → 185, Δ = −56): the largest loser among the
  top-10, falling 72 rank positions. With 1,653 publications, this author's
  citation impact is concentrated at the "leaves" of the citation graph.
- **Author 6558419** (h: 248 → 246, Δ = −2) is the most resilient: almost
  unchanged, suggesting their work propagates influence effectively through
  citation chains.

---

## 4. Biggest Gainers and Losers

### Top Gainers at r=0.25

| Author ID | h@1.0 | h@0.25 | Δh | Rank@1.0 → Rank@0.25 | Pubs |
|----------:|------:|-------:|---:|----------------------:|-----:|
| 122408 | 101 | 197 | **+96** | 3,066 → 50 | 534 |
| 593164 | 105 | 200 | **+95** | 2,520 → 44 | 410 |
| 4055467 | 73 | 168 | **+95** | 13,664 → 147 | 510 |
| 10033469 | 73 | 163 | +90 | 13,555 → 165 | 549 |
| 9737076 | 130 | 218 | +88 | 730 → 25 | 1,549 |
| 101090 | 209 | 296 | +87 | 29 → 1 | 782 |
| 10499811 | 72 | 157 | +85 | 14,518 → 200 | 399 |
| 8772248 | 126 | 210 | +84 | 899 → 33 | 1,051 |
| 11324641 | 84 | 168 | +84 | 7,513 → 146 | 731 |
| 751135 | 111 | 191 | +80 | 1,831 → 69 | 1,199 |

These authors experience **massive rank leaps**:
- Author 122408 jumps from rank 3,066 to rank 50 — a leap of 3,016
  positions — with only 534 publications.
- Author 4055467 (h=73, modest by top standards) jumps from rank 13,664 to
  rank 147 — nearly 100× closer to the top.
- **Author 101090 becomes #1 at r=0.25** (h: 209 → 296). Already ranked
  29th at baseline, this author's work is at the intersection of direct
  impact and transitive influence.

The pattern is clear: **gainers are authors with moderate baseline h-index
(typically 60–130) whose papers are cited by papers that themselves become
highly cited**.  They have moderate publication counts (200–600 typically),
suggesting focused research programs with high downstream influence.

### Top Losers at r=0.25

| Author ID | h@1.0 | h@0.25 | Δh | Rank@1.0 → Rank@0.25 | Pubs |
|----------:|------:|-------:|---:|----------------------:|-----:|
| 5187963 | 234 | 169 | **−65** | 11 → 140 | 1,527 |
| 8879664 | 155 | 96 | −59 | 251 → 2,321 | 1,720 |
| 3829461 | 149 | 90 | −59 | 315 → 3,128 | 2,048 |
| 8693805 | 155 | 97 | −58 | 250 → 2,224 | 2,021 |
| 8122176 | 110 | 52 | −58 | 1,951 → 23,473 | 1,842 |
| 1204811 | 183 | 126 | −57 | 80 → 656 | 1,141 |
| 2049097 | 174 | 117 | −57 | 99 → 942 | 1,853 |
| 11384487 | 241 | 185 | −56 | 9 → 81 | 1,653 |
| 12203369 | 147 | 91 | −56 | 353 → 2,994 | 1,274 |
| 6953248 | 143 | 88 | −55 | 429 → 3,531 | 822 |

Key observations about losers:
- Losers tend to have **high publication counts** (typically 800–2,400),
  much higher than gainers. Author 8122176, for instance, has 1,842
  publications but drops from rank 1,951 to rank 23,473 — a catastrophic
  fall.
- **Author 5187963** (the biggest loser) is the 11th-ranked author at
  baseline with h=234, yet drops to 169 under full transitivity. With
  1,527 papers, this author's citation impact does not propagate through
  chains.
- Losers' high publication output combined with their loss suggests
  **prolific but "terminal" citation profiles**: their papers are cited
  but do not serve as stepping stones for further influential work.

### Consistency across variations

The gainers are remarkably consistent across all three retention rates.
For example, the same author IDs appear at the top of the gainers list for
r=0.75 (Authors 4226882, 1898713, 4101734, 593164), r=0.50 (Authors
101090, 593164, 4101734, 8772248), and r=0.25 (Authors 122408, 593164,
4055467).  The consistent presence of authors like **593164** and
**4101734** across all three variations confirms their role as foundational
contributors.

Similarly, losers are consistent: Authors 12203369, 8693805, 6953248, and
3829461 appear as top losers at every retention level.

---

## 5. Hidden Foundational Authors: Modest H-Index, High Transitive Gain

Perhaps the most interesting finding concerns authors with an unremarkable
baseline h-index who gain disproportionately from transitivity. These are
researchers whose work forms the intellectual foundation for later
breakthroughs. We identify them via the **relative gain** metric
(Δh / h@1.0) at r=0.25, filtered to h@1.0 ≥ 10.

### Authors with the highest relative h-index gain (r=0.25)

| Rank | Author ID | h@1.0 | h@0.25 | Δh | Rel. Gain | Pubs | Kudos Ratio |
|-----:|----------:|------:|-------:|---:|----------:|-----:|------------:|
| 1 | 9143901 | 22 | 80 | +58 | **+263.6%** | 149 | 69.51 |
| 2 | 13645591 | 26 | 84 | +58 | **+223.1%** | 151 | 155.75 |
| 3 | 4578170 | 21 | 67 | +46 | +219.0% | 161 | 20.82 |
| 4 | 3181113 | 27 | 80 | +53 | +196.3% | 134 | 19.19 |
| 5 | 1233086 | 28 | 78 | +50 | +178.6% | 169 | 17.14 |
| 6 | 6080776 | 21 | 58 | +37 | +176.2% | 141 | 22.81 |
| 7 | 2496356 | 21 | 57 | +36 | +171.4% | 121 | 19.39 |
| 8 | 13592447 | 29 | 78 | +49 | +169.0% | 188 | 13.91 |
| 9 | 8929934 | 26 | 69 | +43 | +165.4% | 90 | 35.54 |
| 10 | 13711797 | 28 | 74 | +46 | +164.3% | 1,051 | 4.36 |

These authors are the most striking finding:

- **Author 9143901** has a modest h-index of 22 at baseline — ranking
  somewhere around position 170,000 in the overall list. Under full
  transitivity, their h-index jumps to 80, a **+263.6% increase**. With
  only 149 publications, this author is far from prolific. But their
  papers are cited by papers that become very influential: the kudos
  ratio of 69.5 means the author receives ~70× more total credit under
  transitive transfer.

- **Author 13645591** (h: 26 → 84, +223.1%) is even more extreme in
  terms of kudos: a ratio of 155.75 means their transitive credit is
  over 150× their direct credit. With only 151 publications, this
  author's work is an extraordinary foundational multiplier.

- **Author 8929934** (h: 26 → 69, +165.4%) has only 90 publications
  yet a kudos ratio of 35.5. This is one of the least prolific authors
  in the list, yet their work has enormous transitive reach.

- **Author 13711797** (h: 28 → 74, +164.3%) is unique in having 1,051
  publications — but with a more modest kudos ratio of 4.36. This
  suggests a different profile: a broadly published author whose many
  papers each contribute a small transitive effect that cumulates.

### What the Kudos Ratio reveals

The kudos ratio (total_kudos@r / total_kudos@1.0) measures how much more
total credit an author receives under transitive transfer. For most
authors, this ratio is close to 1 (their credit doesn't change much). For
top gainers, it ranges from 4–156×:

- **Ratios above 20×** (e.g., Authors 9143901, 13645591, 8929934,
  1313321, 9919543, 1814834, 5578349) signal authors whose direct
  citation impact is modest but whose work is deeply embedded in the
  citation chains leading to highly cited papers. These are the
  **"invisible pillars"** of the scientific literature.

- **Ratios of 3–10×** with high absolute gains (e.g., Authors 122408,
  593164, 4055467) indicate a middle ground: already somewhat
  recognized, but whose transitive influence far exceeds their direct
  recognition.

### These authors are consistent across variations

The same hidden foundational authors appear in the relative-gain lists at
all three retention rates:

| Author ID | Rel. gain @0.75 | Rel. gain @0.50 | Rel. gain @0.25 |
|----------:|----------------:|----------------:|----------------:|
| 9143901 | +54.5% (rank 3) | +159.1% (rank 1) | +263.6% (rank 1) |
| 13645591 | +61.5% (rank 1) | +123.1% (rank 3) | +223.1% (rank 2) |
| 6080776 | +42.9% (rank 6) | +123.8% (rank 2) | +176.2% (rank 6) |
| 8929934 | +42.3% (rank 7) | +103.8% (rank 8) | +165.4% (rank 9) |
| 1313321 | +55.6% (rank 2) | +118.5% (rank 4) | +159.3% (rank 15) |

Their transitive benefit is already detectable at r=0.75 and grows
monotonically with deeper transitivity, confirming that it is a genuine
structural property of their position in the citation graph — not an
artifact of a single retention level.

---

## 6. Profile Comparison: Gainers vs Losers

| Property | Gainers | Losers |
|----------|--------:|-------:|
| Mean h@1.0 | 37.2 | 35.1 |
| Mean publications | 132.4 | 127.0 |
| Typical pub range of top-30 | 190–1,549 | 482–2,466 |
| Typical h@1.0 range of top-30 | 48–209 | 108–245 |

At the population level, gainers and losers are not dramatically different
in their baseline metrics. Both have similar mean h-indices (~35–37) and
publication counts (~127–132).

The difference lies in their **structural position in the citation graph**:
- **Gainers** are upstream: their work is foundational — cited by papers
  that go on to be cited again.
- **Losers** are downstream: their work is the terminus of citation chains
  — directly cited but not serving as a springboard for further impact.

This is confirmed by the top-30 extremes:  the biggest losers are
concentrated among the most-published authors (1,000–2,400+ papers),
while the biggest gainers include authors with quite modest output
(190–600 papers) who happen to occupy structurally influential positions.

---

## 7. Summary of Key Takeaways

1. **Transitive credit transfer reshuffles the author ranking dramatically,
   especially at the top.** At r=0.25, the Top-10 correlation with
   baseline is *negative*, meaning the elite is completely overturned.

2. **~91% of authors lose h-index at r=0.25**, but the ~7% who gain
   experience large absolute and relative increases (up to +96 absolute,
   +264% relative).

3. **The biggest gainers are foundational authors** with moderate h-index
   (20–130) and focused publication output (100–600 papers) whose work
   is cited by papers that become highly cited. They are the invisible
   infrastructure of science.

4. **The biggest losers are prolific, highly cited authors** (h>100, often
   1,000–2,500 papers) whose citation impact is "terminal" — they are
   cited directly but do not propagate influence through citation chains.

5. **Author 101090 becomes the #1 ranked author at r=0.25** (h: 209 →
   296), exemplifying the "foundational star" — an already prominent
   researcher whose transitive influence far exceeds even their direct
   impact.

6. **Hidden foundational authors** (h~20–30 at baseline) who more than
   triple their h-index under transitive transfer (e.g., Authors
   9143901, 13645591, 4578170) represent a category of researcher
   that is structurally invisible under traditional bibliometrics but
   essential to the generation of high-impact science.

---

*All data tables referenced in this report are available in
`analyses/tables/` in both CSV and TXT format. Plots are in
`analyses/plots/`.*

