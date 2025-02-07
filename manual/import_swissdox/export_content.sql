COPY (
	SELECT content_id, content
	FROM core.content
	WHERE substr(content_id::text, 1, 3) = '@'
) TO STDOUT
