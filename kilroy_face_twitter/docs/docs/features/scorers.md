# Scorers

Scorers are a way to evaluate posts.
You give them a tweet, and they return a single number representing the score.
All implemented scorers are described below.

## `RelativeLikesScorer`

This scorer returns the number of likes a tweet has
divided by the number of followers the tweet author has.

## `RelativeRetweetsScorer`

This scorer returns the number of retweets a tweet has
divided by the number of followers the tweet author has.

## `IRelativempressionsScorer`

This scorer returns the number of impressions a tweet has
divided by the number of followers the tweet author has.
