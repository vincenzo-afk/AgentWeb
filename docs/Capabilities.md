
No paid search APIs

Self-host the retrieval infrastructure wherever possible

Aim for effectively unlimited searching subject to upstream/provider limits, not paid per-request quotas

Different modes must have genuinely different retrieval behavior

Quality > quantity

Dive must use web + GitHub + documents + YouTube

WaterCrawl + open-source ScrapeGraphAI

Add only a small number of search backends

Return a small, high-value evidence package to the AI, not a giant search dump

Make the whole thing suitable for your coding agents to implement in AgentWeb.


One correction from the previous plan: don't add Brave Search API if your requirement is strictly no paid services. Use SearXNG + LibreY as the two additional self-hosted metasearch backends. Both are open-source/self-hostable; SearXNG exposes a JSON search API and currently aggregates many search services, while LibreY is another metasearch engine with its own API. 

AgentWeb — complete retrieval architecture

1. The core philosophy

AgentWeb should optimize for:

> Maximum useful evidence per token and per second.



Not:

> maximum number of search results.



The pipeline should therefore be:

USER QUESTION
      │
      ▼
TASK UNDERSTANDING
      │
      ▼
RESEARCH PLAN
      │
      ├── Search
      ├── Web pages
      ├── GitHub
      ├── Documents
      ├── YouTube
      ├── Academic
      └── Community
      │
      ▼
CANDIDATE DISCOVERY
      │
      ▼
DEDUPLICATION
      │
      ▼
SOURCE QUALITY RANKING
      │
      ▼
SELECTIVE FETCH
      │
      ▼
IMPORTANT-PASSAGE EXTRACTION
      │
      ▼
CLAIM / EVIDENCE GRAPH
      │
      ▼
CORROBORATION + CONFLICT DETECTION
      │
      ▼
MISSING-EVIDENCE DETECTION
      │
      ├── sufficient → STOP
      │
      └── insufficient → TARGETED SECOND WAVE
      │
      ▼
CONTEXT COMPILER
      │
      ▼
SMALL MCP RESPONSE
      │
      ▼
AI MODEL


---

2. The search backends

I would use exactly these:

🥇 SearXNG — primary web discovery

Self-host your own SearXNG instance.

It has a programmatic /search API with JSON output and supports categories, language, time ranges and paging. 

Its current documentation describes it as a free, self-hosted metasearch engine aggregating results from many search services. 

Use it for:

general web
news
images when necessary
science
GitHub discovery
technical content
community sources

Role

Broad discovery.


---

3. LibreY — independent second discovery backend

LibreY is also self-hostable and provides an API. It currently searches across several providers including Google, DuckDuckGo, Brave, Ecosia, Yandex and Mojeek. 

Use it selectively, not for every query.

For example:

SearXNG → primary discovery
LibreY  → second independent discovery

Then merge:

SearXNG
   +
LibreY
   ↓
canonical URL
   ↓
content fingerprint
   ↓
duplicate removal

This gives AgentWeb more retrieval diversity without requiring a paid API.


---

4. Don't search both engines blindly

This is important.

Bad:

every query
 ├── SearXNG × 10
 └── LibreY × 10

Better:

normal question
      ↓
SearXNG
      ↓
enough candidates?
      ├── yes → continue
      └── no → LibreY

For Dive:

SearXNG
   +
LibreY
   ↓
merge
   ↓
deduplicate
   ↓
rank

So LibreY becomes a recall/redundancy layer, not a result multiplier.


---

5. WaterCrawl — deep web extraction

WaterCrawl should be AgentWeb's deep web crawler/extractor.

Its current project supports customizable crawling, search, multiple crawl depths, targeted content, asynchronous processing, REST/OpenAPI and self-hosting. 

Use it when AgentWeb decides:

> "This website is important enough to investigate further."



Not on every search result.

Flow

SearXNG / LibreY
       ↓
candidate URL
       ↓
source ranking
       ↓
IMPORTANT?
   ├── no → discard
   └── yes
        ↓
    WaterCrawl
        ↓
    clean content


---

6. ScrapeGraphAI — structured extraction

Use the open-source self-hosted ScrapeGraphAI library, not its paid managed API.

The project explicitly distinguishes its open-source library from the paid managed service; the open-source version can run on your own infrastructure and can use local models/Ollama or other supported LLMs. 

Its job should be:

> Extract specific information from an already-important source.



Example:

Source:
NVIDIA technical report

AgentWeb asks:

Extract:
- model architecture
- parameter count
- training data
- context length
- benchmark results
- limitations

ScrapeGraphAI returns structured data.

That's far better than throwing the entire document at the final AI.


---

7. WaterCrawl vs ScrapeGraphAI

Keep the responsibilities separate.

Tool	AgentWeb role

SearXNG	Find things
LibreY	Additional discovery
WaterCrawl	Crawl/extract websites
ScrapeGraphAI	Extract specific structured information
Native fetcher	Fast/simple pages
YouTube pipeline	Video evidence
Document pipeline	PDF/DOC/etc. evidence


Simple rule

"Find it"
    → search

"Read it"
    → fetch/WaterCrawl

"Extract these exact fields"
    → ScrapeGraphAI


---

8. ⚡ FLASH

Flash should be fast factual retrieval.

Budget

TIME:             3–8 sec target
SEARCH WAVES:     1
QUERIES:          1–2
CANDIDATES:       8–15
FETCH:            2–4 pages
CRAWL DEPTH:      0
FINAL SOURCES:    2–4
MCP CONTEXT:      ~2–4k tokens

Sources

Priority:

official
primary
documentation
high-authority

Pipeline

Question
  ↓
query expansion
  ↓
SearXNG
  ↓
rank
  ↓
top 2–4
  ↓
fast fetch
  ↓
extract relevant passages
  ↓
evidence gate
  ↓
STOP

Flash should NOT:

crawl websites deeply

transcribe YouTube

analyze giant PDFs

launch many providers

perform multiple research waves


If the answer can't be established quickly:

{
  "status": "insufficient_evidence",
  "suggested_mode": "focus"
}

Don't secretly turn Flash into Dive.


---

9. 🎯 FOCUS

Focus should be the normal AI research mode.

Budget

TIME:             8–20 sec target
SEARCH WAVES:     1–2
QUERIES:          3–4
CANDIDATES:       20–35
FETCH:            5–8
CRAWL DEPTH:      0–1
FINAL SOURCES:    4–8
MCP CONTEXT:      ~4–7k tokens

Search

Primary:

SearXNG

Fallback/expansion:

LibreY

Source strategy

official
technical
independent
community
recent

Not every category has to be present.

Focus process

Question
   ↓
identify research dimensions
   ↓
3–4 targeted queries
   ↓
SearXNG
   ↓
if weak → LibreY
   ↓
merge
   ↓
deduplicate
   ↓
rank
   ↓
fetch top sources
   ↓
extract useful passages
   ↓
check evidence
   ↓
one targeted follow-up if necessary
   ↓
STOP


---

10. 🔬 DIVE — this is the big one

Dive should become AgentWeb's full research mode.

Not:

> "search harder"



but:

> "investigate the question across different information modalities."



Budget

TIME:             20–60 sec target
SEARCH WAVES:     2–4
QUERIES:          5–10
CANDIDATES:       40–80
WEB FETCHES:      10–20
YOUTUBE:          3–5 important videos
DOCUMENTS:        3–8 important documents
CRAWL DEPTH:      1–2
FINAL SOURCES:    ~8–15
FINAL EVIDENCE:   ~20–40 passages
MCP CONTEXT:      ~6–12k tokens

These are budgets/targets, not hard guarantees.


---

11. Dive source planner

For every question, dynamically determine:

WEB
GITHUB
DOCUMENTS
YOUTUBE
ACADEMIC
COMMUNITY
OFFICIAL

Example:

"Research this AI framework"

Official docs     █████
GitHub            █████
Technical blogs   ███
YouTube           ███
Community         ██
Academic          █

"Research this ML paper"

Academic          █████
Paper              █████
GitHub             ████
Technical          ███
YouTube            ██
Community          █

"Research this programming library"

Official docs     █████
GitHub            █████
Issues/PRs        ████
Technical         ███
YouTube           ██
Community         ██

This is what I mean by adaptive retrieval.


---

12. 🎥 Dive + YouTube

This should absolutely be implemented.

Discovery

Search
 ↓
find relevant videos
 ↓
rank video candidates

Candidate scoring:

relevance
+ channel authority
+ technical depth
+ freshness
+ transcript availability
+ topic coverage
- duplication
- low-quality signals


---

13. Don't transcribe every video

Example:

Dive discovers 15 videos
        ↓
rank
        ↓
top 3–5
        ↓
get captions/transcripts
        ↓
segment transcript
        ↓
find relevant sections

For a 2-hour conference:

2 hours
   ↓
chapters / transcript segmentation
   ↓
relevance scoring
   ↓
important 8–15 minutes
   ↓
extract claims

The final AI never needs the whole 2-hour transcript.


---

14. YouTube evidence format

Internally:

{
  "type": "youtube_evidence",
  "video_id": "...",
  "title": "...",
  "channel": "...",
  "published_at": "...",
  "segments": [
    {
      "start": 1380,
      "end": 1712,
      "text": "...",
      "importance": 0.94
    }
  ]
}

Then the final response can cite:

Video — 23:00–28:32

This makes YouTube a real evidence source, not just a recommendation.


---

15. 📄 Dive + documents

Documents should be handled similarly.

Don't:

PDF → full text → AI

Do:

PDF
 ↓
document structure
 ↓
TOC/headings/pages
 ↓
relevance scoring
 ↓
important sections
 ↓
extract passages/tables
 ↓
claims


---

16. Example: 300-page PDF

AgentWeb:

300 pages
    ↓
structure analysis
    ↓
identify relevant sections
    ↓
42 candidate pages
    ↓
semantic ranking
    ↓
15 important pages
    ↓
extract 30 evidence passages
    ↓
8 major claims

The AI gets:

Claim
Evidence
Page
Source
Confidence

Not 300 pages.


---

17. Documents should preserve location

Every extracted document fact should have:

{
  "claim": "...",
  "evidence": "...",
  "source": "...",
  "page": 37,
  "section": "3.2 Architecture"
}

For HTML:

{
  "section": "Authentication",
  "heading_path": [
    "Documentation",
    "API",
    "Authentication"
  ]
}

For YouTube:

{
  "timestamp": "23:10–28:45"
}

This gives you strong provenance.


---

18. 🕸️ Dive's crawl strategy

This is the most important part.

Wave 1 — Discovery

SearXNG
+
LibreY
+
GitHub
+
specialized discovery

Find:

40–80 candidates

Wave 2 — Evidence extraction

Select only important sources.

40–80
 ↓
20
 ↓
fetch

Wave 3 — Gap research

Analyze:

What do we still not know?

Then search only for missing information.

Wave 4 — Verification

Only if there are:

important conflicts
weak primary evidence
unverified claims

Otherwise:

STOP.


---

19. 🧠 The killer feature: Missing Evidence Detector

After every Dive wave:

KNOWN
─────
facts confidently established

UNCERTAIN
─────────
facts with weak support

CONFLICTING
───────────
sources disagree

MISSING
───────
important unanswered questions

Then:

MISSING
   ↓
generate targeted query
   ↓
search
   ↓
fetch
   ↓
update evidence graph

This prevents endless searching.


---

20. Evidence quality > result quantity

Every source should receive a score based on:

relevance
authority
primary-source status
freshness
specificity
independence
content quality
claim coverage

And penalties:

duplicate
syndicated copy
SEO spam
thin content
same-domain saturation
outdated information
irrelevant sections


---

21. Don't count duplicate websites as corroboration

This is critical.

Suppose:

Website A
Website B
Website C

all copied the same press release.

That's one evidence lineage, not three independent confirmations.

Your evidence graph should detect:

A ──┐
B ──┼── same underlying source
C ──┘

and count it accordingly.


---

22. Domain saturation

Never allow:

top 10 results

8 × same-domain

to dominate the evidence package.

Use diminishing returns:

1st source from domain → full value
2nd → reduced
3rd → heavily reduced
4th+ → only if uniquely useful


---

23. The AI should receive claims, not pages

This is probably the biggest architectural principle.

Instead of:

{
  "results": [
    {"content": "10,000 chars"},
    {"content": "15,000 chars"},
    {"content": "7,000 chars"}
  ]
}

return:

{
  "claims": [
    {
      "claim": "...",
      "evidence": "...",
      "sources": ["..."],
      "confidence": 0.94
    }
  ]
}


---

24. MCP response architecture

I'd make three levels.

compact

Default.

{
  "answer_context": [...],
  "evidence": [...],
  "citations": [...]
}

standard

{
  "answer_context": [...],
  "evidence": [...],
  "citations": [...],
  "conflicts": [...],
  "coverage": {...}
}

debug

{
  "queries": [...],
  "waves": [...],
  "providers": [...],
  "fetches": [...],
  "ranking": [...],
  "deduplication": [...],
  "timings": [...]
}

Never dump debug information into the normal model context.


---

25. Context budget

Set a hard ceiling.

For example:

Flash     2–4k tokens
Focus     4–7k
Dive      6–12k
Monitor   tiny

If evidence exceeds the budget:

rank evidence
      ↓
remove redundant passages
      ↓
merge overlapping evidence
      ↓
retain strongest source
      ↓
compress

Never just truncate randomly.


---

26. ⏱️ Hard execution budgets

Every operation gets a deadline.

Example:

flash:
  total: 8s
  search: 3s
  fetch: 3s
  compile: 2s

focus:
  total: 20s
  search: 6s
  fetch: 10s
  compile: 4s

dive:
  total: 60s
  discovery: 10s
  web_fetch: 15s
  youtube: 15s
  documents: 10s
  followup: 5s
  compile: 5s

These should be configurable.


---

27. Concurrency

Use parallel execution aggressively, but bounded.

Flash

4 concurrent operations

Focus

6–8

Dive

10–16

But implement:

global concurrency limit
per-provider limit
per-domain limit
timeout
retry
backoff

Otherwise your "free unlimited" system will get destroyed by rate limits.


---

28. "Unlimited free" needs one important clarification

You can make AgentWeb itself have no per-query paid API cost by self-hosting the open-source components.

But internet search is never literally unlimited.

Your upstream search engines can:

rate-limit

block IPs

change anti-bot systems

change result formats

temporarily fail


So the correct engineering goal is:

> No paid per-search API dependency + resilient self-hosted retrieval + multiple free/open providers + graceful fallback.



SearXNG itself is an aggregator, not an infinite independent web index. 

That's why your architecture needs provider fallback.


---

29. Provider fallback

SEARCH REQUEST
      │
      ▼
SearXNG
      │
      ├── good → continue
      │
      └── poor/failed
              ↓
            LibreY
              ↓
        direct/specialized
              ↓
        continue with what exists

Don't fail the whole research task because one provider fails.


---

30. Local/self-hosted stack

Your deployment can ultimately look like:

AgentWeb
                        │
        ┌───────────────┼────────────────┐
        │               │                │
     Search          Crawl           Evidence
        │               │                │
   SearXNG          WaterCrawl        Ranker
   LibreY           ScrapeGraphAI     Graph
        │               │             Gate
        └───────────────┼────────────────┘
                        │
                 YouTube pipeline
                        │
                 Document pipeline
                        │
                        ▼
                Context Compiler
                        │
                        ▼
                     MCP


---

31. Final mode specification

⚡ FLASH

Goal: fastest reliable answer.

1–2 queries
8–15 candidates
2–4 fetches
no deep crawl
no YouTube
no heavy document processing
1 wave
2–4 sources
2–4k-token evidence budget


---

🎯 FOCUS

Goal: reliable normal research.

3–4 research queries
20–35 candidates
5–8 fetches
SearXNG → LibreY if needed
light WaterCrawl
1 follow-up wave
4–8 sources
4–7k-token evidence budget


---

🔬 DIVE

Goal: comprehensive evidence gathering.

5–10 research dimensions
40–80 candidates
SearXNG + LibreY
GitHub
official sources
WaterCrawl
ScrapeGraphAI
YouTube
documents
academic/community sources
10–20 web fetches
3–5 important videos
3–8 important documents
2–4 research waves
8–15 final sources
6–12k-token evidence budget

But the final output remains small.


---

👁️ MONITOR

Goal: detect meaningful changes.

known sources
 ↓
cheap change detection
 ↓
only changed sources fetched
 ↓
semantic diff
 ↓
importance detection
 ↓
alert

No full research run unless necessary.


---

32. The final rule for every mode

This should be hard-coded into the architecture:

MORE RESULTS
                      ❌
                       │
                       ▼
                 MORE EVIDENCE
                      ❌
                       │
                       ▼
              BETTER EVIDENCE
                       ✅
                       │
                       ▼
              BETTER AI OUTPUT

The system should continuously ask:

> "What information would materially improve the answer?"



not:

> "What else can I scrape?"

You don't want AgentWeb to become:

> “User asks one question → call SearXNG + LibreY + GitHub + arXiv + YouTube + WaterCrawl + ScrapeGraph + documents + Reddit + everything → huge latency + huge context.”



That is tool orchestration for the sake of tool orchestration.

What you want is a Research Router / Research Planner that decides before every operation:

> What kind of evidence does this question actually require?



Then it activates only the necessary capabilities.

The core idea

USER QUERY
                        │
                        ▼
                ┌───────────────┐
                │ QUERY ANALYZER│
                └───────┬───────┘
                        │
             classify research intent
                        │
        ┌───────────────┴────────────────┐
        ▼                                ▼
   What evidence                     How deep?
   is required?                     Flash/Focus/Dive
        │                                │
        └───────────────┬────────────────┘
                        ▼
                RESEARCH PLANNER
                        │
             selects ONLY needed tools
                        │
       ┌────────────────┼─────────────────┐
       ▼                ▼                 ▼
    Web search       GitHub           Academic
       │                │                 │
       │          only if relevant       │
       └────────────────┼─────────────────┘
                        ▼
                  EVIDENCE GATE
                        │
              enough evidence?
                 /            \
               YES             NO
                │               │
                ▼               ▼
              STOP       activate next capability

The important change is:

Capabilities become conditional, not mandatory.


---

1. Build a Research Intent Classifier

Before calling anything, AgentWeb should classify the question.

For example:

Query	Intent

"What is Rust ownership?"	technical_explanation
"How does llama.cpp implement speculative decoding?"	code_repository + technical
"What changed in React 20?"	recent_technical + official
"Find papers about speech-to-speech LLMs"	academic
"Compare these 5 GitHub repos"	github
"What are developers saying about this?"	community
"Explain this 2-hour conference talk"	youtube
"Extract the architecture from this PDF"	document
"Research everything about X"	deep_multimodal
"Is this website updated?"	monitoring


The planner should produce something like:

{
  "intent": [
    "technical_explanation"
  ],
  "freshness": "low",
  "depth": "focus",
  "required_evidence": [
    "official_docs"
  ],
  "optional_evidence": [
    "technical_sources"
  ],
  "avoid": [
    "youtube",
    "academic",
    "github",
    "community"
  ]
}

Now AgentWeb knows what NOT to use.

That's just as important as knowing what to use.


---

2. Give Every Tool a "Capability Contract"

This is probably the biggest architectural improvement I'd make.

Don't let your agent arbitrarily call:

GitHub
YouTube
arXiv
Reddit
WaterCrawl
ScrapeGraph
...

Instead, every provider declares:

provider: github

capabilities:
  - source_code
  - repository_structure
  - issues
  - pull_requests
  - discussions
  - implementation_details

best_for:
  - code_questions
  - library_behavior
  - bug_investigation
  - implementation_comparison

bad_for:
  - general_news
  - scientific_literature
  - generic_explanations

cost:
  latency: medium
  context: medium
  reliability: high

Do this for every provider.

Then the planner chooses providers based on their capabilities.


---

3. Your Providers Should Have Roles

I'd organize AgentWeb into evidence families, not a giant list of tools.

🌐 Discovery

SearXNG

Primary broad web discovery.

Use when:

general research

recent information

technical discovery

news

finding documentation

finding papers

finding videos


LibreY

Secondary discovery / independent search.

Use when:

SearXNG results are weak

result diversity is low

you need a second discovery source

SearXNG provider fails


Do not automatically run both.


---

4. Official Sources Should Override Everything When Appropriate

This is extremely important for AgentWeb.

Suppose user asks:

> "How does OpenAI API structured output work?"



Don't do:

SearXNG
LibreY
Reddit
YouTube
GitHub
Academic

Instead:

Query classification
       ↓
Official documentation required
       ↓
Search official domain
       ↓
Fetch docs
       ↓
Extract relevant section
       ↓
Evidence sufficient
       ↓
STOP

That's a high-quality 1-source answer.

This is the quality-over-quantity philosophy you want.


---

5. GitHub Should Be Activated Only for Code Questions

Your GitHub integration should have very clear triggers.

Activate GitHub for:

"How does X implement..."
"Find the implementation..."
"Why does this repo..."
"Compare these repositories..."
"Was this bug fixed?"
"What changed in this PR?"
"How does this library behave?"
"Find examples of..."

Don't activate GitHub for:

"What is quantum computing?"
"Latest AI news"
"What happened in OpenAI today?"
"Explain transformers"
"Find papers about speech synthesis"

GitHub becomes a code evidence provider, not a generic search engine.


---

6. Academic Search Should Be Extremely Selective

This is another place where you're probably wasting resources.

Academic sources are useful when the question contains signals like:

paper
research
study
benchmark
SOTA
algorithm
method
architecture
dataset
publication
literature
survey
experiment
citation

Example:

> "What are the latest approaches to speech-to-speech LLMs?"



Activate:

Academic
Web
Official papers

But:

> "How does Whisper work?"



You probably don't need an academic research sweep.

You can use:

OpenAI paper
official implementation
technical documentation

Academic search becomes a research evidence provider, not another mandatory search engine.


---

7. YouTube Should Become a "Visual/Spoken Evidence Provider"

Don't use YouTube because it exists.

Activate it when:

conference talk
tutorial
demo
interview
lecture
presentation
walkthrough
podcast
hands-on explanation

Or when the query is something like:

> "Show me how this actually works."



Then:

Search
 ↓
Find videos
 ↓
Rank videos
 ↓
Select top 2–5
 ↓
Transcript/captions
 ↓
Relevant segments only
 ↓
Timestamped evidence

Not:

download 20 videos
transcribe everything
dump transcripts into context


---

8. Documents Should Be Input-Driven

Documents shouldn't be a general research provider.

If the user gives:

PDF
DOCX
PPTX
paper
specification
report
dataset documentation

then activate the document pipeline.

Or if web search discovers an important PDF:

Is PDF highly relevant?
        │
       YES
        ↓
Document extraction

Otherwise don't touch it.


---

9. WaterCrawl Should NOT Be a Search Engine

This distinction matters.

WaterCrawl should mean:

> "This website is important. Go deeper."



Not:

> "Let's crawl websites."



Example:

Search discovers:

https://docs.example.com

Source score:

relevance = 0.96
authority = 0.98

Then:

WaterCrawl
    ↓
docs.example.com
    ↓
discover relevant linked pages
    ↓
extract relevant content

But if a random blog has:

relevance = 0.31

don't crawl it.


---

10. ScrapeGraphAI Should Be Schema Extraction

WaterCrawl and ScrapeGraph should never have the same job.

Think:

WaterCrawl

> "Understand this website."



ScrapeGraphAI

> "Extract these exact things."



Example:

User asks:

> "Compare these 5 LLMs by context window, parameters, license, architecture and benchmark."



Planner:

Search
 ↓
find official model pages
 ↓
WaterCrawl if documentation is distributed
 ↓
ScrapeGraphAI
 ↓
extract:
  parameters
  context_length
  architecture
  license
  benchmarks

Output:

{
  "model": "...",
  "parameters": "...",
  "context_length": "...",
  "architecture": "...",
  "license": "...",
  "benchmarks": [...]
}

That is a very strong use case for ScrapeGraph.


---

11. Reddit / Community Should Be a Separate Evidence Class

Community evidence is useful for:

real-world experience
bugs
developer complaints
workarounds
opinions
usability
"does this actually work?"

Example:

> "Does Ollama run this model well on 16 GB RAM?"



Official documentation won't answer that fully.

Then:

Official documentation
+
GitHub issues
+
Reddit/community

But for:

> "What is the official context length?"



Reddit should be excluded.


---

12. Add a "Required Evidence Type" System

This is where AgentWeb starts becoming genuinely intelligent.

Instead of asking:

> "Which tools should I call?"



ask:

> "What evidence must exist for this answer to be trustworthy?"



For example:

Question

> "Did library X fix bug Y?"



Required:

PRIMARY:
GitHub issue / PR / commit

SECONDARY:
release notes

OPTIONAL:
community discussion

No YouTube.

No academic.

No generic web research.


---

Question

> "What does research say about model X?"



Required:

PRIMARY:
papers

SECONDARY:
official technical reports

OPTIONAL:
independent analysis

GitHub only if implementation matters.


---

Question

> "How do developers actually use X?"



Required:

GitHub
documentation
community
examples

Academic = unnecessary.


---

13. Build a Research DAG Instead of a Tool List

This is the architecture I'd aim for.

QUERY
                           │
                           ▼
                    INTENT ANALYZER
                           │
                           ▼
                    EVIDENCE PLAN
                           │
          ┌────────────────┼────────────────┐
          │                │                │
          ▼                ▼                ▼
       Official          Code            Academic
       sources          sources          sources
          │                │                │
          └────────────────┼────────────────┘
                           ▼
                    SOURCE RANKER
                           │
                           ▼
                    SELECTIVE FETCH
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
           Webpage      Document      Video
              │            │            │
              ▼            ▼            ▼
          extraction   extraction   transcript
              │            │            │
              └────────────┼────────────┘
                           ▼
                    CLAIM EXTRACTION
                           │
                           ▼
                   CORROBORATION
                           │
                           ▼
                    EVIDENCE GATE
                     /           \
                   PASS          FAIL
                    │              │
                    ▼              ▼
                   STOP       Missing evidence
                                   │
                                   ▼
                            TARGETED NEXT WAVE

This is much better than:

QUERY
 ↓
CALL EVERYTHING
 ↓
HOPE SOMETHING IS USEFUL

😂


---

14. Add "Negative Routing"

This is something I'd explicitly implement.

The planner should output both:

{
  "activate": [
    "searxng",
    "official_docs"
  ],

  "avoid": [
    "youtube",
    "github",
    "academic",
    "reddit",
    "documents"
  ]
}

Why?

Because otherwise agents tend to progressively accumulate tools.

You want the planner to actively say:

> These providers are irrelevant. Don't touch them.




---

15. Add a Tool Escalation Ladder

Don't start with expensive/deep operations.

Use:

LEVEL 0
Query classification
        ↓
LEVEL 1
Cheap discovery
        ↓
LEVEL 2
Primary source fetch
        ↓
LEVEL 3
Targeted secondary evidence
        ↓
LEVEL 4
Deep extraction
        ↓
LEVEL 5
Multimodal investigation

Example:

User:

> "What is the current Node.js LTS version?"



AgentWeb:

classification
 ↓
official Node source
 ↓
answer

Done.

Not:

SearXNG
LibreY
GitHub
Reddit
YouTube
academic
WaterCrawl
ScrapeGraph

🤣


---

16. Evidence Gate Should Control Everything

This is the heart of your system.

After each wave:

Do we know enough?

Calculate:

coverage
authority
relevance
freshness
corroboration
source diversity
conflict

For example:

{
  "coverage": 0.94,
  "authority": 0.97,
  "relevance": 0.96,
  "freshness": 0.91,
  "corroboration": 0.89,
  "conflicts": 0,
  "sufficient": true
}

Then:

STOP.

Even if only two sources were used.


---

17. Add "Research Budget"

Every query gets a budget.

Example:

budget:
  max_time: 20s
  max_sources: 8
  max_fetches: 10
  max_tokens: 7000
  max_youtube_videos: 3
  max_documents: 4
  max_crawl_depth: 1

But importantly:

These are MAXIMUMS, not targets.

If the answer is solved after:

2 sources
3 fetches
4 seconds

stop.


---

18. Add "Provider Utility Scoring"

This can make the router much smarter.

For each candidate provider:

utility =
expected_information_gain
× relevance_probability
× source_quality
÷ estimated_cost

Example:

GitHub
information_gain = 0.92
relevance = 0.95
quality = 0.94
cost = 0.30

utility = high

YouTube:

information_gain = 0.20
relevance = 0.10
quality = 0.70
cost = 0.80

utility = extremely low

Don't call it.

This is much more principled than hardcoding:

if dive:
    github()
    youtube()
    academic()


---

19. Make "DIVE" Intelligent, Not "Everything Mode"

This is especially important.

DIVE should not mean:

> Use every capability.



It should mean:

> Use whatever evidence modalities are necessary to answer the research question deeply.



For example:

Dive query A

> "Investigate how llama.cpp implements speculative decoding."



Planner:

GitHub        ✅
official docs ✅
technical web ✅
academic      🟡
YouTube       ❌
Reddit        ❌
documents     ❌

Dive query B

> "Research the state of speech-to-speech LLMs."



Academic      ✅
papers        ✅
official      ✅
YouTube       🟡
GitHub        🟡
community     🟡
documents     🟡

Dive query C

> "Analyze this company's 100-page technical report."



Document      ✅
Web           🟡
Academic      ❌
GitHub        ❌
YouTube       ❌
Reddit        ❌

That is real deep research.


---

20. Add Source-Lineage Awareness

This will make AgentWeb considerably better.

Suppose:

Website A
Website B
Website C
Website D

all copied the same announcement.

Naive AgentWeb:

4 sources agree!

Correct AgentWeb:

1 underlying source
4 syndicated copies

So:

independent_support = 1

rather than 4.

This prevents fake corroboration.


---

21. Add Domain Saturation

Same idea.

Suppose AgentWeb finds:

OpenAI blog
OpenAI docs
OpenAI announcement
OpenAI GitHub
OpenAI help page

Don't treat them as five independent perspectives.

Instead:

source_family:
    OpenAI

Then deliberately seek independent evidence only if needed.


---

22. Add "Research Completeness"

Don't measure:

> "I found 30 sources."



Measure:

> "Did I answer every important part of the question?"



Example:

User asks:

> "Compare Llama, Qwen and Mistral for local coding."



Research dimensions:

architecture
context
license
coding performance
VRAM/RAM
quantization availability
tool calling
inference speed
ecosystem

AgentWeb should track:

{
  "architecture": true,
  "context": true,
  "license": true,
  "coding_performance": true,
  "hardware_requirements": true,
  "tool_calling": false,
  "ecosystem": true
}

Then:

Missing:
tool_calling

So it performs one targeted search.

That is much better than searching again broadly.


---

23. Your MCP Response Should Be a "Context Compiler"

This is another major upgrade.

Your backend can collect:

100 pages
30 search results
4 GitHub repos
3 papers
5 videos

But the model should receive:

8 claims
12 evidence passages
3 conflicts
6 citations
1 uncertainty note

Think:

> AgentWeb is a research engine internally, but a context compiler externally.



That's a killer positioning.


---

24. Separate Execution From Evidence

Internally:

execution_trace

can contain:

queries
providers
URLs
latencies
retries
ranking
failed calls
crawl operations

But the model receives:

model_context

only.

Example:

{
  "answer_context": {
    "claims": [...],
    "evidence": [...],
    "uncertainties": [...],
    "citations": [...]
  }
}

Debug mode can expose:

/research/debug

or:

{
  "trace": {...}
}

This alone can solve a lot of your Claude-context problems.


---

25. I'd Give Your AgentWeb Providers These Exact Jobs

Capability	Provider	Trigger

Broad discovery	SearXNG	Most research
Secondary discovery	LibreY	Weak/insufficient discovery
Official docs	Web fetcher	Product/API/library questions
Source crawling	WaterCrawl	Important multi-page site
Structured extraction	ScrapeGraphAI	Schema/data extraction
Code	GitHub	Repository/implementation questions
Academic	Papers/indexes	Research/science questions
Community	Reddit/GitHub discussions	Experience/issues/opinions
Video	YouTube	Talks/tutorials/demos
Documents	Document pipeline	PDFs/reports/specifications
Monitoring	Monitor engine	Change detection


Notice something:

SearXNG and LibreY are the only generic discovery systems.

Everything else has a specialized purpose.


---

26. Then Give Your Planner This Rule

This should basically become an AgentWeb law:

NEVER CALL A PROVIDER BECAUSE IT EXISTS.

CALL A PROVIDER ONLY WHEN ITS EVIDENCE TYPE
MATCHES A RESEARCH REQUIREMENT.

And:

NEVER FETCH A SOURCE BECAUSE IT RANKS HIGH.

FETCH IT WHEN THE EXPECTED INFORMATION GAIN
JUSTIFIES THE COST.

And:

NEVER CONTINUE RESEARCH BECAUSE THE BUDGET REMAINS.

CONTINUE ONLY WHEN IMPORTANT EVIDENCE IS MISSING,
CONFLICTING, OR INSUFFICIENT.


---

