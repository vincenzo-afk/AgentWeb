# Manifesto

1. **Intent, not connectors.** Nobody should have to choose between `search()`, `crawl()`, and `browser.extract()` to answer a simple question. Describe the goal; let the platform choose the mechanism.
2. **Nothing ungrounded.** Every claim in a synthesized answer traces to a source. An answer without evidence is a liability, not a feature.
3. **Memory is not optional.** Treating the web as stateless wastes compute and misses the most important information: what changed.
4. **Explainability is not a UI feature, it's an architectural requirement.** If a system can't show its work, it can't be trusted for anything that matters.
5. **The internet is an event stream, not just a document store.** The long-term win isn't answering more questions faster — it's noticing what changed before anyone had to ask.
6. **Learning compounds.** A platform that remembers which strategies worked gets better and cheaper over time; one that replans from scratch every time never does.

See [docs/vision.md](../../docs/vision.md) and [docs/architecture.md](../../docs/architecture.md) for how these principles map to the actual system.
