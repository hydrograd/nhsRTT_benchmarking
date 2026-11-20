# How much of a trust's 18-week performance is the trust?

*NHS England RTT full extract, September 2026. All counts are referral-to-treatment pathways, not patients.*

## Question

NHS providers are routinely compared on one number: the share of their incomplete RTT pathways waiting under 18 weeks. In England in September 2026 that share was 65.9%, across 7.1 million pathways.

Ranking providers on this raw rate mixes up three things:

- what the provider does,
- which specialties it treats,
- how much its rate would move by chance at its size.

This analysis asks how much of the variation between providers is left once specialty mix and size are accounted for.

## Data and validation

The source is NHS England's commissioner-based full CSV extract for September 2026. It has 183,346 rows at provider × commissioner × specialty × RTT part, with 105 weekly wait bands.

Before any analysis I checked the file's structural traps and wrote a test for each:

- The "Total" (C_999) rows equal the sum of the specialty rows, so summing both doubles every figure.
- The waiting list is Part_2 only. Part_2A is a subset of it.
- The Part_2 week bands reconcile exactly to `Total All` on every row.

National figures reproduce the published statistics:

- 65.85% within 18 weeks.
- Median wait 12.19 weeks, against 12.2 published.
- 92nd percentile 37.75 weeks, against 37.7 published. It sits on a rounding boundary.

Pathway counts run 0.35–0.43% above the published provider-based figures in every RTT part. Long-wait counts run well above them: 648 pathways over 104 weeks, against 314 published. Half of those 648 come from a single orthopaedic trust. Until I can explain both gaps, I don't quote any 65-, 78- or 104-week figure as a national number.

One data-quality exception turned up. One provider reports more Part_2A pathways than Part_2, which shouldn't be possible.

## Method

**Scope.** I benchmarked the 267 providers with at least 1,000 pathways: 134 NHS trusts and 133 independent-sector or other providers. The two sectors are treated as separate peer groups, because their case mix and referral routes differ.

**Specialty mix: indirect standardisation.** Each provider's expected number within 18 weeks is the sum, over its specialties, of its pathways times the national rate for that specialty. The ratio of observed to expected (O/E), multiplied by the national rate, gives a mix-adjusted rate. England's O/E is exactly 1.

**Size: funnel plots.** Control limits at 95% and 99.8% sit around the national rate and narrow as list size grows.

The textbook binomial limits failed immediately. 119 of 134 trusts fell outside the 99.8% limits, because with lists of around 100,000 the limits are almost zero-width. Real between-trust variation is far larger than sampling noise.

I therefore used Spiegelhalter's additive overdispersion adjustment. It estimates the genuine between-provider variance (τ) within each sector and widens the limits to match. For NHS trusts, τ is about 4.1 percentage points.

## Findings

**1. Once real variation is allowed for, few trusts are statistical outliers.** On overdispersion-adjusted, mix-adjusted limits, 12 NHS trusts are outside the 99.8% band: 10 above and 2 below.

- **Below:** Mid and South Essex (51.6% within 18 weeks) and University Hospitals Sussex (52.0%). Both are below the limits on every version of the analysis.
- **Above:** seven community, mental health and specialist cancer trusts, such as Kent Community Health and The Christie, whose waiting lists are structurally different from acute trusts'. The other three are acute trusts: Northumbria, Royal Berkshire, and Tameside and Glossop.
- **Trusts the naive chart would flag:** 107 of the 119 flagged by the naive binomial chart sit inside the limits once size and mix are properly accounted for.

**2. Specialty mix barely matters for large acute trusts.** Among the 20 largest trusts, the mix-expected rate spans only 64.8% to 66.7%. Their portfolios look alike, so adjusting changes almost nothing: six trusts swap places by one rank and none moves further.

Mix matters for trusts with unusual portfolios. Across all 134 trusts the expected rate ranges from 60.9% to 80.4%.

- Moorfields Eye Hospital drops from 85.6% to 77.5% after adjustment. Royal Papworth drops from 79.3% to 72.4%. Both move back inside the 99.8% limits, because part of their raw advantage is that their specialties are quick nationally.
- Sussex Community and Liverpool Women's rise 40 and 38 places.

**3. Ranks exaggerate small differences.** 54 trusts move five or more places after adjustment, but the underlying rate changes are small. Sussex Community's 40-place jump is a 4-point change. The middle of the distribution is crowded, so a league table turns small, uncertain differences into large apparent ones. The funnel plot shows the same data without that distortion.

A related observation on long waits: they are concentrated. Ten providers hold 36.5% of England's 52-week-plus pathways, and Mid and South Essex alone holds 11.6%. By specialty, trauma and orthopaedics holds 19.3%.

## Limitations

- **Specialty is the only adjustment.** Complexity within a specialty, deprivation, referral thresholds and demand pressure are not adjusted for. So "outside the limits" means "unlikely to be chance", not "failing", and this data cannot say why.
- **One month.** A single snapshot can't separate persistent performance from a temporary backlog. A 12-month series would be needed before judging any trust.
- **Not fully reconciled.** The commissioner-based file runs about 0.4% above the published provider-based figures, and the long-wait tail doesn't reconcile yet. Six trusts, including Sheffield Teaching Hospitals and Nottingham University Hospitals, submitted no data, so national figures exclude them.
- **Pathways, not patients.** 7.1 million pathways are roughly 6.2 million people. Policy claims about "patients waiting" need that conversion.
- **Method choices.** The overdispersion estimate depends on the peer group and the winsorising choice. The independent sector is so heterogeneous (τ ≈ 11–13 points) that its limits are wide and rarely informative.
