# Deletion Cases on English Wikipedia
Collecting and curating a set of article deletion cases (from the Articles for Deletion logs) for analysis.

These scripts should allow you to:
* Crawl through all the logs of the `https://en.wikipedia.org/wiki/Wikipedia:Archived_articles_for_deletion_discussions`
* Get all the deletion cases (Articles for Deletion) from each day in the logs
* Cleans this into one `pandas` DataFrame that removes cases that are have been nominated more than once (in my use case, I only care about articles that have been nominated for deletion once)
* Get the raw HTML of each deletion discussion as a single string
* Extract the decisions from each discussion
* Identifies the deletion cases that still exist and are likely "keep"
* Matches each kept, existing article to roughly 100 similar articles ~2022 embeddings
* Gets more relevant metadata for the rough matches for a CEM match
* CEM of each kept, existing article that went through AfD to a untreated article on enwiki
* Notebook of data analysis of this matched sample

Your directory should be set up like this:

* `./venv` (unless you have a `conda` environment)
* `./repo` (this one)
    * (contains the scripts for collecting and pulling together data)
* `./deletion_cases`
    * `deletion_cases_YYYY_MM_uncleaned.tsv`
    * nb: this is the output of running `0_get_deletion_cases*.py`
* `./deletion_discussions`
    * `chunk_iii.tsv`
    * nb: this is one of the outputs of `0_get_case_data.py`
    * TODO - re-format to `pageid.tsv`
* `./revisions`
    * `{pageid}_revisionhistory.tsv`
    * nb: this is one of the outputs of `1_get_case_data.py`
* `./rough_n_matches`
    * `{pageid}_n_matches.tsv` where each row is a rough match, and there are n (=100) rows
    * nb: this is the output of `3_rough_match_n.py`

Additionally, the additional following data files/directories are generated (via the scripts in the repo) or downloaded:
* `./wikipda_data` (dl from `https://github.com/epfl-dlab/WikiPDA/tree/master/WikiPDA-Lib`)
    * lang
        * enwiki.json (this is very large)
* `log_links_YYYYMMDD_TIME.tsv` --- generated from `./repo/0_get_deletion_cases.py` when recollect is set to `True`
* `deletion_cases_dedup.tsv` --- generated from using `./repo/0_get_deletion_cases.py` to combine and dedup everything in `./deletion_cases`
* `full_df.tsv` --- combined with the WikiPDA data, we create with `./repo/2_build_full_df.py`: 
    * `pageid | qid | treated | embeddings | creation_date | afd_date | keep_heuristic`
        * `treated` indicates it was 
        * We get `creation_date` and `afd_date` from the revision_history data and case data we've been collecting
        * calculate the `keep_heuristic` which is that the creation_date < afd_date - 90 days AND page_exists
    * this dataset is the basis for doing our rough matches in `3_rough_match_n.py`

More to come. Basically, we will also need scripts that collect and then organize metadata about rough matches in a convenient format. Then, CEM.

