# SwarmFolio Referee: pitch kit

**One line:** AI proposes. Math decides.
**Say it like this:** "AI drafts investment portfolios that break the client's rules. My Referee catches it, proves it, fixes it and gives you a receipt."

---

## 1. The 30-second version (judge walks up, or you're short on time)

> "Advisors are starting to let AI draft client portfolios. The problem: the AI breaks the client's rules. In my tests, about 80% of first drafts broke at least one rule. And when you tell the AI to fix it, it mostly doesn't.
>
> So I built a Referee. It's not another AI, it's an exact math solver. It checks every rule, tells you what broke in the client's own words, finds the smallest fix, and if the rules are impossible it proves it and tells you which rules clash.
>
> It runs as five Fetch.ai agents you can talk to in ASI:One. Want to see it?"

---

## 2. The full pitch (about 2.5 min, with the demo)

**Tabs open, in this order:** (1) the ASI:One shared chat of C04 · (2) swarmfolio.biz on C04 · (3) C02 receipt · (4) C03 · (5) a fresh ASI:One chat · (6) the Agentverse profiles

### 0:00 Hook (15s)
> "Anyone can ask an AI for a portfolio. But an advisor has rules from the client: 'max 20% in one stock', 'no oil companies', 'don't trigger a big tax bill'. AI drafts break those rules. A published study found it in up to 86% of first drafts. I measured about 80% myself. An advisor legally can't send that."

### 0:15 The committee (45s) — Tab 1 (ASI:One) then Tab 2 (website)
> "This is Mr. Alvarez, a synthetic client: tech executive, 60% of his money in NVIDIA, Microsoft and Apple, wants to de-risk without a huge tax bill. Eight rules.
>
> Five Fetch agents: a Macro, a Fundamentals and a Risk analyst write memos, a Chair proposes a portfolio, and the Referee checks it.
>
> Round 1 broke 2 rules. The analysts argue: concede, defend or modify. Round 2 still broke 3. Round 3: compliant with all 8. And you can see who changed their mind and why."

*(Point at the round tally: broke 2 → broke 3 → ✅.)*

### 1:00 The receipt (20s) — Tab 3 (C02)
> "When the AI can't fix it, the Referee does. This is Dr. Patel: the draft broke 2 of 7 rules. The Referee found the nearest compliant portfolio. It moves 3.9% of the money, and every broken rule is quoted in the client's own words, actual vs. limit. Same inputs, same receipt ID, every time. It's an audit record."

### 1:20 The twist: impossible rules (25s) — Tab 4 (C03)
> "Now the hard part. Dr. Patel's family gives her UNH shares she has to keep. Now her rules are impossible: 30% JNJ plus 10% UNH is 40% healthcare, but her cap is 35%.
>
> An AI would just quietly break one. A heuristic optimizer would say 'couldn't find one'. The Referee *proves* no portfolio exists, names the exact 3 rules that clash, and gives the cheapest fix: raise the healthcare cap to 40%. That's a conversation the advisor can have with the client."

### 1:45 Price tags + the finding (25s)
> "It also prices every rule. For Mr. Alvarez, the tax rule costs him 4.2 points a year of risk-adjusted return, the volatility cap 2.4, and the tech cap almost nothing.
>
> And I tested whether AI can fix itself. Two different models, 26 clients. About 80% of first drafts broke a rule, and after three rounds of feedback only 20 to 50% became compliant. The Referee's repair gets 100%. So the verifier is the product, not the AI."

### 2:10 Close (20s) — Tab 6 (Agentverse) or Tab 5 (live)
> "The Referee is its own agent on Agentverse. Any AI that builds portfolios can call it, and it supports pay-per-check through Fetch's payment protocol. You can even type rules in plain English.
>
> AI proposes. Math decides. Want to try to break it?"

**Then hand them the laptop** (see section 3).

---

## 3. "Try to break it" (the moment that wins the judge)

Pick one, depending on how things are going:

- **Safe (website, instant):** swarmfolio.biz → any client → *Try the Referee* → let them change the weights and check.
- **Live in ASI:One (plain English):** in a fresh chat:
  `@swarmfolio-referee check AAPL 50, JNJ 30, KO 20 against: no single stock above 40%, at least 35% in healthcare, healthcare at most 25%`
  → it reads the rules back, then sends the receipt: the rules are impossible (35% > 25%), here are the clashing rules and the cheapest fix.
  **Test this exact message once before judging**, so you know what it replies.
- **Fully live committee (~50s, only if ASI:One is responsive):** `@swarmfolio-chair run C14 fresh`.
  Say upfront: "This is a brand-new run, no cache, it takes about a minute." Keep talking while it runs (section 5 answers).

**If anything is slow or fails:** "ASI:One is rate-limited right now, here's the same thing recorded." Switch to Tab 1 and keep going. Never debug in front of a judge.

---

## 4. Demo video for Devpost (2–3 min) — shot list

Record with QuickTime (File → New Screen Recording) or Cmd+Shift+5. Use your mic and talk like the pitch above. One take per scene is fine. Joining clips in iMovie is optional.

| # | Time | Screen | What you say |
|---|---|---|---|
| 1 | 0:00–0:15 | swarmfolio.biz home | The hook (section 2) |
| 2 | 0:15–0:55 | ASI:One: `@swarmfolio-chair` C04 run, scroll the rounds + cards | The committee, 5 agents, broke 2 → 3 → compliant |
| 3 | 0:55–1:15 | Website C04 run page | "Same run, as an audit report" + round tally |
| 4 | 1:15–1:35 | C02 receipt with the stamp | The receipt |
| 5 | 1:35–1:55 | C03 impossible | The twist |
| 6 | 1:55–2:10 | C04 price tags | Price tags |
| 7 | 2:10–2:30 | Experiment page | The finding (honest numbers) |
| 8 | 2:30–2:50 | ASI:One: plain-English Referee message + the payment flow (show the Stripe test checkout if you recorded it earlier) | "Any agent can call it, pay per check" + close |

Upload to YouTube as **Unlisted**. Put the link in Devpost + the Fetch submission + the README.

---

## 5. Judge Q&A (short answers, say them out loud once)

**"Isn't this just an AI wrapper?"**
"The opposite. The AI is the easy part. Delete the AI and the Referee still works on a portfolio from anywhere. It's an exact solver (CVXPY with SCIP, mixed-integer). That's the product."

**"Is it hardcoded / is it cached?"**
"The Referee always runs live. The AI debates on the website are real saved runs, so the site is fast and doesn't burn the AI quota. Want a brand-new one? Name any client and I'll run it fresh in ASI:One right now."

**"Why not just put the rules in the prompt?"**
"I did, that's the baseline. It still broke rules about 80% of the time. Prompts are suggestions. Constraints are guarantees."

**"How do you find which rules clash?"**
"A deletion filter. Remove rules one at a time. If it's still impossible without a rule, that rule wasn't needed. What's left is a minimal clashing set."

**"How does the cheapest fix work?"**
"I let every rule bend with a penalty weighted by how important it is, and solve for the smallest total bend."

**"How do price tags work?"**
"Solve for the best risk-adjusted portfolio with all the rules, then again without each rule. The difference is what that rule costs. It's never negative, and zero means the rule doesn't bind."

**"Why five agents and not one program?"**
"Each has one job and its own address, so they can fail or be swapped independently. The Referee especially is a reusable service any other agent can call. If an analyst times out, the Chair carries on and says so."

**"What did your experiment find?"**
"Two models, realistic tight clients. About 80% of first drafts broke a rule. After three rounds of feedback only 20–50% were compliant. Explaining the violation was a small trend, not statistically significant, and I report that honestly. Only the Referee's repair reaches 100%."

**"Why only 19 stocks, synthetic clients?"**
"It's a demo universe so everything is reproducible. The solver doesn't care. More tickers is just more data."

**"Is this financial advice?"**
"No. It's a tool for advisors, who are the fiduciaries. It only checks rules, a human decides."

**"Who would pay for this?"**
"Wealthtech platforms and AI-agent builders, per verification. That's why the Referee is a standalone agent with Fetch's payment protocol."

**"What did you build here vs. before?"**
"Before: my SwarmFolio repo (price data, return math, a swarm optimizer). Here: the whole Referee, the committee, the 5 agents, the website, the experiment. It's in the README table and the commit history."

**"Did you use AI to code it?"**
"Yes, heavily: Claude Code and Devin. I designed it in Paper, decided the architecture, and reviewed and tested every change. That's how software gets built now."

---

## 6. Before judging (12:00–12:30)

- [ ] Laptop charged + plugged in, sleep off, phone hotspot ready
- [ ] Agents running: `pgrep -fl agents.run_all` shows a process
- [ ] 12:15: load swarmfolio.biz (wakes Render), send `@swarmfolio-chair` one message
- [ ] Tabs open in the order from section 2
- [ ] Said the full pitch out loud 3×, once with a timer
- [ ] Water. Breathe. You built something real.
