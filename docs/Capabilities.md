
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

