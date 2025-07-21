#!/usr/bin/env python3

import pandas as pd
from datetime import datetime
from bs4 import BeautifulSoup
import wikifunctions as wf
import re
#import argparse
from pathlib import Path

def extract_date_link(link):
    match = re.search(r'/Log/(\d{4}) (\w+) (\d{1,2})', link.get_text())
    link = link.get('href')
    if match:
        year = int(match.group(1))
        month = match.group(2)
        day = int(match.group(3))

        return [year, month, day, link]

    else:
        print("We couldn't find a date for {}".format(link))
        return [0,0,0,link]

def collect_all_log_links(archive_homepage, initialized_log_links, output_tsv_name):
    """
    Go through the archives/logs of deletion discussion to get links to all the daily logs for the years 2007 - present
    """
    # soup the home archive page
    soup = BeautifulSoup( archive_homepage , features="html.parser")

    # we can get daily log links for years that are not yet archived directly from this page
    a_tags = soup.find_all("a")
    links = [a for a in a_tags if a['href'].startswith("/wiki/Wikipedia:Articles_for_deletion/Log/")]

    # building our list of lists 
    for link in links:
        _sublist = extract_date_link(link)
        #print(_sublist)
        initialized_log_links.append(_sublist)

    # for earlier years, we need to go to each year:
    yearly_archives = [a for a in a_tags if a['href'].startswith("/wiki/Wikipedia:Archived_articles_for_deletion_discussions/20")]
    for year in yearly_archives:
        #print(year.get_text())

        # we go to the actual page of that year's archive, extract each month's links
        soup = BeautifulSoup( wf.get_page_raw_content(year.get_text()) , features="html.parser")
        months = soup.find_all("div", class_="mw-parser-output")[0].find_all('ul')
        for m in months:
            links = m.find_all('a')

            for link in links:
                _sublist = extract_date_link(link)
                print(_sublist)
                initialized_log_links.append(_sublist)
    
    output = pd.DataFrame(initialized_log_links, columns=['year','month','day','log_link'])
    # 2003 and 2004 are weirdly formatted, so there is a 0 placeholder. drop those.
    output = output[output['year'] != 0]
    output.to_csv(output_tsv_name,sep='\t',index=False,header=True)

def get_deletion_cases(log_page_link, case_list_output):
    # open log page and soup it
    title = log_page_link[6:]
    #print(title)
    soup = BeautifulSoup( wf.get_page_raw_content(title), features="html.parser")

    # get all the deletion cases for that day
    # block > boilerplate afd vfd xfd-closed archived
    cases = soup.find_all("div", class_=lambda classes: classes and 'boilerplate' in classes)

    # case title > mw-heading mw-heading3
    for c in cases[1:]:
        if c.find("div", class_="mw-heading mw-heading3"):
            case_title = c.find("div", class_="mw-heading mw-heading3").get_text()
            case_discussion_url = f"Wikipedia:Articles_for_deletion/{case_title}"
        else:
            # these will need to be corrected in post!
            ## some of these are not actually cases, but other things with same div class. BUT we should still have someone check what is going on here...
            case_title = None
            case_discussion_url = None

        # look for multiple nominations noted = "AfDs for this article:"
        block = c.find(string=lambda text: text and "AfDs for this article:" in text)
        if block:
            multiple_noms = True
        else:
            multiple_noms = False

        formatted_case = [log_page_link, case_title, case_discussion_url, multiple_noms]
        #print(formatted_case)

        case_list_output.append(formatted_case)

def main():
    archive_link = "Wikipedia:Archived_articles_for_deletion_discussions" #https://en.wikipedia.org/wiki/
    archive_home = wf.get_page_raw_content(archive_link)

    # ADJUST THIS IF YOU WANT TO RECOLLECT ALL THE LOG LINKS
    recollect = False
    if recollect == True:
        log_links = []
        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_output_file = f"./../log_links_{now}.tsv"

        # get all the links to daily logs in a tsv file
        collect_all_log_links(archive_home,log_links,log_output_file)
        print(f"Created {log_output_file} with {len(log_links)} daily log links.")
        return 
    else:
        print("Using an existing list of daily log links.")

    log_link_file = input("Enter the log link file to use: (e.g., ./../log_links_20250624_145626.tsv) ")

    # go to each daily log link and extract all the cases into a tsv
    log_link_df = pd.read_csv( log_link_file ,sep='\t')

    months = ["January", "February", "March", "April", "May", "June","July", "August", "September", "October", "November", "December"]

    months_to_numbers = {"January": "01", "February": "02", "March": "03", "April": "04", "May": "05", "June": "06", "July": "07", "August": "08", "September": "09", "October": "10", "November": "11", "December": "12"}

    # let's do this by year and month, so that we can chunk it up a bit
    # 2003 and 2004 have to do with other script, format is different, so we will not collect those here.
    start_year = 2005
    end_year = 2025
    case_output_dir = Path.cwd().parent / 'deletion_cases'

    for i in list(range(start_year,end_year+1)):
        subset_year_df = log_link_df[log_link_df['year']==i]
        for m in months:
            n = months_to_numbers[m]
            if (case_output_dir / f"deletion_cases_{i}_{n}_uncleaned.tsv").exists():
                print(f"{i}, {m} has already been collected.")
                continue

            print(i, m)
            subset_month_df = subset_year_df[subset_year_df['month']==m]
            print(subset_month_df.head())
            daily_logs = subset_month_df['log_link'].tolist()
            cases = []
            for link in daily_logs:
                get_deletion_cases(link, cases)

            # cases for this year and month should now be populated
            cases_df = pd.DataFrame(cases,columns=["log_link", "case_title", "case_discussion_url", "multiple_noms"])
            # add year, month, day columns from the log_link_file's df based on log_link shared column
            merged_df = pd.merge(cases_df, log_link_df, on='log_link', how='left')
            print(merged_df.head())

            # export
            # remember we need to correct the None cases...
            case_output_file = case_output_dir / f"deletion_cases_{i}_{n}_uncleaned.tsv"
            merged_df.to_csv(case_output_file,sep="\t",index=False,header=True)
            print(f"Created {case_output_file}")

if __name__ == "__main__":
    main()