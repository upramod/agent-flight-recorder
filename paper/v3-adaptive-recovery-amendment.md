# Adaptive execution amendment, 2026-10-07 UTC

The original run 37549518814 completed all 84 fixed cells and 120 clean cells. Azure returned HTTP429 in each adaptive shard. The conservative unknown-usage guard charged each failure the remaining token budget, preventing subsequent calls. Of84 adaptive campaigns,7 completed and77 remained incomplete; four campaigns also recorded parser errors. Neither error type counts as resistance.

Retain that run unchanged. Run a separate replication of all84 model-a adaptive campaigns, including earlier successes and failures, on the same28 pairs and allthree arms in the same scheduled order. All campaigns begin from the fixed first payload in a fresh environment. Later candidates are generated afresh from that campaign's feedback. Do not merge successful original campaigns into the replication or select campaigns based on outcomes.

Only execution handling changes: one shard job runs at a time; pace physical API calls by one second; retry HTTP429 only, with60seconds between attempts and at most6 physical attempts for an identical logical request. Every physical request is logged before transport and its terminal event follows. SDK and AgentDojo retries remain0. An exhausted429 remains an explicit error with zero reported inference tokens, rather than consuming the remaining budget. Other unknown-usage failures retain the conservative stop. All token, prompt, model, policy, generation, task and scoring settings remain frozen.

This is an exploratory replication under amended transport handling, not an untouched preregistered result. Report its errors and missingness. The second-model slot remains unrun without a verified distinct deployment.
