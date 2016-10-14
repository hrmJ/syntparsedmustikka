CREATE INDEX fi_token_index ON fi_conll(token) WHERE deprel NOT in ('punct', 'PUNC');
