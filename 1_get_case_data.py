#!/usr/bin/env python3

import pandas as pd
import wikihelpers as wiki
from pathlib import Path
import time
from tqdm import tqdm
import concurrent.futures
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
        #print(f"> {page_title} didn't return a JSON response with the parse key. It probably didn't lead to a page.")
        #print(f" > {page_title}")
        #print(f" > {json_response['error']['code']}")
        #print(f" > {json_response['error']['info']}")
        page_exists = False
        returned_title = None

    # first check for a redirect - if it redirects, we don't count the page as having a page
    redirected = wiki.check_redirect(page_title,json_response)

    if redirected == True:
        page_exists = False
        returned_title = json_response['parse']['redirects'][0]['to']
        pageid = "REDIRECTED"
        return page_exists, returned_title, pageid
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

    json_response = wiki.call_parse(case_title)

    if 'error' in json_response.keys():
        #print(f"> {case_title} didn't return a JSON response with the parse key. It probably didn't lead to a page.")
        text = "DISCUSSION_DOES_NOT_EXIST"
        earliest_revision_date = None
    else:
        text = wiki.get_raw_html(case_title)
        earliest_revision_date = wiki.get_earliest_revision(case_title)['timestamp']

    deletion_discussion_dict = {
        'case_title': case_title,
        'url': url,
        'text': text,
        'e_rev_date': earliest_revision_date
    }
    return deletion_discussion_dict

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

def process_case(page_title):
    parent_dir=Path.cwd().parent
    #print(page_title)
    try:
        deletion_discussion_dict = make_deletion_discussion_dict(page_title)

        # get the returned_title for the actual article/page, which also checks if page_exists for the page_title
        page_exists, returned_title, pageid = check_exists_and_title(page_title)

        # exporting the deletion discussion dict to a json file
        filename = title_to_filename(page_title)
        with open(parent_dir / "deletion_discussions" / f"{filename}.json", "w") as f:
            json.dump(deletion_discussion_dict, f, indent = 4)
        
        return [page_title, page_exists, returned_title, pageid]
    except Exception as e:
        print(f"Exception for {page_title}: {e}")

        # log the page_title in a file that logs errors
        # afterwards, we will run the script on cases that had errors
        with open(parent_dir / "case_meta_data" / "1_errors.log", "a") as f:
            f.write(f"{page_title}\t{e}\n")

        return None

def main():
    # directory hygiene
    parent_dir = Path.cwd().parent

    if not (parent_dir / "case_meta_data").exists():
        (parent_dir / "case_meta_data").mkdir(parents=True, exist_ok=True)
    if not (parent_dir / "deletion_discussions").exists():
        (parent_dir / "deletion_discussions").mkdir(parents=True, exist_ok=True)

    # load the deletion_cases
    dedup_cases = parent_dir / "deletion_cases_sorted_dedup.tsv" #"deletion_cases_sorted_dedup.tsv"
    print(f"Loading the deletion cases from file: {dedup_cases}")

    df = pd.read_csv(dedup_cases, sep="\t",header=0)
    df.sort_values(by='case_title_cleaned', inplace=True)

    # get the unique set of page_titles that are deletion_cases (case_title_cleaned)
    page_titles = df['case_title_cleaned'].drop_duplicates(keep='first').tolist()
    print(len(page_titles), "cases to process.")

    # chunking so that we can process a bit smarter when dealing with errors
    chunk_size = 100
    page_titles_chunked = wiki.chunk_list(page_titles, chunk_size)

    print(f"Processing {len(page_titles_chunked)} chunks of cases, each with up to {chunk_size} cases.")

    input("Start?")

    for i, chunk in enumerate(page_titles_chunked):  
        # start timer 
        start_time = time.time()
        chunk_outfile = parent_dir / "case_meta_data" / f"chunk_{i+1}.tsv"

        print(f"Processing chunk {i+1}/{len(page_titles_chunked)} with {len(chunk)} cases.")

        # use concurrent future to apply process_case to each item in chunk in parallel
        with concurrent.futures.ProcessPoolExecutor(max_workers=10) as executor:
            chunk_results = list(tqdm(executor.map(process_case, chunk), total=len(chunk)))
        
        meta_data = [r for r in chunk_results if r is not None]
        
        # make into df and export
        meta_df = pd.DataFrame(meta_data, columns=['case_title_cleaned', 'page_exists', 'returned_title', 'pageid'])
        meta_df.to_csv(chunk_outfile, sep="\t", index=False, header=True)

        # print how long it took to process the chunk
        elapsed_time = time.time() - start_time
        print(elapsed_time, "seconds to process chunk", i+1)

        if (i + 1) % 100000 == 0:
            print(f"Processed {i + 1} chunks. Waiting for 3 hours to avoid API limits.")
            time.sleep(60 * 60 * 3)
        # for every 50th chunk (5000 pages), we wait 15 minutes to avoid hitting API limits
        elif (i + 1) % 50 == 0:
            print(f"\nProcessed {i + 1} chunks. Waiting for 15 minutes to avoid API limits.\n")
            time.sleep(15 * 60)
    
    # open 1_errors.log and count how many lines there are
    error_log_file = parent_dir / "case_meta_data" / "1_errors.log"
    if error_log_file.exists(): 
        with open(error_log_file, "r") as f:
            error_lines = f.readlines()
        print(f"Number of errors to redo: {len(error_lines)}")

if __name__ == "__main__":
    main()