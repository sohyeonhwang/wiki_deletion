#!/usr/bin/env python3

import pandas as pd
import wikihelpers as wiki
from pathlib import Path
from bs4 import BeautifulSoup
import os
import time
from tqdm import tqdm
import random
import concurrent.futures
import requests
from urllib.parse import unquote, quote
import json 

def check_exists_and_title(page_title):
    """
    Get the page title that is pinged back to us when we make an API call, which may or may not be different from the case_title we have (e.g., it redirects). We also check if a page_exists while doing this.

    If a case_title redirects to a different page, we assume that the original page no longer exists (it was merged). Thus, page_exists = False.

    If the returned page is blank, page_exists is also False. There is somehow, no content.
    """
    page_title = unquote(page_title)
    json_response = wiki.call_parse(page_title)

    if 'error' in json_response.keys():
        print("This didn't return a JSON response with the parse key. It probably didn't lead to a page.")
        print(f" > {page_title}")
        print(f" > {json_response['error']['code']}")
        print(f" > {json_response['error']['info']}")
        page_exists = False
        returned_title = None

    # first check for a redirect - if it redirects, we don't count the page as having a page
    redirected = wiki.check_redirect(page_title,json_response)

    if redirected == True:
        page_exists = False
        returned_title = json_response['parse']['redirects'][0]['to']
        return page_exists, returned_title
    else:
        # page doesn't redirect, so we continue checking if it exists and what the returned title is
        if 'parse' in json_response.keys():
            markup = json_response['parse']['text']
            returned_title = json_response['parse']['title']
        else:
            markup = str()
            returned_title = None

        if not markup or markup.strip() == "":
            page_exists = False
        else:
            page_exists = True
    
    if page_exists == True:
        # get pageid
        pageid = json_response['parse']['pageid']
    else:
        pageid = None

    return page_exists, returned_title, pageid

def make_deletion_discussion_dict(page_title):
    # get the deletion_discussion (text, url, calculate the earliest revision)
    case_title = f"Wikipedia:Articles_for_deletion/{page_title}"
    url = f"https://en.wikipedia.org/wiki/{case_title.replace(' ', '_')}"
    text = wiki.get_raw_html(case_title)
    earliest_revision_date = wiki.get_earliest_revision(case_title)['timestamp']

    deletion_discussion_dict = {
        'case_title': case_title,
        'url': url,
        'text': text,
        'e_rev': earliest_revision_date
    }
    return deletion_discussion_dict

def process_case(page_title):
    deletion_discussion_dict = make_deletion_discussion_dict(page_title)

    # get the returned_title for the actual article/page, which also checks if page_exists for the page_title
    page_exists, returned_title, pageid = check_exists_and_title(page_title)

    return deletion_discussion_dict, page_exists, returned_title, pageid

def main():
    # load the deletion_cases
    dedup_cases = Path("deletion_cases_dedup.tsv")
    #TODO - make sure dedup keeps the first instance of a case, and marks multiple_noms as True
    # this involves going back into 0_get_deletion_cases.ipynb

    df = pd.read_csv(dedup_cases, sep="\t",header=0)
    df.sort_values(by='case_title_cleaned', inplace=True)

    # get the unique set of page_titles that are deletion_cases (case_title_cleaned)
    page_titles = df['case_title_cleaned'].drop_duplicates(keep='first').tolist()

    # initialize data
    meta_data = []

    # start processing each case... 
    #TODO - eventually, parallelize this with concurrent.futures?
    counter = 0
    for page_title in page_titles:
        filename = quote(page_title)

        # process the case, which involves about 4 API calls 
        deletion_discussion_dict, page_exists, returned_title, pageid = process_case(page_title)

        # export deletion_discussion_dict to a efficient format
        with open(f"{filename}.json", "w") as f:
            json.dump(deletion_discussion_dict, f, indent = 4)

        # store page_exists, returned_title, and pageid into a list of lists, so that we can df it later and export to tsv file 
        meta_data.append([page_title, page_exists, returned_title, pageid])

        counter += 1
        if counter % 2500 == 0:
            time.sleep(1000)
    
    # export meta_data to a DataFrame and then to a tsv file
    meta_df = pd.DataFrame(meta_data, columns=['case_title_cleaned', 'page_exists', 'returned_title', 'pageid'])
    meta_df.to_csv("deletion_cases_meta_data.tsv", sep="\t", index=False, header=True)

if __name__ == "__main__":
    main()