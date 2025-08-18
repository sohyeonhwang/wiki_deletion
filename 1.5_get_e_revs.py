#!/usr/bin/env python3

import pandas as pd
import wikihelpers as wiki
from pathlib import Path
from tqdm import tqdm
from urllib.parse import unquote, quote
import json 
import traceback
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--input', type=str, help='Path to the input JSON file containing case titles.')
parser.add_argument('--type', type=str, help='`content` if the input file contains pages for content articles. `afd` if input file contains pages for deletion discussions.')

def main():
    # read in the input file
    parent_dir = Path.cwd().parent
    input_path = parent_dir / args.input

    print(input_path)

    df = pd.read_csv(input_path, header=0, sep="\t")

    if args.type == "content":
        df = df[df['page_exists'] ==True]
        pages = df['returned_title'].tolist()
    if args.type == "afd":
        pages = df['case_title_cleaned'].tolist()


    ##CHUNKIFY
    chunk_size = 100  
    page_titles_chunked = wiki.chunk_list(pages, chunk_size)

    print(f"Processing {len(page_titles_chunked)} chunks of cases, each with up to {chunk_size} cases.")
    print(f"The last chunk is smaller: {len(page_titles_chunked[-1])}")

    input("Start?")

    for i, chunk in enumerate(page_titles_chunked):

        #print(chunk)

        dates = []

        output_path = parent_dir / "case_meta_data" / f"1.5_earliest_revisions_{args.type}_{i+1:04d}.tsv"
        if output_path.exists():
            print(f"> Chunk {i+1} already processed into {output_path}, skipping.")
            continue

        for page_title in tqdm(chunk):

            if args.type == "afd":
                page_title = f"Wikipedia:Articles for deletion/{page_title}"

            print(page_title)
            # get earliest revision
            try:
                dates.append([page_title, wiki.get_earliest_revision(page_title)])
            except Exception as e:
                print(f"Error processing {page_title}: {e}")
                traceback.print_exc()
                dates.append([page_title, None])

                with open(parent_dir / "case_meta_data" / "1.5_errors.log", "a") as f:
                    f.write(f"{i+1}\t{page_title}\t{e}\n")
                        
        # dates to dataframe
        df_dates = pd.DataFrame(dates, columns=['page_title', 'earliest_revision_date'])
        
        df_dates.to_csv(output_path, sep="\t", index=False)
        print(f"Saved earliest revisions to {output_path}")

if __name__ == "__main__":
    args = parser.parse_args()

    main()