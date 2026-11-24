# LivingOps AI — the story to tell

মুখে বলার script ইংরেজিতে (judge আর mentor-দের জন্য), নির্দেশনা বাংলায়।
তিনটা অংশ: ৬০ সেকেন্ডের version, পুরো গল্প (৬ মিনিট, demo-র সাথে), আর
Q&A। Mentor-কে বোঝানোর সময় পুরো গল্প বলো, আর প্রতিটা দৃশ্যের পরের
"Deeper, if asked" অংশ ব্যবহার করো।

নিয়ম: সংখ্যা যেটা বলবে তার source slide-এ থাকবে (`docs/CONTEXT.md` §5)।
আমাদের নিজেদের সংখ্যা সবসময় "measured on our demo company, small sample"
বলে বলবে।

---

## ৬০ সেকেন্ডের version (lift pitch)

> When an engineer leaves a company, IT revokes their email and their GitHub
> access. But the AI agent they built keeps running, with the same keys, and
> nobody owns it anymore. In a recent survey, 79% of former employees said at
> least one work account still worked after they left, and only 21% of
> companies have any process for retiring AI agents.
>
> LivingOps AI puts people and AI agents through one governed lifecycle:
> joining, asking for access, changing owners, leaving. Our rule is simple:
> every access has an owner, a policy reason, an expiry, and proof.
>
> AI reads the company's own policies and drafts the plan, citing them. Rules
> and humans decide. n8n executes only what was approved, on real GitHub. And
> the backend checks GitHub itself before it calls anything done. When a
> manager corrects the AI, that correction becomes an approved lesson the next
> plan uses. And when a policy changes, Policy Guardian finds every old
> decision that now breaks it.

---

## পুরো গল্প (৬ মিনিট, demo-র সাথে)

### দৃশ্য ১ — The hook (০:০০–০:৩৫)
Screen: Dashboard, ownership map। উপরে "Agents with an active sponsor 79.2%"।

> Meet Nexora Labs. Eighty-five people and twenty-four AI agents. Every line on
> this map is ownership: who is responsible for what.
>
> Look at the red ones. Five agents already have no active owner. Their sponsor
> left, or is leaving. They still have keys. Nobody is watching them.
>
> This is not a made-up problem. Companies now find AI agents they did not
> know they had, and almost none have a way to retire them.

Note: Nexora fictional, সব data বানানো। এটা একবার বলে দাও।

### দৃশ্য ২ — Arif is leaving (০:৩৫–১:২০)
Screen: Acting as Farhana (HR) → Arif-এর offboarding শুরু → plan।

> Arif, a senior engineer, is leaving. Farhana from HR opens his offboarding.
>
> In seconds, LivingOps lists everything Arif owns, from the database, not from
> the AI: email, laptop, GitHub access, documents, and two AI agents he
> sponsors. One of them, Aurora Release Bot, has write access to a confidential
> repository. On real GitHub.
>
> Then the AI drafts the plan. It doesn't answer from memory. It retrieves the
> company's own policy clauses and cites them. Click "why" on any step: this
> clause, this version.
>
> And before anyone sees it, our code checks the AI's work: no invented
> resources, nothing missed, only real policy citations. If it fails, the AI
> gets one repair attempt. Otherwise a human takes over.

Deeper, if asked: RAG on Qdrant (hybrid search), LangGraph steps
(inventory → retrieve → plan → validate → repair → questions), evidence IDs
`POL-ACCESS-V1-C0`, no chain-of-thought stored।

### দৃশ্য ৩ — The manager corrects the AI (১:২০–১:৫০)
Screen: Acting as Nabil → plan edit → revision → lesson।

> Nabil, Arif's manager, disagrees with one step. "Don't shut the bot down. We
> still ship with it. Give it to me, but make its key read-only."
>
> His change goes through the same validator. The AI's version isn't deleted:
> we keep both, so anyone can see what the AI said and what the human changed.
>
> And here's the part I like most. The difference becomes a lesson. The AI
> writes it in plain words, a reviewer approves it, we strip personal data,
> and it's stored as company knowledge.
>
> The next time an engineer with a release bot leaves, the AI uses that lesson.
> We measured it: without the lesson, zero of three plans matched Nabil's
> correction. With it, three of three. Every step still cites policy, because
> a lesson is advice, and policy is the law.

Deeper, if asked: lesson আলাদা Qdrant collection-এ; planner-এ যাওয়ার আগে
PostgreSQL-এ যাচাই (APPROVED, stale না, policy CURRENT); AI শুধু ঠিক করে
lesson খাটে কিনা, read-only করার কাজটা code বসায়।

### দৃশ্য ৪ — Execution with proof (১:৫০–২:৪০)
Screen: Approve → Execute → n8n → GitHub page খোলো।

> Tahmid, the IT owner, approves. Now it's real.
>
> n8n carries out only the approved steps, on real GitHub: Arif is removed, the
> bot's write key is swapped for a read-only one under Nabil.
>
> But we never trust the automation's word. n8n holds the write token; our
> backend holds a separate, read-only token. It goes to GitHub itself and
> checks. Only then does a step become "verified".
>
> [GitHub page দেখাও] Here's GitHub. Arif is gone. The key is read-only. Not a
> screenshot from our app: GitHub itself.

Deeper, if asked: idempotency key (একই কাজ দুবার হয় না), retry সর্বোচ্চ ২
বার তারপর HUMAN_REVIEW, n8n ব্যর্থ হলে non-2xx।

### দৃশ্য ৫ — The bot asks for access itself (২:৪০–৩:৩০)
Screen: MCP demo client → LOW request auto → HIGH request → Tahmid approve।

> AI agents don't only get managed. They ask. Through MCP, the standard
> protocol AI agents use for tools, any agent can come to LivingOps and ask
> for access.
>
> A read request on a normal repo: approved instantly. The release bot asking
> for write on the confidential repo: that waits for Tahmid. And production
> access, or an agent whose owner has left: refused, with the rule it breaks.
>
> The risk tier is decided by fixed rules, never by the AI. The AI only
> explains the request to the approver. And every grant expires: eight hours
> for write. When the job is done, the agent gives it back, or a sweeper takes
> it away.

### দৃশ্য ৬ — Main wow: the policy changes (৩:৩০–৪:৪০)
Screen: Guardian → Access Policy V2 activate → impacts → map লাল → remediation।

> Now the question no one asks. What happens when the rules change?
>
> Tahmid activates Access Policy Version 2. New rule: an agent may keep write
> access to a confidential repo only if its sponsor has completed security
> training.
>
> Policy Guardian puts old and new side by side, and then looks back at every
> decision made under the old rule. It finds two things. The bot's write
> access we approved two minutes ago now breaks the policy. And Nabil's lesson
> was learned under the old rule, so it's marked stale and will never steer a
> plan again.
>
> [map লাল] One approval, and the key is downscoped on GitHub and verified.
>
> Policies change. Old decisions usually stay. LivingOps re-checks them.

Deeper, if asked: পার্থক্য বের করে code (diff), AI শুধু সারাংশ লেখে; চালু
access পরীক্ষা হয় নির্দিষ্ট নিয়মে (AI ছাড়া); plan আর lesson ধরা পড়ে policy
version link দিয়ে।

### দৃশ্য ৭ — Proof and quality (৪:৪০–৫:১৫)
Screen: ISO 27001 evidence report → evaluation panel।

> Auditors ask: show me that access was removed on time, and why. One click:
> an evidence report mapped to ISO 27001 controls, built from the work itself.
>
> And we measure ourselves. On our demo company: plans valid, every step
> citing policy, Guardian finding every seeded impact with zero false alarms,
> every action verified on GitHub. Small samples, reported as found.

### দৃশ্য ৮ — Why it matters (৫:১৫–৬:০০)
> Our target is companies of one to five hundred people, the ones without an
> identity team or a six-month enterprise rollout. Bangladesh alone has over
> four and a half thousand software companies, and they are adopting AI agents
> right now.
>
> Our principle fits in one line: AI thinks, rules and humans decide, n8n acts,
> and the backend verifies.
>
> Every access has an owner, a policy reason, an expiry, and proof. For people,
> and for the AI agents that now work beside them.

---

## Mentor-কে আগে বলার ৫টা কথা (গল্পের আগে)
১. **কী সমস্যা:** মানুষ চলে গেলে তার access আর তার বানানো AI agent দুটোই
   থেকে যায়।
২. **কী নতুন:** মানুষ আর agent একই lifecycle-এ; policy বদলালে পুরোনো
   সিদ্ধান্ত আবার পরীক্ষা হয়; মানুষের correction থেকে approve-করা শেখা।
৩. **কেন বিশ্বাসযোগ্য:** AI কখনো নিজে কিছু বদলায় না; ঝুঁকি ঠিক করে নিয়ম;
   GitHub-এ নিজে গিয়ে যাচাই।
৪. **কী সত্যিই চলে:** আসল GitHub org, deployed backend + MCP + n8n, তিনটা
   demo mode (LIVE, CACHED_AI, OFFLINE) একই ফল দেয়।
৫. **কী সীমা:** নিচে Q&A-তে।

---

## Q&A — সম্ভাব্য প্রশ্ন আর ছোট উত্তর

**What if the AI makes a mistake?**
> It can't act on it. It only drafts. Our validator rejects invented resources
> or citations, humans approve, and the backend verifies on GitHub.

**Why not let the AI decide the risk tier?**
> Same request, same answer, every time, and an auditor can read the rule.
> The AI explains; rules decide.

**Does the system really learn?**
> Yes, but only from approved corrections, and policy always wins. Without the
> lesson 0 of 3 plans matched the manager; with it 3 of 3. Small sample.

**How do you find what changed in a policy?**
> Code compares the texts; the AI only summarises. Live access is re-checked
> with fixed rules, and plans and lessons are found through the policy version
> they cite.

**What if someone rewrites the whole policy?**
> Plans and lessons are still caught, because that uses version links. A
> completely new kind of rule needs to be added to our rule set before live
> access is checked against it. That's deliberate: we don't let an AI guess
> that someone's access is illegal. Next step: the AI proposes a rule, a human
> approves it.

**What if n8n says success but it didn't happen?**
> The step never becomes verified. That's exactly why the backend checks
> GitHub itself, with its own read-only token.

**What about privacy?**
> The AI sees only approved metadata, never passwords or private files.
> Lessons are stripped of names, emails and IDs before storage. The demo
> company is fictional.

**What if the internet fails on stage?**
> OFFLINE mode replays recorded AI answers and a local executor. Same result.

**How is this different from Okta or Microsoft Entra?**
> They're built for large enterprises with add-on licences. We ground every
> decision in the company's own policy text, keep human approval records, and
> handle the "owner left, agent keeps running" case end to end, at a size and
> price small companies can use.

**What are the limits today?**
> GitHub is the one real integration; email, laptop and documents run on a
> demo system. Our evaluation numbers are on a small demo company. New kinds of
> policy rules need code before live access is checked against them.
