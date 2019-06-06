from newspaper import Article
from multiprocessing import Pool
import mediacloud.api
import os
import logging
import json
from dotenv import load_dotenv

import doppler

logger = logging.getLogger(__file__)

TOPIC_ID = 2981  # caravan and migration
TIMESPAN_ID = 346026
DATA_DIR = 'data'
PAGE_SIZE = 1000
POOL_SIZE = 20

# load in environment (or .env file) variables
load_dotenv()
MC_API_KEY = os.getenv('MC_API_KEY')

mc = mediacloud.api.AdminMediaCloud(MC_API_KEY)


def top_image_from_html(url, html):
    article = Article(url=url)
    article.set_html(html)
    article.parse()
    return article.top_image


def _top_image_worker(s):
    return {
        'stories_id': s['stories_id'],
        'metadata': s,
        'top_image': top_image_from_html(s['url'], s['raw_first_download_file'])
    }


def top_images_in_timespan(topics_id, timespans_id):
    logger.info("Fetching stories by page...")
    link_id = 0
    more_pages = True
    top_images = []
    pool = Pool(processes=POOL_SIZE)
    while more_pages:
        logger.info("  Starting a page:")
        logger.debug("    fetching story list...")
        story_page = mc.topicStoryList(topics_id=topics_id, timespans_id=timespans_id, limit=PAGE_SIZE, link_id=link_id)
        # TODO: pull out all the story_ids in the while loop and then fetch the HTML in parallel batches to speed it up
        story_ids = [str(s['stories_id']) for s in story_page['stories']]
        logger.debug("    fetching story html...")
        html_stories = mc.storyList(solr_query="stories_id:({})".format(' '.join(story_ids)), raw_1st_download=True,
                                    rows=PAGE_SIZE)
        logger.debug("    parsing out images (in parallel)...")
        timespan_top_images = pool.map(_top_image_worker, html_stories)
        logger.info("  done with page ({} top images)".format(len(timespan_top_images)))
        top_images += timespan_top_images
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
    }
    data.append(item)
file_path = os.path.join(DATA_DIR, 'images-{}-{}.json'.format(TOPIC_ID, TIMESPAN_ID))
with open(file_path, 'w') as outfile:
    json.dump(data, outfile)
logger.info("done")
