# Feedback on Vaani

Draft. Factual points re-checked against the live site on 10 Nov 2026 (`vaani.dev`,
`vaani.dev/pricing`, `vaani.dev/platform`); edit the opinions into your own voice before
submitting. No live call or interview was run, so anything about call quality here is
untested by me and marked as such.

## What is strong

* **The problem is framed correctly.** "Zero dead air", "turn taking", "auto language
  switch" are the things that actually make a voice agent feel wrong, and they are stated
  as outcomes rather than as model features.
* **Teacher AI lowers the floor.** Describing an agent in a sentence and getting a
  deployment-ready draft, with a prompt diff to accept, is the right shape for this
  market: the buyer is an ops team, not an ML engineer. The diff-before-save detail is
  the part that makes it trustworthy.
* **Memories are a real differentiator.** Callers repeating context every call is the
  most common complaint about phone agents, and per-caller recall with a filter is a
  concrete answer to it.
* **Call screening handling** - staying on the line through the carrier prompt and
  re-introducing on pickup - is exactly the unglamorous engineering that decides whether
  an outbound campaign works.

## What I would push on

* **Numbers without denominators.** The homepage shows "0M+", "0.0%", "<0ms" in the
  rendered text, and the claims (~450 ms p90, 98% of screenings under 15 s) have no
  sample size or test conditions. For a latency-led product, publishing the measurement
  method is part of the pitch.
* **Docs are one click away but not on the page.** There is no visible quickstart or API
  snippet on the landing page; the path from "interested" to "first call made" runs
  through a separate docs domain and an app signup. A curl example next to the latency
  claim would shorten that.
* **"Start free" does not lead to a free plan.** The hero CTA reads "Start free on
  Vaani's Platform", but `/pricing` lists only pay-as-you-go (prepaid wallet, ₹1/min
  platform fee, 2 concurrent calls, ₹600/month for a number) and Enterprise. A reader
  who clicks expecting a free allowance finds a wallet top-up instead. Either name the
  allowance or change the CTA.
* **Language claim vs evidence.** "Auto-switch to your language and dialect" is a strong
  claim for Indian telephony; a short before/after audio sample would be more convincing
  than the sentence.

## What I would test if I had access

1. Time to first working agent, from signup to a call that answers one question.
2. Whether the documented p90 latency holds on a Hinglish, noisy 8 kHz line - the
   conditions the marketing implies.
3. What happens on an interruption mid-sentence, and whether the agent recovers the
   thread or restarts it. That is the failure mode I would optimise against.
