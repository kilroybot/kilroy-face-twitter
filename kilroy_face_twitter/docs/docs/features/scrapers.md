# Scrapers

Scrapers are used to provide a stream of existing posts.
They define a source of posts, and a way to retrieve them.
All implemented scrapers are described below.

## `TimelineScraper`

This is the only implemented scraper.
It returns the tweets from the timeline (home feed).
So it's important who the bot is following.
