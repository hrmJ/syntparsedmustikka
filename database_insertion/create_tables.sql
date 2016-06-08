CREATE TABLE
	ru_conll
		(
		tokenid BIGINT,
		token VARCHAR,
		lemma VARCHAR,
		pos VARCHAR,
		feat VARCHAR,
		head SMALLINT,
		deprel VARCHAR,
		sentence_id BIGINT,
		align_id BIGINT,
		text_id BIGINT,
		translation_id BIGINT,
		id SERIAL PRIMARY KEY
		);
CREATE TABLE
	fi_conll
		(
		tokenid BIGINT,
		token VARCHAR,
		lemma VARCHAR,
		pos VARCHAR,
		feat VARCHAR,
		head SMALLINT,
		deprel VARCHAR,
		sentence_id BIGINT,
		align_id BIGINT,
		text_id BIGINT,
		translation_id BIGINT,
		id SERIAL PRIMARY KEY
		);
CREATE TABLE
	text_ids
		(
		id SERIAL PRIMARY KEY,
		title VARCHAR,
        source_blog VARCHAR,
        post_id VARCHAR,
        parsedate VARCHAR,
		author VARCHAR,
		translator VARCHAR,
		origtitle VARCHAR,
		transtitle VARCHAR,
		origyear SMALLINT,
		transyear SMALLINT,
		origpublisher VARCHAR,
		transpublisher VARCHAR,
		genre VARCHAR

		);
CREATE TABLE
	translation_ids
		(
		id SERIAL PRIMARY KEY,
		sourcetext_id      BIGINT references text_ids(id),
		title VARCHAR,
		translator VARCHAR,
		year SMALLINT,
		publisher VARCHAR,
		genre VARCHAR
		);


CREATE TABLE groups
(
  id serial NOT NULL,
  name character varying,
  sentence_id bigint,
  corpus character varying,
  CONSTRAINT groups_pkey PRIMARY KEY (id)
)
WITH (
  OIDS=FALSE
);
ALTER TABLE groups
  OWNER TO juho;
