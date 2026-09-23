# Post-Listing Underperformance in Cryptocurrency Markets: Evidence from Every Binance USDT Listing, 2021-2026

AUTHORLINE::Said Bakhtiev
AUTHORLINE::Gymnasium of Aznakayevo, Republic of Tatarstan, Russia; mr.saidklick@gmail.com; ORCID 0009-0009-6357-3168

ABSTRACT::Buying a token on the day a major exchange lists it is one of the most persistent folk trades in cryptocurrency markets. We argue that the apparent support is an artifact of how the measurement is built, and rebuild it: every Binance spot USDT listing from January 2021 through July 2026, 470 events, reconstructed point-in-time from raw exchange archives so that delisted tokens are never dropped. The median token loses 11.45% in its first week from the listing-day close and 21.53% in its first month. The median dollar, weighted by day-0 turnover, loses 28.7%, and delisting explains less than one percentage point of that gap. A holdout on 415 Bybit listings, with four predictions frozen in advance, replicates the fade; 566 Coinbase listings reproduce it almost exactly. Announcement timestamps reconstructed from the exchange's own publication API locate the premium before the announcement, on other venues' markets.

KEYTERMS::Cryptocurrency, event study, exchange listings, survivorship bias, dollar-weighted returns.

# I. Introduction

Every few days, a large exchange lists a new token. Volume floods in, and the chart goes vertical. Buying that moment is one of crypto's most persistent folk trades, and the academic literature appears to support it: cross-listings of crypto tokens on major exchanges are followed by large positive average returns around the listing date [1], [2], with announcement-day means of +22-33% documented for Coinbase and Binance [3].

This paper argues that the apparent support is an optical illusion created by how the measurement is built. Two features of standard practice do the damage. One is the sample: data providers and live data feeds (APIs) keep only tokens that still exist, so every coin that died takes its worst outcomes with it. The other is the window: headline event studies straddle the listing date, so the reported number bundles the pre-listing run-up into whatever a buyer can still obtain once trading opens.

We rebuilt the measurement. Every Binance spot listing in USDT (Tether, a dollar-pegged stablecoin) from January 2021 through July 2026 went into the calendar: 470 events from the exchange's raw public archive, with tokens delisted years ago sitting in it exactly like tokens listed last month. Outcomes are anchored where a retail buyer can actually act, at the listing-day close; the weights follow money, not ticker counts; and the inference accounts for the fact that listings cluster in calendar time [4], [5]. The research question is single and measurable: what does a buyer earn who purchases every new Binance USDT listing at its listing-day close, when dead tokens are kept in the sample? To our knowledge, this is the first academic event study of first listings that is death-inclusive, turnover-weighted, and anchored at the buyer-accessible close; industry panels have documented the same fade without these design features [6], [7]. The sign was visible in the literature's own numbers: of the celebrated +9.97% listing-window effect of [2], +5.0 percentage points accrue before the listing day, and the post-opening window turns significantly negative. Underperformance after public issuance is among the oldest anomalies in empirical finance [8]-[10], and its canonical mechanism, divergence of opinion combined with constraints on short selling [11]-[14], predicts exactly the pattern we find.

# II. Methods

## A. Data

Binance publishes monthly archives of daily price candles for every symbol it has ever listed, including symbols delisted years ago. From the archive index (retrieved August 2026) we screened 3,682 symbols, kept the 722 USDT spot pairs, removed 52 leveraged-token suffixes (restoring two false matches, JUP and SYRUP), and kept first listings from January 2021 onward: 470 events. A listing here is the debut of the USDT pair: 59 events traded earlier under another quote currency, and the panel knowingly includes 56 tokenized-stock and 5 stablecoin pairs; removing all 120 leaves every conclusion stronger (Section III). Day-0 turnover in US dollars comes from the first daily candle of each event.

## B. Design

Events are dated at the first trading day (day 0). Forward returns run from the day-0 close to the close k trading days later, for k in {1, 3, 7, 14, 30}, counted in the token's own daily bars so that every event shares one clock from its first print. A first listing has no venue history, so abnormal returns are computed against Bitcoin, the sample's dominant common factor [15], following the market-adjusted model of standard event-study practice [16]. Where a price path ends before a horizon (ten recent listings), the return is marked at the last available close; marking such cases as total losses instead would worsen every estimate.

## C. Inference

Four layers. (i) A cross-sectional t-test. (ii) The Wilcoxon signed-rank test, a rank-based check of whether the typical outcome differs from zero that is robust to a heavy right tail. (iii) A month-block bootstrap that resamples whole listing months 5,000 times, because listing events cluster in calendar time. (iv) Benjamini-Hochberg control of the false discovery rate across the confirmatory family. Layers (i) and (ii) assume independent events and are reported for comparability with the prior literature; the bootstrap layer is the valid one under clustering, and every headline statistic carries its interval. Dollar-typical outcomes are weighted medians with weights equal to day-0 dollar turnover: the smallest value at which cumulative weight reaches 50%, a weighting choice rather than an internal-rate-of-return measure [17].

## D. Pre-specified holdout design

Four directional predictions were written on 2026-08-23 and frozen in version control on 2026-08-24, before any Bybit price data was touched. Three transplant the Binance findings to the Bybit venue and form the multiple-testing family; the fourth, a survivorship decomposition, runs on the Binance panel outside the corrected family. Bybit's API serves price histories only for listed instruments, so the holdout cohort consists of survivors by construction (419 candidates, 415 usable); the limitation is declared upfront.

## E. AI-assistance disclosure

Large-language-model tools (Anthropic Claude agents of the opus-4 and sonnet-4 families and Moonshot Kimi k3, via the ZCode command-line environment, August-September 2026; OpenAI GPT-family models for text checks) assisted code drafting, debugging, literature search, and language editing under the author's direction. Prompts were conversational and task-level (representative: "recompute the week-one turnover-weighted median with a bootstrap interval"). No model generated data or results; the work was designed and directed by the author, who verified every reported number against the released data and code; no AI tool is an author.

# III. Results

## A. The fade

TABLE::TABLE I. Forward returns from the day-0 close (n = 470). Wilcoxon p is the signed-rank test against zero; month-block bootstrap intervals of the medians exclude zero at every horizon.
| Day | Median | Mean | t-stat | Wilcoxon p | %>0 |
|---|---|---|---|---|---|
| +1d | −4.45% | −1.35% | −1.22 | 7.9×10⁻¹³ | 32.6% |
| +3d | −8.87% | −3.44% | −2.21 | 9.98×10⁻¹⁶ | 27.4% |
| +7d | −11.45% | −6.65% | −3.72 | 3.38×10⁻¹⁷ | 28.9% |
| +14d | −14.51% | −9.68% | −4.77 | 8.59×10⁻¹⁹ | 28.9% |
| +30d | −21.53% | −7.29% | −1.71 | 1.03×10⁻¹⁸ | 29.1% |

From the listing-day close the median token loses 4.45% in one day, 11.45% in a week, and 21.53% in a month (Table I, Fig. 1). Mean and median disagree by design: at +30 days the mean (−7.29%) is statistically indistinguishable from zero, because a thin right tail of spectacular winners offsets the typical loss. This lottery structure makes "average listing return" marketing misleading. The drift also settles a piece of trader folklore: the median token bottoms 31.78% below its listing-day close within the first month, so even perfectly timing the bottom leaves a buyer far below the close. A permutation test pooling the forward returns of all events and horizons places the late-horizon medians beyond all 2,000 random draws, whilst the week-one median does not clear the pool (p = 0.06), so the test does not by itself rule out a market-wide post-peak regime.

FIG::../charts/post_listing_drift.png::Fig. 1. Median cumulative return after the listing day. Forward return from the day-0 close over the first 30 trading days, median across the 470 death-inclusive events: −4.45% at +1d, −11.45% at +7d, −21.53% at +30d.

Inside day 0, the median listing gains +30.9% in its first hour and drifts −2.25% into the close; the day's peak is the very first minute bar for the median event (80.4% peak within the first hour), and the first minute closes +38.1% above the open. The frenzy is intensity, not buyer imbalance: a median 3,858 trades per minute print in the first five minutes (13.7× the rest of the day), and the quartile with the busiest first hour fades −21.9% within a week, against −0.7% for the quietest.

## B. Where the money sits

Counting tokens and counting dollars give different answers. The turnover-weighted median week-one return is −28.72% (95% confidence interval (CI) [−39.45, −19.79] from the month-block bootstrap; −35.46% adjusted for Bitcoin's own move), against the token-counted −11.45% (Fig. 2). The dollar-weighted mean, −17.40%, sits far above the median: a thin right tail of winners carries part of the money. Split into day-0 turnover quintiles, the median week-one return runs −0.6%, −5.0%, −14.5%, −16.8%, −23.5% (Fig. 3): the quietest quintile shows no fade at all, and the gradient from quietest to busiest is −22.9 pp (percentage points; CI [−32.6, −13.3]). Turnover keeps incremental predictive power in the cross-section (−2.4 pp per log unit, t = −2.6, with the day-0 pop, day-0 range and first-week volatility controlled), persists in every calendar year, and survives removal of the five heaviest events. This is the listing-day version of the divergence-of-opinion mechanism [11]-[14]: record turnover marks peak attention [18], optimists set the price, and dollars systematically buy that peak.

FIG::../charts/dollar_vs_token.png::Fig. 2. Token-counted versus dollar-counted week-one returns. Median forward week-one return from the day-0 close, counted per token (−11.45%) versus weighted by day-0 dollar turnover (−28.72%).

FIG::../charts/turnover_quintiles.png::Fig. 3. Median week-one return from the day-0 close across day-0 dollar turnover quintiles (n = 470). The fade steepens in day-0 turnover; the quietest quintile shows no fade at all.

## C. Survivorship: bounded here, large elsewhere

Dropping delisted tokens moves the week-one median by only +0.35 pp (bootstrap CI [−1.27, +2.15]); the archive keeps the dead paths, so little hides there. The warning is for samples drawn from live-universe endpoints, where every token that died before sampling disappears entirely: a monthly point-in-time simulation of that sampling rule shifts the equal-weight median by at most ±1.5 pp and never flips the sign, and the dollar-weighted median by at most +1.9 pp, with the vanished share peaking at 23% of the panel. Portfolio studies that compound dead coins out of existence report survivorship inflation of up to 62 pp per year equal-weighted [19]; the two facts reconcile, because their weights are market capitalizations in a buy-and-hold portfolio while ours are day-0 turnover shares in a short event window. The death events themselves close the loop. For the 73 true delistings with a located announcement, the announcement day loses −28.5% at the median, the price halves again from announcement to the last trade (−51.5%), and buying the listing and holding to the grave loses −98.3%. Migration and rebrand notices, the same genre of headline without death, gain +7.9% (76% positive): the reaction is specific to dying. No run-up precedes the delisting announcement: over the two weeks before it, the median event drifts −7.5% (30% positive).

## D. Robustness, and the economics of shorting the fade

The week-one median stays within [−11.52%, −11.31%] under tail trimming, winsorization (capping extreme values at the percentile boundary), and sub-sample exclusions. Excluding the 59 re-pairings and the 61 non-token pairs strengthens every number (clean panel: −14.32% week one, −30.99% month one, weighted median −28.89%). Monetizing the fade is harder than documenting it. Only 17.0% of the panel had a shortable perpetual futures contract on day 0 (44.7% within week one); median week-one funding, the periodic transfer between longs and shorts (negative here, i.e. paid by shorts), is −0.36% against the −11.45% drift; and where a contract existed from day 0 the short did pay (median +25.6% on the twelve most-traded such names). But that is a selected slice: venues list contracts first on the hottest names, which fade hardest, and funding itself carries the hype signature (Spearman rank correlation ρ = +0.16, p = 0.016).

## E. Dating the announcements, and where the premium sits

The exchange's own content API returns a millisecond-precision publication timestamp for each of 2,255 catalogue articles back to 2017; matching them to panel events dates 468 of 470 (99.6%), cross-validated against the exchange's independent Telegram channel (median absolute disagreement: 2 minutes). The premium accrues before the announcement, in someone else's market: for the 79 events already trading on Coinbase when Binance announced, the median return there is +24.4% over the three days before the announcement (Wilcoxon p = 2.4×10⁻⁹) and −17.9% over the seven days after (Fig. 4). Minute-level data around the exact timestamps (92 events with a pre-existing market on Coinbase or Bybit) show +9.4% in the three hours before publication, about 7 percentage points of it in the last fifteen minutes, against +3.3% after (Fig. 5); the pre-announcement run-up appears on both venues. The market learns of the listing before the announcement, consistent with estimates that place informed trading before 28-48% of crypto listings [20]; the publication itself is the afterthought.

FIG::../charts/announcement_premium.png::Fig. 4. Returns on Coinbase around Binance announcement timestamps for the 79 cross-listed events. Median returns: +24.4% over the three days before the announcement; −17.9% over the seven days after.

FIG::../charts/announcement_shock_minutes.png::Fig. 5. Median cumulative return around Binance announcement timestamps, minute-level, on venues where the token already traded (n = 92). The run-up of +9.4% accumulates in the three hours before publication; the three hours after add +3.3%.

## F. The pre-specified holdout, and a third venue

TABLE::TABLE II. The confirmatory family, written 2026-08-23 and frozen in version control 2026-08-24 (Bybit cohort, n = 415): raw and Benjamini-Hochberg-adjusted p-values. H1 and H2 are two-sided, H3 one-sided per the frozen specification.
| Hypothesis | Raw p | BH-adjusted p | Verdict |
|---|---|---|---|
| H1: the fade replicates (+7d) | 5.4×10⁻¹⁴ | 8.1×10⁻¹⁴ | replicates |
| H2: day-0 range predicts the fade | 7.4×10⁻³ | 7.4×10⁻³ | fails: sign flipped |
| H3: extremes mark continuation | 1.9×10⁻¹⁵ | 5.6×10⁻¹⁵ | replicates |

The fade replicates on 415 surviving Bybit listings (−10.34% median week one), and first-week extremes predict continuation (Pearson r = +0.373, inside the predicted band); Table II collects the family. The volatility-predicts-fade gradient fails: its coefficient flips sign on Bybit (+4.65, against −3.47 on Binance in the frozen specification), and the frozen prediction band, calibrated on a different specification, would have failed on the discovery sample too; we report the failure plainly. The survivorship decomposition attributes +0.35 pp of the week-one median to delisting, against the frozen prediction of at least +1 pp. An exploratory third-venue check closes the loop: Coinbase keeps delisted instruments in its public API, and its 566 listings from 2021 onward, 171 of them since delisted, fade almost exactly like Binance's (−4.49%, −12.24%, and −22.26% at one day, one week, and one month; p = 6.6×10⁻³⁵).

# IV. Discussion

The widely cited listing premium is real as a statistic and misleading as a signal: it measures anticipatory accumulation, actions taken before retail buyers can act. Virtually all post-opening windows in the reference table of [2] are negative, and on a panel that keeps the dead, the buyer-accessible component of the effect inverts entirely. The canonical statistics survive every check: we verify the +6.51% listing-day mean of [2] and the +22-33% announcement-day means of [3] exactly as published. It is the trading interpretation built on them that fails. For traders the object of interest is different: the expected loss steepens with day-0 turnover, surviving the listing does not rescue it, and shorting the fade is constrained by instrument access rather than funding costs, a limits-of-arbitrage point [21]. The measurement lesson generalizes. The token-counted median answers "what happens to a typical token?"; the turnover-weighted median answers "what happened to the money?". Here they disagree by 17 percentage points, and any study drawing its sample from live APIs is studying a different market than the one traders experienced.

Limitations. (1) The primary panel is one venue; the Bybit holdout is restricted to survivors, and the Coinbase check is exploratory and mostly USD-quoted. (2) The pre-announcement exercises cover only tokens already trading on another venue and are exploratory. (3) The volatility-fade sign flip across venues is documented, not explained. (4) Day-0 turnover mixes retail demand with market-maker churn, and no public order-book history exists to separate them. (5) Events are dated by the USDT pair's debut; the clean panel (n = 350) strengthens all results.

Future work: order-flow reconstruction around announcements and a mechanism account of the volatility-gradient flip.

# V. Conclusion

Rebuilding the measurement so that no dead coin can drop out of the sample shows that prices fall after listing, by 11.45% in a week for the median token and 28.72% for the median dollar, and most where attention peaked. A pre-specified holdout confirms the fade on a second venue, a third venue reproduces it, and the premium is gone before trading opens: by the time a listing becomes tradeable, the trade everyone knows about has already happened.

# Acknowledgements

The author thanks Sergey Solntsev, PhD in Economics, National Research University Higher School of Economics, for academic supervision, and Binance, Bybit, and Coinbase for maintaining public market-data archives. Large-language-model tools assisted as disclosed in Section II; the work was designed and directed by the author, and no AI tool is an author.

# Data and Code Availability

The companion repository (MIT licence) contains the listing calendars, the 470-event panel, the holdout code with its raw data cache, the announcement-timestamp panel, the funding sweep, the delisting study, and all verification code; a one-command script re-checks every headline number offline. [Editorial note, remove before submission: insert the public GitHub URL and Zenodo DOI.]

# References

REF::[1] L. Ante, "Market reaction to exchange listings of cryptocurrencies," Blockchain Research Lab Working Paper No. 3, 2019, doi:10.2139/ssrn.3450301.
REF::[2] L. Ante and A. Meyer, "Cross-listings of blockchain-based tokens issued through initial coin offerings," Decisions in Economics and Finance, vol. 44, pp. 957-980, 2021.
REF::[3] J. Li, M. Luo, M. Wang, and Z. Wei, "Cryptocurrency listings on cryptocurrency exchanges," SSRN 4715718, 2024.
REF::[4] J. Kolari and S. Pynnönen, "Event study testing with cross-sectional correlation of abnormal returns," Review of Financial Studies, vol. 23, no. 11, 2010.
REF::[5] J. Lyon, B. Barber, and C.-L. Tsai, "Improved methods for tests of long-run abnormal stock returns," Journal of Finance, vol. 54, no. 1, 1999.
REF::[6] J. Moss, The Tie Research, "What does an exchange listing actually deliver?" July 13, 2026, https://thetie.io/insights/what-does-an-exchange-listing-actually-deliver-in-2026.
REF::[7] Animoca Research, "Token listings on centralized exchanges: performance analysis," October 2024; as covered by CryptoSlate, October 31, 2024.
REF::[8] J. Ritter, "The long-run performance of initial public offerings," Journal of Finance, vol. 46, no. 1, 1991.
REF::[9] T. Loughran and J. Ritter, "The new issues puzzle," Journal of Finance, vol. 50, no. 1, 1995.
REF::[10] B. Dharan and D. Ikenberry, "The long-run negative drift of post-listing stock returns," Journal of Finance, vol. 50, no. 5, 1995.
REF::[11] E. Miller, "Risk, uncertainty, and divergence of opinion," Journal of Finance, vol. 32, no. 4, 1977.
REF::[12] R. Boehme, B. Danielsen, and S. Sorescu, "Short-sale constraints, differences of opinion, and overvaluation," Journal of Financial and Quantitative Analysis, vol. 41, no. 2, pp. 455-487, 2006.
REF::[13] Y. Gao, C. X. Mao, and R. Zhong, "Divergence of opinion and long-term performance of initial public offerings," Journal of Financial Research, vol. 29, no. 1, pp. 113-129, 2006.
REF::[14] T. Houge, T. Loughran, G. Suchanek, and X. Yan, "Divergence of opinion, uncertainty, and the quality of initial public offerings," Financial Management, vol. 30, no. 4, pp. 5-23, 2001.
REF::[15] Y. Liu, A. Tsyvinski, and X. Wu, "Common risk factors in cryptocurrency," Journal of Finance, vol. 77, no. 2, pp. 1133-1177, 2022.
REF::[16] A. C. MacKinlay, "Event studies in economics and finance," Journal of Economic Literature, vol. 35, no. 1, pp. 13-39, 1997.
REF::[17] I. D. Dichev, "What are stock investors' actual historical returns? Evidence from dollar-weighted returns," American Economic Review, vol. 97, no. 1, pp. 386-401, 2007.
REF::[18] B. Barber and T. Odean, "All that glitters: The effect of attention and news on the buying behavior of individual and institutional investors," Review of Financial Studies, vol. 21, no. 2, 2008.
REF::[19] M. Ammann, T. Burdorf, L. J. Liebi, and S. Stöckl, "Survivorship and delisting bias in cryptocurrency markets," SSRN 4287573, 2022.
REF::[20] E. Félez-Viñas, L. Johnson, and T. J. Putnins, "Insider trading in cryptocurrency markets," SSRN Working Paper No. 4184367, 2022, revised February 2025, doi:10.2139/ssrn.4184367.
REF::[21] A. Shleifer and R. Vishny, "The limits of arbitrage," Journal of Finance, vol. 52, no. 1, pp. 35-55, 1997.
