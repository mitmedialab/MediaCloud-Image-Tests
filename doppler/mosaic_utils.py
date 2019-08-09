import os
from rasterfairy import transformPointCloud2D
from PIL import Image, ImageFont, ImageDraw
from tqdm import tqdm
import numpy as np
import csv
import json

from doppler.image_utils import resize_image

def make_csv_and_json_with_data(data):
    sorted_data = sorted(data, key=lambda k: k['fb_count'])
    json_file_path = os.path.join(DATA_DIR, 'images-{}-{}.json'.format(TOPIC_ID, TIMESPAN_ID))
    with open(json_file_path, 'w') as outfile:
        json.dump(sorted_data, outfile)

    csv_file_path = os.path.join(DATA_DIR, 'images-{}-{}.csv'.format(TOPIC_ID, TIMESPAN_ID))

    wr = csv.writer(open(csv_file_path, 'w'), quoting=csv.QUOTE_ALL)
    wr.writerow(sorted_data[0].keys())
    for row in sorted_data:
        wr.writerow(row.values())

def generate_mosaic(embeddings, images, fb_counts, titles, origins, urls, mosaic_width, mosaic_height,
                    tile_width=150, tile_height=100, title="Doppler Mosaic",
                    title_rbg=(255, 255, 255), save_as_file='mosaic.png',
                    return_image=True, verbose=False):
    """
    Transforms 2-dimensional embeddings to a grid. 
    Plots the images for each embedding in the corresponding grid (mosaic).
    Includes arguments for the dimensions of each tile and the the mosaic.
    """
    # assign to grid
    grid_assignment = transformPointCloud2D(embeddings,
                                            target=(mosaic_width,
                                                    mosaic_height))
    full_width = tile_width * mosaic_width
    full_height = tile_height * (mosaic_height + 2)
    aspect_ratio = float(tile_width) / tile_height

    # create an empty image for the mosaic
    mosaic = Image.new('RGB', (full_width, full_height))
    html_header = """
     <html>
          <link rel="stylesheet" href="https://ajax.googleapis.com/ajax/libs/jqueryui/1.12.1/themes/smoothness/jquery-ui.css">
      <script src="https://ajax.googleapis.com/ajax/libs/jquery/3.4.1/jquery.min.js"></script>
<script src="https://ajax.googleapis.com/ajax/libs/jqueryui/1.12.1/jquery-ui.min.js"></script>
     <style>
        .data {
            background-color: white;
        }
        .icon {
            width: 50px;
            height: 50px;
        }
     </style>
     <body>
        <div>
     """
    html_footer = """
    </div>
    <script>
    $(".data" ).hide();
    $( document ).tooltip();
    


        $(".images").hover(
  function() {
    $( this ).css("border", "2px solid red");
    $( this ).css("cursor","pointer");
  }, function() {
    $( this ).css("border", "none");
    $( this ).css("cursor","default");
  }
);
     </script>
    </body>
    </html>


    """
    html_file_path = save_as_file
    if save_as_file:
        html_file_path = save_as_file.replace('png','html')
    html_file = open(html_file_path, "w")
    html_file.write(html_header)
    fnt = ImageFont.truetype('/Library/Fonts/Arial.ttf', 20)
    # iterate through each image and where it is possed to live.
    for f_img, fb_count, title, origin, url, (idx_x, idx_y) in tqdm(zip(images, fb_counts, titles, origins, urls, grid_assignment[0]),
                                      disable=not verbose):
        # Find exactly where the image will be
        x, y = tile_width * idx_x, tile_height * idx_y
        media_origin_img = "https://www.google.com/s2/favicons?domain={}".format(origin)
        # read the image, center crop the image and add it to the mosaic
        try:
            img_format = "<a href='{}' target='_blank'><img class='images' src='{}' width='{}' height='{}' title='{} shares, {}' /></a>".format(url, f_img, tile_width, tile_height, fb_count, title)
            html_file.write(img_format)
            html_file.write("<img class='icon' src='{}' alt='{}' title='{}' />".format(media_origin_img, origin, origin))
            #html_file.write(data_format)
            img = Image.open(f_img).convert('RGBA')
            tile = resize_image(img, tile_width, tile_height, aspect_ratio)
            tileDraw = ImageDraw.Draw(tile)
            tileDraw.text((4, 4),
                      " {}".format(fb_count), fill=250, font=fnt)
            mosaic.paste(tile, (int(x), int(y)))
        except Exception as e:
            print(f"Failed to add image {f_img} see error:\n{e}")

            # write an annotation

    draw = ImageDraw.Draw(mosaic)
    draw.text((4, (tile_height * mosaic_height) + 10),
              title, title_rbg, font=fnt)
    html_file.write(html_footer)
    html_file.close()

    if save_as_file and not os.path.exists(save_as_file):
        try:
            mosaic.save(save_as_file)
        except Exception as e:
            print(f'Saving the mosaic to {save_as_file} failed, see error:\n{e}')

    if return_image:
        return mosaic


def scatterplot_images(embeddings, images, fb_counts, titles, origins,
                       width=2000, height=1100,
                       max_dim=40):
    """
    Plots images in a scatterplot where coordinates are from
    embeddings.
    """
    tx, ty = embeddings[:, 0], embeddings[:, 1]
    tx = (tx - np.min(tx)) / (np.max(tx) - np.min(tx))
    ty = (ty - np.min(ty)) / (np.max(ty) - np.min(ty))

    full_image = Image.new('RGB',
                           size=(width, height),
                           color=(55, 61, 71))
    fnt = ImageFont.truetype('/Library/Fonts/Arial.ttf', 20)
    for f_img, fb_count, title, x, y in tqdm(zip(images, fb_counts, titles, tx, ty)):
        # read and resize image
        tile = Image.open(f_img)
        rs = max(1, tile.width / max_dim, tile.height / max_dim)
        tile_width = int(tile.width / rs)
        tile_height = int(tile.height / rs)
        aspect_ratio = float(tile_width) / tile_height
        tile = resize_image(tile,
                            tile_width,
                            tile_height,
                            aspect_ratio)
        tileDraw = ImageDraw.Draw(tile)
        tileDraw.text((2, 2),
                      "{}".format(fb_count), fill=250, font=fnt)
        draw = ImageDraw.Draw(full_image)
        draw.text((4, (tile_height * height) + 10),
                  title, fill=200, font=fnt)
        # add the image to the graph               
        x_coord = int((width - max_dim) * x)
        y_coord = int((height - max_dim) * y)
        img_coords = (x_coord, y_coord)
        full_image.paste(tile,
                         box=img_coords,
                         mask=tile.convert('RGBA'))

    return full_image
