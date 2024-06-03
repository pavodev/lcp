# The LCP Database

## Data Structure

Each corpus has its own dedicated schema with mutliple tables in it; in addition, the table `main.corpus` stores metadata and structural information about how the tables relate to one another

Each entity type (also called "layer") in a corpus is associated with one or more tables; as a result, because corpora must minimally include three basic entity types (token, segment and document), each corpus will have three tables in its schema. Token and segment tables are further divided in smaller partitions of exponentially increasing size, which allows for faster, iterative querying

The main table for each entity type is reported in the `mapping` column of `main.corpus` in this way:

```
mapping
----------
{
    'layer': {
        'Document': {
            'relation': 'document'
        },
        'Segment': {
            'relation': 'segment<batch>'
        },
        'Token': {
            'relation': 'token<batch>'
        }
    }
}
```



## Indexing

## Scripts
