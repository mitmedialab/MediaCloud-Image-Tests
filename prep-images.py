import os
import json
import sys
import logging
from multiprocessing import Pool

from doppler.image_utils import download_media_and_return_dhash, NO_HASH

"""
Download all the images from a sample file into the examples directory (parrelelized for speed).
You have to do this yourself because we can't commit the images to the repo due to US copyright restrictions.

Note: this doesn't do any smart throttling by domain, so there is a chance you'll be spammy and rude
to domain owners if a lot of the images are from the same domain.
"""

logger = logging.getLogger(__file__)

POOL_SIZE = 20

if len(sys.argv) is not 2:
    logger.error("You must pass in a path to a .json file, like examples/caravan-news-images.json")
    sys.exit()
file_name = sys.argv[1]


def _image_worker(row):
    dest_image_path = os.path.join(image_dir_path, str(row['stories_id']))
    try:
        # This will *not* re-download if a file is there
        d_hash, img_size = download_media_and_return_dhash(row['image_url'], dest_image_path)
        row['deleted'] = (img_size == 0)
        row['d_hash'] = d_hash
        row['image_path'] = os.path.abspath(dest_image_path)
        row['img_size'] = img_size
    except OSError:
        # happens when the image file doesn't download right
        row['deleted'] = True
        row['d_hash'] = NO_HASH
        row['image_path'] = os.path.abspath(dest_image_path)
        row['img_size'] = 0
    return row


if __name__ == "__main__":
    # read in the sample data
    logger.info("Reading from {}".format(file_name))
    json_path = file_name
    with open(json_path, 'r') as f:
        data = json.load(f)
    # set up a place to put the images
    image_dir_path = '{}-files'.format(file_name.replace('.json', ''))
    if not os.path.exists(image_dir_path):
        os.makedirs(image_dir_path)
    logger.info("Will save images to {}".format(image_dir_path))
    # download each image and grab relevant metadata
    logger.info("Starting parallel download of {} images...".format(len(data)))
    pool = Pool(processes=POOL_SIZE)
    updated_data = pool.map(_image_worker, data)
    pool.terminate()
    logger.info("done")
    # update json with relevant metadata
    with open(json_path, 'w') as outfile:
        json.dump(updated_data, outfile)
    logger.info("Updated data in {}".format(file_name))
