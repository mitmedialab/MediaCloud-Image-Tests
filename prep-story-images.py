import os
import json
import sys
import logging
import pandas as pd
from multiprocessing import Pool
import json
import csv
from doppler.image_utils import download_media_and_return_dhash, NO_HASH

"""
Download all the images from a sample file into the examples directory (parrelelized for speed).
You have to do this yourself because we can't commit the images to the repo due to US copyright restrictions.

Note: this doesn't do any smart throttling by domain, so there is a chance you'll be spammy and rude
to domain owners if a lot of the images are from the same domain.
"""

logger = logging.getLogger(__file__)


POOL_SIZE = 10

if len(sys.argv) is not 2:
    logger.error("You must pass in a path to a .json file, like examples/caravan-news-images.json")
    sys.exit()
file_name = sys.argv[1]


def _image_worker(row):
    dest_image_fn = os.path.join(image_dir_path, str(row['stories_id']))
    dest_image_fn = "{}.jpg.jpg".format(dest_image_fn) #ensure jpg..  TODO issue
    logger.info("image {}".format(dest_image_fn))
    try:
            # This will *not* re-download if a file is there
        d_hash, img_size = download_media_and_return_dhash(row['image_url'], dest_image_fn)
        row['deleted'] = (img_size == 0)
        row['d_hash'] = d_hash
        row['image_path'] = os.path.abspath(dest_image_fn)
        row['img_size'] = img_size
    except OSError as e:
            # happens when the image file doesn't download right
        logger.info("get image dhash failed {}".format(e))
        row['deleted'] = True
        row['d_hash'] = NO_HASH
        row['image_path'] = os.path.abspath(dest_image_fn)
        row['img_size'] = 0
    return row



def rewrite_json_from_csv(json_path): # convenience, not currently used
    csv_file = "{}".format(json_path).replace('json','csv')
    csvfile = open(csv_file, 'r')
    jsonfile = open(json_path, 'w')


    reader = csv.DictReader(csvfile)
    # fieldnames = reader.fieldnames
    for row in reader:
        json.dump(row, jsonfile)
        jsonfile.write('\n')


if __name__ == "__main__":

    json_path = file_name
    # read in the sample data


    logger.info("Reading from {}".format(file_name))
    #data = [json.loads(line) for line in open(json_path, 'r')]

    with open(json_path, 'r') as f:
        data = json.load(f)
    # set up a place to put the images
    image_dir_path = './{}-files'.format(file_name.replace('.json', ''))
    if not os.path.exists(image_dir_path):
        os.makedirs(image_dir_path)
    logger.info("Will save images to {}".format(image_dir_path))
    # download each image and grab relevant metadata
    logger.info("Starting parallel download of {} images...".format(len(data)))
    #pooling isn't working reliably for me so am commenting out
    # pool = Pool(processes=POOL_SIZE)
    # updated_data = pool.map(_image_worker, data)
    # pool.terminate()
    updated_data =[]
    for d in data:
        #has_fb_count = d['fb_count'] # for my purposes, I only want pics that have fb links
        #has_inlink_count = d['inlink_count']  # for my purposes, I only want pics that have fb links
        #if int(has_inlink_count) > 60:
        logger.info("data...{} {}".format(len(updated_data), d))
        row = _image_worker(d)
        updated_data.append(row)
    logger.info("done")
    # update json with relevant metadata

    with open(json_path, 'w') as outfile:
        json.dump(updated_data, outfile)
    logger.info("done w updated json file")


    image_dir_path_csv = "{}-dataset.csv".format(file_name.replace('.json', ''))
    newlist = sorted(updated_data, key=lambda k: k['publish_date'])
    wr = csv.writer(open(image_dir_path_csv, 'w'), quoting=csv.QUOTE_ALL)
    wr.writerow(newlist[0].keys())
    for row in newlist:
        print(row)
        wr.writerow(row.values())


