import logging

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] {%(module)s:%(lineno)d} %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

# shared variables
skip_hash = ['NOHASH', '0000000000000000', 'nan']
n_dimensions = 2048  # features from resnet50, change this is you change the model in feature extraction.
cols_conv_feats = [f'conv_{n}' for n in range(n_dimensions)]
