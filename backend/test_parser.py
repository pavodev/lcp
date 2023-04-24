import dqd_parser

dqd_query = """
Turn d
    IsPresident = no
    PoliticalGroup != NI

Segment@d s

sequence seq
    Token@s t1
        upos = DET
    Token@s t2
        upos = ADJ
    Token@s t3
        upos = NOUN
        lemma.length > 5

set tdeps
    Token@s tx
        DepRel
            head = t3
            dep = tx


Token thead
    upos = VERB
    DepRel
        head = thead
        dep = t3

myKWIC1 => plain
    context
        s
    entities
        t1
        t2
        t3

myKWIC2 => plain
    context
        s
    entities
        seq

myStat1 => analysis
    attributes
        t1.lemma
        t2.lemma
        t3.lemma
    functions
        frequency
    filter
        frequency > 10

myStat2 => analysis
    attributes
        t3.lemma
        d.OriginalLanguage
    functions
        frequency
    filter
        frequency > 10

myColl1 => collocation
    center
        t3
    window
        -5..+5
    attribute
        lemma

myColl2 => collocation
    space
        tdeps
    attribute
        upos
    comment
        PoS collocations of all dependends

myColl3 => collocation
    space
        thead
    attribute
        lemma

"""

dqd_json = dqd_parser.convert(dqd_query)
print(dqd_json)
