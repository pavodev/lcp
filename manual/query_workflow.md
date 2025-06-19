# Overhaul

## _query

BE saves request-specific parameters (offset, total_requested, resume, to_export) in redis
and query-wide values (corpus id, languages, latest results, etc.) in first job's meta

_query callback sends ONE message over PUBSUB

_query sock pushes 1+ WS msgs to FE and submits sentences/meta + next queries as necessary


## _sentences / _meta

_sentences / _meta callback sends 1+ messages over PUBSUB, containing the respective results of _format_kwics

_sentences / _meta sock pushes 1 WS message each time it is called


# LCP's query workflow

<p align="center"> <!-- Doesnt work, I wanted to center it, but it's not that important -->
  <img src="images/lcp_query_workflow.svg" alt="alt" width="550"/>
</p>

Note that the query parameters start off as part of the request (or are passed as `manual`)
then are passed a initialiazing values to a new `QueryIteration` object
and passed down as `kwargs` to either `redis.publish` or to a new `Job`

They are then fetched by a callback method either directly as `kwargs` (if called directly)
or as `job.kwargs` (if called as a redis job's callback) and sent back to the app via `_publish_msg`

The app finally retrieves the data in `_process_message` either from the message itself
(if sent directly from `redis.publish`) or from redis's memory (using `msg_id` from the payload)