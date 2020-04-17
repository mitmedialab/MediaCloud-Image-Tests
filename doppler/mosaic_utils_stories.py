import os
from rasterfairy import transformPointCloud2D
from PIL import Image, ImageFont, ImageDraw
from tqdm import tqdm
import numpy as np
import csv
import json

from doppler.image_utils import resize_image

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

javacript_load_img_section = """
    <script>
    var canvas = document.getElementById("scatter");
    var context = canvas.getContext("2d");
    function loadImages(url, x, y) {
        var img = new Image;
        img.src = url;
        img.onload = function(){
            context.drawImage(img, x, y);
        };
    }
    </script>
"""

def make_csv_and_json_with_data(data):
    sorted_data = sorted(data, key=lambda k: k['publish_date'])
    json_file_path = os.path.join(DATA_DIR, 'images-{}-{}.json'.format(story_country))
    with open(json_file_path, 'w') as outfile:
        json.dump(sorted_data, outfile)

    csv_file_path = os.path.join(DATA_DIR, 'images-{}-{}.csv'.format(story_country))

    wr = csv.writer(open(csv_file_path, 'w'), quoting=csv.QUOTE_ALL)
    wr.writerow(sorted_data[0].keys())
    for row in sorted_data:
        wr.writerow(row.values())

def generate_mosaic(embeddings, images, titles, origins, urls, mosaic_width=1000, mosaic_height=1000, tile_width=150, tile_height=100,
                    title_rbg=(255, 255, 255), save_as_file='mosaic.png',
                    fb_counts=None,partisanship=None,verbose=True,
                    return_image=True, title="Doppler Mosaic" ):
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
    #print(grid_assignment)
    # create an empty image for the mosaic
    mosaic = Image.new('RGB', (full_width, full_height))

    # iterate through each image and where it is possed to live.
    for f_img, (idx_x, idx_y) in tqdm(zip(images, grid_assignment[0]),
                                      disable = False):
        # Find exactly where the image will be
        x, y = tile_width * idx_x, tile_height * idx_y
        
        # read the image, center crop the image and add it to the mosaic
        try:
            img = Image.open(f_img).convert('RGBA')
            tile = resize_image(img, tile_width, tile_height, aspect_ratio)
            mosaic.paste(tile, (int(x), int(y)))
        except Exception as e:
            print(f"Failed to add image {f_img} see error:\n{e}")

    draw = ImageDraw.Draw(mosaic)
        #draw.text((4, (tile_height * (mosaic_height)) + 10),title, title_rbg, font=fnt)
        
    if save_as_file and not os.path.exists(save_as_file):
        try:
            mosaic.save(save_as_file)
        except Exception as e:
            print(f'Saving the mosaic to {save_as_file} failed, see error:\n{e}')

    if return_image:
        return mosaic


def scatterplot_images(embeddings, images, titles, origins, urls,save_as_file='scatterplot.png',
                fb_counts=None,partisanship=None,
                       width=2000, height=1100,
                       max_dim=40):
    """
    Plots images in a scatterplot where coordinates are from
    embeddings.
    """
    # I think we could merge author/site info here in a quadrant kind of way.. think think think
    tx, ty = embeddings[:, 0], embeddings[:, 1]
    tx = (tx - np.min(tx)) / (np.max(tx) - np.min(tx))
    ty = (ty - np.min(ty)) / (np.max(ty) - np.min(ty))


    html_file_path = save_as_file
    if save_as_file:
        html_file_path = save_as_file.replace('png','html')
    html_file = open(html_file_path, "w")
    html_file.write(html_header)
    html_file.write('<img alt="Image Map"  src="{}"  usemap="#imagemap" />'.format(save_as_file))
    html_file.write('<map name="imagemap">')

    html_file.write(javacript_load_img_section)
    scatterplot = Image.new('RGB',
                           size=(width, height),
                           color=(55, 61, 71))
    fnt = ImageFont.truetype('/Library/Fonts/Arial.ttf', 20)
    for f_img, title, origin, url, x, y in tqdm(zip(images, titles, origins, urls, tx, ty)):
        # read and resize image
        tile = Image.open(f_img)
        #media_origin_img = "https://www.google.com/s2/favicons?domain={}".format(origin)


        rs = max(1, tile.width / max_dim, tile.height / max_dim)
        tile_width = int(tile.width / rs)
        tile_height = int(tile.height / rs)
        aspect_ratio = float(tile_width) / tile_height
        tile = resize_image(tile,
                            tile_width,
                            tile_height,
                            aspect_ratio)
        tileDraw = ImageDraw.Draw(tile)
            #tileDraw.text((2, 2),"{}".format(fb_count), fill=250, font=fnt)
        draw = ImageDraw.Draw(scatterplot)
        draw.text((4, (tile_height * height) + 10),
                  title, fill=200, font=fnt)
        # add the image to the graph               
        x_coord = int((width - max_dim) * x)
        
        y_coord = int((height - max_dim) * y)
        img_coords = (x_coord, y_coord)
        scatterplot.paste(tile,
                         box=img_coords,
                         mask=tile.convert('RGBA'))

        try:
            #img_format = "<a href='{}' target='_blank'><img class='images' src='{}' width='{}' height='{}' title='{} shares, {}' /></a>".format(
            #    url, f_img, tile_width, tile_height, fb_count, title)
            #html_file.write(img_format)

            html_file.write('<area href="{}" shape="rect" coords="{}, {}, {}, {}" />'.format(url, x_coord, y_coord, x_coord + tile_width, y_coord + tile_height))
            img = Image.open(f_img).convert('RGBA')
            tile = resize_image(img, tile_width, tile_height, aspect_ratio)
            tileDraw = ImageDraw.Draw(tile)
            #tileDraw.text((4, 4)," {}".format(fb_count), fill=250, font=fnt)
            scatterplot.paste(tile, (int(x), int(y)))
        except Exception as e:
            print(f"Failed to add image {f_img} see error:\n{e}")

    html_file.write("</map>")
    html_file.write(html_footer)
    html_file.close()
    # write an annotation
    return scatterplot

