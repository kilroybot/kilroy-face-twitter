# Restrictions

Score modifiers are a way to modify the score of a post given by the scorer.
This can be useful to constraint the score to a certain range,
or to reduce the score of risky posts.
Their usage is optional.
All implemented restrictions are listed below.

## `ToxicityRestriction`

This restriction uses the [`Detoxify`](https://github.com/unitaryai/detoxify)
model to calculate the toxicity of a post.
Posts with a toxicity above the configured threshold are rejected.
You can configure the toxicity threshold.
