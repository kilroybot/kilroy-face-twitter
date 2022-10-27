# Score modifiers

Score modifiers are a way to modify the score of a post,
independent of the score given by the scorer.
This can be useful to constraint the score to a certain range,
or to reduce the score of risky posts.
Their usage is optional.
All implemented score modifiers are listed below.

## `ToxicityScoreModifier`

This score modifier uses the [`Detoxify`](https://github.com/unitaryai/detoxify)
model to calculate the toxicity of a post.
The toxicity is then used to modify the score of the post,
greatly reducing the score of toxic posts.
You can configure the toxicity threshold and reduction factor.
