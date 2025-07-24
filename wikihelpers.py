#!/usr/bin/env python3
 
import pandas as pd
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import unquote, quote
from copy import deepcopy
import requests, re
import wikifunctions as wf
from pathlib import Path

def chunk_list(lst, n):
    k, m = divmod(len(lst), n)
    return [lst[i*k + min(i, m):(i+1)*k + min(i+1, m)] for i in range(n)]

def call_query(page_title, endpoint='en.wikipedia.org/w/api.php', redirects=1):
    # Get the response from the API for a query
    # After passing a page title, the API returns the HTML markup of the current article version within a JSON payload
    #req = requests.get('https://{2}.wikipedia.org/w/api.php?action=parse&format=json&page={0}&redirects={1}&prop=text&disableeditsection=1&disabletoc=1'.format(page_title,redirects,lang))    
    query_url = "https://{0}".format(endpoint)
    query_params = {}
    query_params['action'] = 'query'
    query_params['titles'] = unquote(page_title)
    query_params['redirects'] = redirects
    query_params['prop'] = 'pageprops'
    query_params['ppprop'] ='wikibase_item'
    query_params['format'] = 'json'

    json_response = requests.get(url = query_url, params = query_params).json()
    
    return json_response['query']

def call_parse(page_title, endpoint='en.wikipedia.org/w/api.php', redirects=1):
    query_url = "https://{0}".format(endpoint)
    query_params = {}
    query_params['action'] = 'parse'
    query_params['page'] = unquote(page_title)
    query_params['redirects'] = redirects
    query_params['prop'] = 'text'
    query_params['disableeditsection'] = 1
    query_params['disabletoc'] = 1
    query_params['format'] = 'json'
    query_params['formatversion'] = 2
    
    json_response = requests.get(url = query_url, params = query_params).json()
    
    return json_response

"""
functions that rely on the query call
"""
def retrieve_ids(page_title, endpoint='en.wikipedia.org/w/api.php', redirects=1):
    # Get the response from the API for a query
    # After passing a page title, the API returns the HTML markup of the current article version within a JSON payload
    #req = requests.get('https://{2}.wikipedia.org/w/api.php?action=parse&format=json&page={0}&redirects={1}&prop=text&disableeditsection=1&disabletoc=1'.format(page_title,redirects,lang))
    json_response = call_query(page_title, endpoint=endpoint, redirects=redirects)

    if "pages" in json_response:
        if '-1' in json_response['pages']:
            # no page! 
            print(f"Found an error where a page does not exist: {page_title}")
            page_exists = False
        else:
            pages = list(json_response['pages'].keys())
            if len(pages) > 1:
                print(f" > Weirdly, there are multiple pages for {page_title}: {pages}")

                page_exists = True
                pageid = pages

                qids = []
                for i in pages:
                    if 'pageprops' in json_response['pages'][pages[0]]:
                        if 'wikibase_item' in json_response['pages'][pages[0]]['pageprops']:
                            q = json_response['pages'][pages[0]]['pageprops']['wikibase_item']
                            qids.append(q)
                qid = qids
            elif len(pages) == 0:
                print(f" > Weirdly, there are no pages even though the page for {page_title} apparently exists. This should not happen.")
                page_exists = False
                pageid = None
                qid = None
            else:
                # there should be exactly one page in the returned json response
                page_exists = True
                if 'pageid' in json_response['pages'][pages[0]]:
                    pageid = json_response['pages'][pages[0]]['pageid']
                else:
                    print(f" > Weirdly, we could not get the pageid for {page_title}, even though the page exists. This should not happen.")
                    pageid = None

                if 'pageprops' in json_response['pages'][pages[0]]:
                    if 'wikibase_item' in json_response['pages'][pages[0]]['pageprops']:
                        qid = json_response['pages'][pages[0]]['pageprops']['wikibase_item']
                else:
                    print(f"{page_title} has no qid")
                    qid = None

    return pageid, qid

def get_qid(page_title):
    p, q = retrieve_ids(page_title)
    return q

def get_pageid(page_title):
    p, q = retrieve_ids(page_title)
    return p

def title_to_filename(page_title):
    """
    Convert a page title to a filename-friendly format.
    """
    filename = quote(page_title)
    filename = filename.replace("/", "_")  # replace slashes to avoid file path issues
    return filename

def filename_to_title(filename):
    """
    Convert a filename back to a page title.
    """
    filename = filename[:-5]
    filename = filename.replace("_", "/")  # replace underscores back to slashes
    title = unquote(filename)
    return title

"""
functions that rely on the parse call (or other things requiring it, like revision history)
"""
def check_redirect(page_title,json_response):
    if 'parse' in json_response.keys():
        redirect_map = json_response['parse']['redirects']
        if len(redirect_map) > 0:
            # if there are redirects, we assume the page no longer exists
            #print(f" > {page_title} redirects to {redirect_map[0]['to']}")
            return True
        else:
            # no directs, so we assume the page exists
            return False
    else:
        return "ERROR_NO_PARSE_KEY"

def get_raw_html(page_title):
    """
    Wrapped for calling the function in wikifunctions.
    This is a parse call.
    """
    page_title = unquote(page_title)
    markup_string = wf.get_page_raw_content(page_title)
    return markup_string

def get_revisions(page_title):
    """
    Wrapper for calling the function in wikifunctions.
    This return a df with 'ids|comment|timestamp|user|size|sha1' #userid - userid is commented out because it causes problems for me
    It saves the revisions to a file in the ./revisions directory.
    This is a query call. 
    """
    page_title = title_to_filename(unquote(page_title))
    revisions_file = Path(f"./revisions/{page_title}_revisions.tsv")
    if revisions_file.exists():
        df = pd.read_csv(revisions_file, sep="\t", header=0)
        #print(f"Revisions for {page_title} already exist in {revisions_file}.")
    else:
        df = wf.get_all_page_revisions(page_title)
        output = f"./revisions/{page_title}_revisions.tsv"
        df.to_csv(output, sep="\t", index=False)
        #print(f"Revisions for {page_title} saved to {output}.")

    return df

def get_earliest_revision(page_title, endpoint='en.wikipedia.org/w/api.php', redirects=1):
    # Get the revision history for the page
    # if it's not already cached in folder revisions as {page_title}_revisions_df.tsv

    # Set up the query
    query_url = f"https://{endpoint}"

    query_params = {}
    query_params['action'] = 'query'
    query_params['titles'] = unquote(page_title)
    query_params['prop'] = 'revisions'
    query_params['rvprop'] = 'ids|comment|timestamp|user|size|sha1' #userid
    query_params['rvlimit'] = 1
    query_params['rvdir'] = 'newer'
    query_params['format'] = 'json'
    query_params['redirects'] = redirects
    query_params['formatversion'] = 2

    json_response = requests.get(url = query_url, params = query_params).json()

    return json_response['query']['pages'][0]['revisions'][0]


#TODO 
def temp(page_title):
    revisions_file = Path(f"./revisions/{page_title}_revisions.tsv")
    if revisions_file.exists():
        revisions_df = pd.read_csv(revisions_file, sep="\t", header=0)
    else:
        # if file does not exist, fetch with wf and save
        revisions_df = get_revisions(page_title)
    
    if revisions_df is None or revisions_df.empty:
        print(f"No revisions found for {page_title}.")
        return None, None
    else:
        # get the date and revid id of the earliest revision
        earliest_revision = revisions_df.loc[revisions_df['timestamp'].idxmin()]
        earliest_revision_date = earliest_revision['timestamp']
        earliest_revision_id = earliest_revision['revid']

    return earliest_revision_date, earliest_revision_id