# Import Swissdox data to LCP

1. export data from Swissdox DB
	1.a content
		file:		export_content.sql
		comment:	no idea, where the WHERE clause is coming from/what it should achieve
		output:		file with content_id, raw XML per line
	2.b meta data
		file:		get_metadata.sql
		comment:	the WHERE restrictions here should also be applied to content export!
		output:		TSV with id, metadat-columns per line

==> steps 2-5 are managed through Makefile
2. parse raw XML and perform language identification
	file: 		Swissdox2LCP_langident.py
	comment:	reads from STDIN
	output:		file with language, type, content lines
				IMPORTANT: type = id signals new article start (i.e. order of lines significant)

3. compute CoNLL-U
	file:		Swissdox2LCP_conll.py
	comment:	reads from STDIN
	output:		compressed CoNLL-U .txts with meta info in header (article_id, confidence language etc.)

4. compute NEs
	file:		Swissdox2LCP_ner.py
	comment:	reads from STDIN

5. compute sentence embeddings
	file:		Swissdox2LCP_vectors.py
	comment:	reads from STDIN
<==

6. compute SQL table content
	file:		process_swissdox_new.py
	output:		TSVs corresponding to the table structure in the DB

7. adjust ranges
    file:		adjust_ranges_idxs.py
	output:		TSVs with updated range values

8. upload data (via batch-COPY)
	file:		import_data.py

