import logging
import os

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] {%(module)s:%(lineno)d} %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

# shared variables
skip_hash = ['NOHASH', '0000000000000000', 'nan']
n_dimensions = 2048  # features from resnet50, change this is you change the model in feature extraction.
cols_conv_feats = ['conv_{}'.format(n) for n in range(n_dimensions)]


def filename_without_extension(path):
    base = os.path.basename(path)
    file_name_parts = os.path.splitext(base)
    return file_name_parts[0]
