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

import doppler

logger = logging.getLogger(__file__)

TOPIC_ID = 3730  # abortion in us
TIMESPAN_ID = 828832 #largest
print(len(sys.argv))
if len(sys.argv) is not 3:
    logger.error("Defaulting to internal topic_id and timespan_id")
else:
    TOPIC_ID = sys.argv[1]
    TIMESPAN_ID = sys.argv[2]


DATA_DIR = 'data'
PAGE_SIZE = 500
POOL_SIZE = 20

s = requests.Session()

# load in environment (or .env file) variables
load_dotenv()
MC_API_KEY = os.getenv('MC_API_KEY')

mc = mediacloud.api.AdminMediaCloud(MC_API_KEY)


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
        'inlink_count': s['inlink_count'],
        'fb_count': s['fb_count'],
        'partisan': s['partisan']
    }


def top_images_in_timespan(topics_id, timespans_id):
    logger.info("Fetching stories by page...")
    link_id = 0
    more_pages = True
    top_images = []
    pool = Pool(processes=POOL_SIZE)
    pagesPulled = 0
    timespan_top_images = []
    while more_pages:
        logger.info("  Starting a page:")
        logger.info("    fetching story list...")
        try:
            story_page = mc.topicStoryList(topics_id=topics_id, timespans_id=timespans_id, limit=PAGE_SIZE, link_id=link_id)

        except mediacloud.error.MCException as mce:
            # when there is nno timespan (ie. an ungenerated version you are adding subtopics to)
            print(mce)
        # TODO: pull out all the story_ids in the while loop and then fetch the HTML in parallel batches to speed it up
        story_ids = [str(s['stories_id']) for s in story_page['stories']]
        logger.info("    fetching story html...")
        pagesPulled += 1
        logger.info('pages pulled ' + str(pagesPulled))
        try:
            #get inlinks and fb_counts for visualization purposes
            html_stories = mc.storyList(solr_query="stories_id:({})".format(' '.join(story_ids)), raw_1st_download=True,
                                    rows=PAGE_SIZE)
            for h in html_stories: #merge story info with raw html

                h['inlink_count'] = [s['media_inlink_count'] for s in story_page['stories'] if
                                         s['stories_id'] == h['stories_id']][0]
                h['fb_count'] = [s['facebook_share_count'] for s in story_page['stories'] if
                                         s['stories_id'] == h['stories_id']][0]

                foci = [s['foci'] for s in story_page['stories'] if
                        s['stories_id'] == h['stories_id']][0]
                h['partisan'] = [tag['foci_id'] for tag in foci if tag['focal_set_name'] == "Retweet Partisanship"]

        except mediacloud.error.MCException as mce:
            # when there is no timespan (ie. an ungenerated version you are adding subtopics to)
            print(mce)

        logger.info("    parsing out images (in parallel)...")
        try:
            timespan_top_images = pool.map(_top_image_worker, html_stories)
            for image in timespan_top_images: #yank undesirable icon pics etc from results
                test_url = str(image['top_image'])
                ignore = ["logo", "Logo", "favicon"]
                if any(x in test_url for x in ignore):
                    timespan_top_images.remove(image)
                media_id = image['metadata']['media_id'] if 'metadata' in image else 0
                if media_id == 623382 or media_id == 1751:
                    print("removing")
                    timespan_top_images.remove(image)
            logger.info("  done with page ({} top images)".format(len(timespan_top_images)))
            top_images += timespan_top_images
        except TypeError as te:
            # when there is no timespan (ie. an ungenerated version you are adding subtopics to)
            logger.info(te)


        if 'next' in story_page['link_ids']:
            link_id = story_page['link_ids']['next']
        else:
            more_pages = False
    pool.terminate()
    logger.info("Done with all pages")
    return top_images


# 1. Grab all the top image urls from stories in a timespan
top_images = top_images_in_timespan(TOPIC_ID, TIMESPAN_ID)
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
        'inlink_count': info['inlink_count'],
        'fb_count': info['fb_count'] if 'fb_count' in info else 0,
        'partisan': info['partisan']
    }
    data.append(item)

    fb_sort = True
    if fb_sort:
        sort_by = 'fb_count'
    else:
        sort_by = 'inlink_count'
#sort by fb_count or inlink_count
sorted_data = sorted(data, key=lambda k: k[sort_by])
json_file_path = os.path.join(DATA_DIR, 'images-{}-{}.json'.format(TOPIC_ID, TIMESPAN_ID))
print(len(sorted_data))
with open(json_file_path, 'w') as outfile:
    json.dump(sorted_data, outfile)

csv_file_path = os.path.join(DATA_DIR, 'images-{}-{}.csv'.format(TOPIC_ID, TIMESPAN_ID))

wr = csv.writer(open(csv_file_path, 'w'), quoting=csv.QUOTE_ALL)
wr.writerow(sorted_data[0].keys())
for row in sorted_data:
    print(row)
    wr.writerow(row.values())

logger.info("done")
