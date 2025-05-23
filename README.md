# Deletion Cases on English Wikipedia
Collecting and curating a set of article deletion cases (from the Articles for Deletion logs) for analysis.

These scripts should allow you to:
* Crawl through all the logs of the `https://en.wikipedia.org/wiki/Wikipedia:Archived_articles_for_deletion_discussions`
* Get all the deletion cases (Articles for Deletion) from each day in the logs
* Cleans this into one `pandas` DataFrame that removes cases that are have been nominated more than once (in my use case, I only care about articles that have been nominated for deletion once)
* Get the raw HTML of each deletion discussion as a single string
* Extract the decisions from each discussion
