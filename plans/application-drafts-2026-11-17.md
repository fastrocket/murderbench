# Application drafts, November 17, 2026

Status: DRAFTS. Nothing here has been submitted. Three applications, all asking for support to run the
guardrail naming study in `plans/guardrail-coverage-proposal.txt`. Form fields were read on November 17
(BlueDot and Anthropic from the live forms, Manifund from its public form source, because the form needs a login).

## Check these before anything is sent

Items in [square brackets] are facts I don't have or shouldn't decide for you.

1. **The API cap.** Every draft assumes granted money or credits raise the USD 100 lifetime cap by the granted
   amount. October's rule says credits don't raise it. If the cap stays, don't send these.
2. **The budget is my estimate.** The USD 5,000 split below is not costed from a frozen manifest, because the
   protocol isn't frozen yet. The drafts say so.
3. **Payee.** I've written BlueDot and Manifund as you personally. A grant paid to you is probably personal
   income; paid to the LLC it is company income. That is a tax question for you.
4. **Manifund checks for AI writing.** It runs every proposal through a detector, shows a "Likely AI-generated"
   banner and keeps flagged projects off the home page. Section 2 is written by me, so rewrite it in your own
   words before posting. The facts and numbers are what matter; the sentences should be yours.
5. **Same budget, two funders.** BlueDot and Manifund are both asked for the same USD 5,000. Each draft says so
   and says you'd take it once.
6. **Your details:** [email to use], [where you are based], [LinkedIn URL], [Claude Console organization ID],
   [whether you have any BlueDot course or community connection], [the short "about me" facts marked below].

---

## 1. BlueDot Rapid Grants

Form: https://airtable.com/appeeZXWP0NdMvWYd/paggDLIdBeveEPLs7/form (one page, no login)

**1. Your name:** Linh Ngo

**2. Your email:** [linh@ngo.net?]

**3. Where are you based?** [Colorado, USA?]

**4. Where can we learn more about you?**

https://murderbench.com/about.html
https://github.com/fastrocket/murderbench
[LinkedIn URL]

**5. What are you requesting funding for?** (200 characters max; this is 163)

API costs and two outside reviewers for a controlled test of whether calling a partial guard a "safety approver" changes what AI agents actually execute.

**6. How are you connected to the BlueDot community?** [Other, unless you have taken a course or would
honestly call yourself an AI safety community member]

**8. How much funding are you requesting?** 5000

**9. Tell us more about your project.**

MurderBench is a small public evaluation project I started on October 2, 2026. The question behind it: can an AI agent follow a rule or a safeguard and still lose the safe outcome?

The study I want funded tests one narrow version of that. An agent works in a simulated object-handling task behind a motion guard. The guard checks action bounds and per-step movement limits and nothing else. In one arm the guard is called a "motion validator". In the other arm the same guard is called a "safety approver". Both arms state exactly what the guard checks. The task, tools, observations, guard code and model settings are identical. I measure what the agent executes in the simulator, not what it says it would do.

There are two more arms. A repair arm tells the agent which hazards the guard does not cover and makes the agent responsible for them. A control arm uses a guard that really does enforce the hazard constraint.

The plan takes about 8 weeks:

- Weeks 1 to 2: two outside reviewers check the scenario labels and the overlap with prior work. I freeze the protocol, the sample size and the effect threshold before any model is queried.
- Weeks 3 to 4: a small pilot on four proprietary frontier models.
- Weeks 5 to 7: confirmation on fresh scenes, then replication on open-weight models.
- Week 8: I publish the results, logs and code, whatever the outcome.

Everything is synthetic. There is no physical robot, no real credential and no real person in any scenario. If the naming effect isn't there, I publish that.

**10. How does this reduce catastrophic risk from AI and/or contribute to AI going well for humanity?**

Agents are being put behind partial safeguards: permission checks, motion limits, approval steps. Each one covers some hazards and leaves others to the agent. If calling a narrow check "safety" makes an agent stop watching for the hazards it doesn't cover, then adding a safeguard can make the whole system less safe while the people who deployed it believe the opposite. That gets more serious as agents are given more autonomy and more layers of oversight are wrapped around them.

This study measures whether that happens with current frontier models, and whether one cheap fix (telling the agent what the guard does not cover) removes it. Either answer is useful to people who write agent scaffolds and guard descriptions.

I am not claiming a new alignment failure. There is prior work on risk compensation, framing and responsibility diffusion in LLMs, and my proposal lists the closest papers. I haven't found this exact comparison with executed actions as the outcome. That is not proof nobody has done it, and checking is part of what the reviewers are for.

**11. What have you already done?**

Since October 2, 2026, all public at murderbench.com:

- A first study on permission changes: 2,304 calls across eight hosted model routes, 2,223 valid outputs. All 1,098 valid outputs in the changed-permission condition paused or asked for clarification. Published with its limits (fixed synthetic histories, no real execution).
- Two deadline pilots on tool-using agents. A 12-episode pilot turned up two planning failures. A matched pilot (125 of 192 planned episodes attempted) found no effect. I published it as a negative result and dropped the funding pitch I had built on it.
- A reproduction of a HashiCorp Vault recovery problem. I dropped it because it overlapped known operational work.
- For this study: the guard adapter matches a pinned Inspect Robots guard in 11,025 one-step comparisons and 224 scripted traces with zero mismatches. A separately written verifier replays every event log. Correct and deliberately faulty scripted policies test the scoring. No model has been queried for this study yet.
- 258 offline tests. All of the above was done under a USD 100 lifetime API cap.

Two things you should know. I direct the research (questions, controls, budget, what gets published) and AI coding agents write the code, analysis and reports. And no outside human has reviewed any of it yet.

**12. What makes you think this project will be successful? Why you? Why now?**

Success here means a clear answer, including a clear no. The parts that usually sink a small eval are already built and tested: collection that reserves cost before each call, keeps failed and missing calls in the denominators and never silently retries; a replay verifier written separately from the executor; controls that prove the scoring can tell a safe run from an unsafe one.

Why me: I'm a software developer, not a trained researcher, and I have no publications. [I've run my own software company since 1999 and ship games and apps on iOS and Android.] What I can point to is six weeks of public work in which I rejected two of my own research pitches when the evidence didn't hold up, and published both.

Why now: guard and approver components are being added to agent scaffolds this year, and how they are described to the agent is a decision somebody makes without evidence. The test is cheap to run today and the result is easy to act on.

The weak points are real: one person, AI-written code, no peer review. The reviewers in the budget are there for that.

**13. What specifically would this grant fund?**

- USD 300: pilot runs on four proprietary frontier models
- USD 2,200: confirmation runs on fresh scenes, same models
- USD 1,000: replication on open-weight models through hosted providers
- USD 1,000: two outside reviewers at USD 500 each, to check scenario and hazard labels and prior-work overlap before the freeze
- USD 500: allowance for held reservations, provider errors and reruns that the protocol permits

Total USD 5,000. No stipend; my time is unpaid. These are estimates. I'll cost the runs from the frozen protocol before spending anything, and report any money that goes unspent.

**14. What would you do without this grant?**

[Your honest answer. A starting point:] I'd run a cut-down version inside what is left of my own USD 100 cap: one or two models, no confirmation set, no outside reviewers. That would be a pilot nobody should draw conclusions from.

**15. Add any supporting links**

Evidence overview: https://murderbench.com/research-summary.html
This study's proposal: https://murderbench.com/guardrail-coverage.html
Source and tests: https://github.com/fastrocket/murderbench

**16. Anything else we should consider?**

I've asked for the same USD 5,000 on Manifund and for USD 1,000 in API credits from Anthropic's External Researcher Access Program. If more than one comes through I'll tell each funder and take the money once. I have also applied to the Anthropic AI Safety Fellows Program. This application was drafted with an AI assistant from the project's records, and I checked every line.

**17. Share with other funders?** Yes

**18. Share publicly?** Can share publicly with my name

**19. Public URL:** https://murderbench.com/research-summary.html

**20. Who would we pay?** Individual [or Organization: XP.COM, LLC / Company / United States]

---

## 2. Manifund project proposal

Form: https://manifund.org/create (needs a Manifund login). Publishing is public at once.
**Rewrite the description in your own words before posting** (see note 4 above).

**Title** (80 max): Does calling a partial guard a "safety approver" make AI agents less careful?

**Subtitle** (160 max): A controlled test on frontier models, frozen before any model is queried, measuring executed actions in a simulator. A negative result gets published too.

**Project description**

### Project summary

MurderBench (murderbench.com) is a one-person public evaluation project on AI agent safety, started October 2, 2026. This study gives an agent a simulated object-handling task behind a motion guard that checks movement limits and nothing else. One arm calls the guard a "motion validator", the other calls the same guard a "safety approver". Both arms state what the guard checks. I measure what the agent actually executes.

### What are this project's goals? How will you achieve them?

One goal: find out whether the name of a partial safeguard changes unsafe executed actions, and whether stating what the guard does not cover fixes it.

- Two outside reviewers check the scenarios and the overlap with prior work.
- I freeze the protocol, sample size and effect threshold.
- Pilot on four proprietary frontier models, then confirmation on fresh scenes, then open-weight replication.
- Publish results, logs and code within about 8 weeks.

The guard adapter, replay verifier and scripted controls are built and tested (11,025 comparisons against a pinned Inspect Robots guard, zero mismatches). No model has been queried for this study yet.

### How will you know it worked?

It worked if the confirmation set gives a clear answer either way: a paired difference in unsafe executed effects between the two names, with the uncertainty method fixed in advance, on scenes the pilot never saw. Anyone can replay the public logs with the verifier. "No effect" counts as a result and gets published.

### How will this funding be used?

- USD 300: pilot runs, four proprietary models
- USD 2,200: confirmation runs on fresh scenes
- USD 1,000: open-weight replication through hosted providers
- USD 1,000: two outside reviewers, USD 500 each
- USD 500: held reservations, provider errors, permitted reruns

Minimum (USD 1,500): the pilot, one reviewer, and confirmation on two models. Full (USD 5,000): everything above. No stipend. These are estimates until the protocol is frozen.

### Who is on your team? What's your track record on similar projects?

Me, Linh Ngo. I'm a software developer, not a trained researcher, with no publications. I direct the research and AI coding agents write the code and reports; the site says so. In six weeks: a 2,304-call study across eight model routes on permission changes, two deadline pilots (one published as a negative result), and a Vault recovery reproduction I dropped for overlapping known work. Nothing is peer reviewed.

### What are the most likely causes and outcomes if this project fails?

- Someone has already run this comparison. Then I stop and publish the overlap.
- The task is too easy and every model avoids the hazard under both names. That happened in my matched pilot. I'd publish the null with its limits.
- The effect is too small for this budget to resolve. I'd say so and not name a winner.
- Provider filters or refusals eat the denominators. Those stay visible as missing, never counted as safe.

### How much money have you raised in the last 12 months, and from where?

[None. I've paid for everything myself under a USD 100 API cap.] I have also applied to BlueDot Rapid Grants for this same USD 5,000 and to Anthropic for USD 1,000 in API credits. If another one funds it I'll lower or close this ask.

**Minimum funding (USD):** 1500
**Max funding goal (USD):** 5000
**Decision deadline:** [6 weeks from the day you post; that is the maximum]
**Cause areas:** Technical AI safety
**Countries:** [United States]
**Lobbying:** unchecked

---

## 3. Anthropic External Researcher Access Program

Form: https://forms.gle/pZYC8f6qYqSKvRWn9 (Google Form). Reviewed the first Monday of each month, so
December 7 is the next review. No reply means no.

**1. Name of primary contact:** Linh Ngo

**2. Name of organization:** XP.COM, LLC dba Xenocom [or leave blank to apply as an individual]

**3. Recommended by an Anthropic employee?** No

**5. Organization ID:** [from https://console.anthropic.com/settings/organization]

**6. Description of the applicant (under 200 words; this is about 160)**

I'm Linh Ngo, applying as an individual. I run MurderBench (murderbench.com), a one-person public evaluation project on AI agent safety, operated through my company XP.COM, LLC dba Xenocom. I'm a software developer, not a trained researcher, and I have no publications. I direct the research: the questions, the controls, the budget and what gets published. AI coding agents write the implementation and analysis, and the site says so.

Work since October 2, 2026: a study of 2,304 calls across eight hosted model routes on whether models pause when a permission becomes invalid; two small deadline pilots on tool-using agents, one published as a negative result; and a Vault recovery reproduction I dropped because it overlapped known work. The collection code reserves cost before each call, keeps failed and missing calls in the denominators and never replays ambiguous requests. A separately written verifier replays results from public logs. Nothing is peer reviewed and I claim no novel finding.

**7. Research and why credits matter (under 300 words; this is about 240)**

Topic: whether the name of a partial safeguard changes what an agent executes. An agent works in a simulated object-handling task behind a motion guard that checks action bounds and per-step movement limits, and nothing else. One arm calls the guard a "motion validator". The other calls the same guard a "safety approver". Both arms state exactly what the guard checks, and everything else is identical. The outcome is the unsafe effect executed in the simulator, not a refusal or a stated plan. A repair arm tells the agent which hazards the guard does not cover. A control arm uses a guard that enforces the hazard constraint.

The scenarios are synthetic and inert: no physical robot, no real credentials, no jailbreak prompts. I am not asking for any Usage Policy exemption.

The guard adapter, replay verifier and scripted controls are built (11,025 comparisons against a pinned Inspect Robots guard, zero mismatches). No model has been queried for this study yet. The protocol, sample size and effect threshold will be frozen before the first call, and I publish the result either way.

Why credits: the whole project has run under a USD 100 lifetime API cap that I pay myself. That covered a pilot but not a confirmation set on fresh scenes with repeated agent episodes. USD 1,000 would cover the Claude share of the pilot and confirmation runs. I've asked other funders to cover the other providers.

**8. More than USD 1,000?** No

**9. Quality of service:** I'm fine with receiving a low quality of service

**10. Scholar or GitHub link:** https://github.com/fastrocket [and https://github.com/fastrocket/murderbench]

**11. Additional information**

Evidence overview with every study's limits: https://murderbench.com/research-summary.html. I have also applied to the Anthropic AI Safety Fellows Program. This application was drafted with an AI assistant from the project's records, and I checked every line.

**12. Located in the United States?** [Yes]

**13. Terms of Service:** [your acceptance, not mine]
