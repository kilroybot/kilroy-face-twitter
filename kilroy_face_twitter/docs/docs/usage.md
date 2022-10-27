# Usage

This package provides an interface to a Twitter bot
that complies with the **kilroy** face API.

## Prerequisites

You need to create a Twitter app and get the following credentials:

- `consumer_key`
- `consumer_secret`
- `access_token`
- `access_token_secret`

You need to pass these to the server,
either as environment variables, command line arguments
or entries in a configuration file.

For example, you can do this:

```sh
export KILROY_FACE_TWITTER_FACE__CONSUMER_KEY="Paste your consumer key here"
export KILROY_FACE_TWITTER_FACE__CONSUMER_SECRET="Paste your consumer secret here"
export KILROY_FACE_TWITTER_FACE__ACCESS_TOKEN="Paste your access token here"
export KILROY_FACE_TWITTER_FACE__ACCESS_TOKEN_SECRET="Paste your access token secret here"
```

## Running the server

To run the server, install the package and run the following command:

```sh
kilroy-face-twitter
```

This will start the face server on port 10001 by default.
Then you can communicate with the server, for example by using
[this package](https://github.com/kilroybot/kilroy-face-client-py-sdk).
