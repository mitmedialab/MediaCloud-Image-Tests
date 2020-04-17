from newspaper import Article
from multiprocessing import Pool
import requests
import mediacloud.api
import os
import sys
import logging
import json
import csv
from dotenv import load_dotenv
import random

import doppler

logger = logging.getLogger(__file__)

stories_country = 'US'
print(len(sys.argv))
if len(sys.argv) is not 2:
    logger.error("Defaulting to something")
else:
   stories_country = sys.argv[1]



DATA_DIR = 'Stories'
PAGE_SIZE = 500
POOL_SIZE = 20

s = requests.Session()

# load in environment (or .env file) variables
load_dotenv()
MC_API_KEY = os.getenv('MC_API_KEY')

mc = mediacloud.api.AdminMediaCloud(MC_API_KEY)


def read_stories_from_csv(csv_file): # convenience, not currently used
    csvfile = open(csv_file, 'r')
    stories_list = []
    reader = csv.DictReader(csvfile)
    # fieldnames = reader.fieldnames
    for row in reader:
        stories_list.append(row)
    return stories_list

def top_image_from_html(url, html):
    try:
        article = Article(url=url)
        article.set_html(html)
        article.parse()
        return article.top_image
    except Exception as e:
        logger.error("error reading article " + url)

    return {}

def _top_image_worker(s):
    return {
        'stories_id': s['stories_id'],
        'metadata': s,
        'top_image': top_image_from_html(s['url'], s['raw_first_download_file']),
        #'inlink_count': s['inlink_count'],
        #'fb_count': s['fb_count'],
        #'partisan': s['partisan']
    }


def top_images_from_stories(story_list): #100 stories
    logger.info("Fetching stories by page...")
    link_id = 0
    more_pages = True
    top_images = []
    pool = Pool(processes=POOL_SIZE)
    pagesPulled = 0
    timespan_top_images = []
   
        
        # TODO: pull out all the story_ids in the while loop and then fetch the HTML in parallel batches to speed it up
    story_ids = [str(s['stories_id']) for s in story_list]
    logger.info("    fetching story html...")
    pagesPulled += 1
    logger.info('pages pulled ' + str(pagesPulled))
    try:
            #get inlinks and fb_counts for visualization purposes
        html_stories = mc.storyList(solr_query="stories_id:({})".format(' '.join(story_ids)), raw_1st_download=True, rows=PAGE_SIZE)
                #for h in html_stories: #merge story info with raw html

                #h['inlink_count'] = [s['media_inlink_count'] for s in story_page['stories'] if s['stories_id'] == h['stories_id']][0]
                #h['fb_count'] = [s['facebook_share_count'] for s in story_page['stories'] if s['stories_id'] == h['stories_id']][0]
                #foci = [s['foci'] for s in story_page['stories'] if
                
                #h['partisan'] = [tag['foci_id'] for tag in foci if tag['focal_set_name'] == "Retweet Partisanship"]
                #s['stories_id'] == h['stories_id']][0]
    
    except mediacloud.error.MCException as mce:
            # when there is no timespan (ie. an ungenerated version you are adding subtopics to)
        print(mce)

    logger.info("    parsing out images (in parallel)...")
    try:
        random_story_top_images = pool.map(_top_image_worker, html_stories)
        for image in random_story_top_images:
            test_url = str(image['top_image'])
            ignore = ["logo", "Logo", "favicon"]
            if any(x in test_url for x in ignore):
                random_story_top_images.remove(image)
        #if media_id is the guardian remove
            media_id = image['metadata']['media_id'] if 'metadata' in image else 0
            print(media_id)
            if media_id == 623382 or media_id == 1751:
                print("removing")
                random_story_top_images.remove(image)
        logger.info("  done with page ({} top images)".format(len(random_story_top_images)))
        top_images += random_story_top_images
    except TypeError as te:
            # when there is no timespan (ie. an ungenerated version you are adding subtopics to)
        logger.info(te)

    pool.terminate()
    logger.info("Done with all pages")
    return top_images


# 1. Grab all the top image urls from csv from a query
csv_file_path = os.path.join(DATA_DIR, '{}-Stories.csv'.format(stories_country))

stories_list = read_stories_from_csv(csv_file_path)

random_list = random.choices(stories_list, k=250)
top_images = top_images_from_stories(random_list)
top_images = [t for t in top_images if len(t['top_image']) > 0]  # remove stories with no top image
top_images = [t for t in top_images if 'favicon' not in t['top_image'] and 'logo' not in t['top_image'] and 'Logo' not in t['top_image'] and '623382' not in str(t['metadata']['media_id']) and '1751' not in str(t['metadata']['media_id'])]

# 2. Write out JSON to use with doppler mosaic (hopefully)
logger.info("Writing to json")
data = []
for info in top_images:
    item = {
        'image_url': info['top_image'],
        'stories_id': info['metadata']['stories_id'],
        'media_id': info['metadata']['media_id'],
        'story_title': info['metadata']['title'],
        'story_url': info['metadata']['url'],
        'media_name': info['metadata']['media_name'],
        'media_url': info['metadata']['media_url'],
        'publish_date': info['metadata']['publish_date'],
        #'inlink_count': info['inlink_count'],
        #'fb_count': info['fb_count'],
        #'partisan': info['partisan']
    }
    data.append(item)

#sort by fb_count
sorted_data = sorted(data, key=lambda k: k['publish_date'])
json_file_path = os.path.join(DATA_DIR, '{}.json'.format(stories_country))
with open(json_file_path, 'w') as outfile:
    json.dump(sorted_data, outfile)

csv_file_path = os.path.join(DATA_DIR, '{}.csv'.format(stories_country))

wr = csv.writer(open(csv_file_path, 'w'), quoting=csv.QUOTE_ALL)
wr.writerow(sorted_data[0].keys())
for row in sorted_data:
    print(row)
    wr.writerow(row.values())

logger.info("done")
