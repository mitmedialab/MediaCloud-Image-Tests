import os
import pandas as pd
from tqdm import tqdm
import sys
import torch
from torch import nn
from torch.utils.data.dataset import Dataset
from torch.utils.data import DataLoader
from torchvision import models, transforms
import logging
import csv
import json

from doppler import skip_hash, cols_conv_feats, filename_without_extension
from doppler.image_utils import read_and_transform_image

logger = logging.getLogger(__file__)

# Are we using a GPU? If not, the device will be using cpu
device = torch.device('cuda:1' if torch.cuda.is_available() else 'cpu')


def load_resnet_for_feature_extraction():
    # Load a pre-trained model
    res50_model = models.resnet50(pretrained=True)
    # Pop the last Dense layer off. This will give us convolutional features.
    res50_conv = nn.Sequential(*list(res50_model.children())[:-1])
    res50_conv.to(device)
    # Don't run backprop!
    for param in res50_conv.parameters():
        param.requires_grad = False
    # we won't be training the model. Instead, we just want predictions so we switch to "eval" mode.
    res50_conv.eval()
    return res50_conv


class FeatureExtractionDataset(Dataset):
    """Dataset wrapping images and file names
    img_col is the column for the image to be read
    index_col is a unique value to index the extracted features
    """
    def __init__(self, df, img_col, index_col, transformations):
        # filter out rows where the file is not on disk.
        self.X_train = df.drop_duplicates(subset=index_col).reset_index(drop=True)
        self.files = self.X_train[img_col]
        self.idx = self.X_train[index_col]
        self.transformations = transformations

    def __getitem__(self, index):
        img_idx = self.idx[index]
        img_file = self.files[index]
        try:
            img = read_and_transform_image(self.files[index], self.transformations)
            return img, img_file, img_idx
        except:
            pass

    def __len__(self):
        return len(self.X_train.index)


# reduce batch_size if running low on memory
def build(json_file_path, logits_file_path, image_path_property='f_img', index_property='d_hash', batch_size=64):
    logger.info("Starting to build logits file")
    logger.info("  reading {}...".format(json_file_path))
    df = pd.read_json(json_file_path,  orient='records')
    logger.info("  loaded {} records ".format(df.shape[0]))
    df = df[~df[index_property].isin(skip_hash)] #ignore records w no hash
    # Set up chain to transform images into the Tensors needed by PyTorch
    # The image needs to be specific dimensions, normalized, and converted to a Tensor to be read into a PyTorch model.
    scaler = transforms.Resize((224, 224))
    to_tensor = transforms.ToTensor()
    normalizer = transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    # this is the order of operations that will occur on each image.
    transformations = transforms.Compose([scaler, to_tensor, normalizer])

    # load up anything we've already processed
    abd = []
    if os.path.exists(logits_file_path):
        logger.info("  Read existing logits file: {}".format(logits_file_path))
        abd = pd.read_csv(logits_file_path, index_col=0).index.tolist()

    # now set up the dataset to run the transforms on
    dataset = FeatureExtractionDataset(df[~df[index_property].isin(abd)],
                                       img_col=image_path_property,
                                       index_col=index_property,
                                       transformations=transformations)
    data_loader = DataLoader(dataset,
                             batch_size=batch_size,
                             shuffle=False,
                             num_workers=8)
    res50_conv = load_resnet_for_feature_extraction()
    logger.info("  Processing data...".format(logits_file_path))
    # now go through our data
    for (X, img_file, idx) in tqdm(data_loader):
        X = X.to(device)
        logits = res50_conv(X)
        # logits.size() # [`batch_size`, 2048, 1, 1])
        logits = logits.squeeze()  # remove the extra dims
        # n_dimensions = logits.size(1)
        logits_dict = dict(zip(idx, logits.cpu().data.numpy()))
        # {'filename' : np.array([x0, x1, ... x2047])}
        df_conv = pd.DataFrame.from_dict(logits_dict,
                                         columns=cols_conv_feats,
                                         orient='index')
        # add a column for the filename of images...
        df_conv[image_path_property] = img_file
        if idx == 10: # show a sample
            logger.info("  loaded this {} conv record ".format(df_conv))
        # write to file
        if os.path.exists(logits_file_path):
            df_conv.to_csv(logits_file_path, mode='a',
                           header=False, compression='gzip')
        else:
            df_conv.to_csv(logits_file_path, compression='gzip')
    logger.info("Done")


if __name__ == "__main__":
    json_path = sys.argv[1]
    logger.info("Reading from {}".format(json_path))
    logits_file_path = './{}-logits.csv.gz'.format(json_path.replace('.json', ''))

    build(json_path, logits_file_path, image_path_property='image_path')
