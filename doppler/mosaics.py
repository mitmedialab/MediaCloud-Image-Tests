import os
import pandas as pd
from sklearn.externals import joblib
import umap
import logging

from doppler import cols_conv_feats, skip_hash
import doppler.mosaic_utils as mosaic_utils

logger = logging.getLogger(__file__)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')


def build(logits_file_path, full_metadata_file_path, sample_dataset_file_path,
          date_col_name='created_at', image_path_property='f_img'):
    logging.info("Starting to build mosaic")
    # Reduce Dimensions

    # UMAP Params
    n_neighbors = 25
    metric = 'euclidean'
    min_dist = 0.5
    training_set_size = 500 #10000
    overwrite_model = False  # set to True to re-train the model.

    # Model files
    file_encoder = (f'{DATA_DIR}/encoder_{str(min_dist).replace(".", "-")}_'
                    f'dist_{metric}_sample_{training_set_size}.pkl')
    file_training_set = f'{DATA_DIR}/umap_training_data_{training_set_size}.csv'

    if not os.path.exists(file_encoder) or overwrite_model:
        logger.info("  Building a new UMAP embeddings model...")
        # Create the training set (note: UMAP can be either supervised or unsupervised.)
        if not os.path.exists(file_training_set):
            df_conv = pd.read_csv(logits_file_path,
                                  index_col=0,
                                  compression='gzip')
            training_set = df_conv[cols_conv_feats].sample(training_set_size, random_state=303)
        else:
            training_set = pd.read_csv(file_training_set,
                                       index_col=0)

        # fit the model scikit-learn style
        encoder = umap.UMAP(n_neighbors=n_neighbors,
                            min_dist=min_dist,
                            metric=metric,
                            random_state=303,
                            verbose=1).fit(training_set.values)

        # save the model for later! Save the training data, too.
        joblib.dump(encoder, file_encoder)
        training_set.to_csv(file_training_set)
        logger.info("  done")
    else:
        logger.info("  Loading existing embeddings model")
        encoder = joblib.load(file_encoder)
        encoder

    # Join the image metadata with convolutional features
    """
    if not os.path.exists(full_metadata_file_path):
        # Read image metadata
        df_media = pd.read_csv(sample_dataset_file_path,
                               compression='gzip')
        df_media = df_media[~df_media['d_hash'].isin(skip_hash)]
        print(len(df_media))

        df_conv = pd.read_csv(logits_file_path,
                              index_col=0,
                              compression='gzip')
        print(len(df_conv))
        # Merge the datasets
        merge_cols = [c for c in df_media.columns if c != image_path_property]
        df_merged = (pd.merge(left=df_media[merge_cols],
                              right=df_conv.reset_index(),
                              how='left',
                              left_on='d_hash',
                              right_on='index').sort_values(by=date_col_name,
                                                            ascending=True))
        df_merged[date_col_name] = pd.to_datetime(df_merged[date_col_name])
        df_merged.to_csv(full_metadata_file_path,
                         compression='gzip')
    else:
        df_merged = pd.read_csv(full_metadata_file_path,
                                index_col=0,
                                compression='gzip')
        df_merged[date_col_name] = pd.to_datetime(df_merged[date_col_name],
                                                  format='%Y-%m-%d %H:%M:%S')
    """
    logger.info("  Read in logits from {}".format(logits_file_path))
    df_merged = pd.read_csv(logits_file_path, index_col=0, compression='gzip')

    # build the mosaic
    # variables for the mosaic
    # tile_width, tile_height = 36, 28  # pixel dimenstions per image
    nx, ny = 50, 40  # number of images in the x and y axis
    sample_size = min(nx * ny, df_merged.shape[0])
    # aspect_ratio = float(tile_width) / tile_height
    # sample the dataset
    df_sample = df_merged.sample(sample_size, random_state=303)
    # min_date = df_sample[date_col_name].min()
    # max_date = df_sample[date_col_name].max()
    images = df_sample[image_path_property]
    embeddings = encoder.transform(df_sample[cols_conv_feats].values)

    # build the scatterplot
    scatterplot_image_path = os.path.join(DATA_DIR, 'scatterplot.png')
    logging.info("  Building scatterplot image to {}...".format(scatterplot_image_path))
    image = mosaic_utils.scatterplot_images(embeddings, images, width=2400, height=1800, max_dim=100)
    image.save(scatterplot_image_path)
    logging.info("  done")

    # and now make the mosaic
    tile_width, tile_height = 36, 2
    mosaic_file_path = os.path.join(DATA_DIR, 'mosaic.png')
    logging.info("  Building mosaic image to {}...".format(mosaic_file_path))
    mosaic_utils.generate_mosaic(embeddings, images,
                                 mosaic_width=nx, mosaic_height=ny,
                                 tile_width=tile_width, tile_height=tile_height,
                                 save_as_file=mosaic_file_path, verbose=True, return_image=True,
                                 title="Mosaic of Caravan News")
    logging.info("Done")


if __name__ == "__main__":
    logits_file_path = os.path.join('./', 'examples', 'caravan-news-images-logits.csv.gz')
    full_metadata_file_path = os.path.join('./', 'examples', 'caravan-news-images-metadata.csv.gz')
    sample_dataset_file_path = os.path.join('./', 'examples', 'caravan-news-images-dataset.csv.gz')
    build(logits_file_path, full_metadata_file_path, sample_dataset_file_path,
          date_col_name='publish_date', image_path_property='image_path')
