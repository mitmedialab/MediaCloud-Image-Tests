MediaCloud + Doppler Topic Test
===============================

Install the requirements first.
Then add a `.env` file and add a line with your api key: `MC_API_KEY=1233423532532523`


Running the Script
------------------

### 1 - Extract Images from a Timespan

The first step is to make a list of all the images in a timespan:
2. edit the constants in `get-timespan-images.py` to specify the topic and timespan you want to get images for
3. run `python get-timespan-images.py` to fetch the images and generate a `.json` file to feed into the doppler


### 2 - Download Images & Prep for Analysis

Run the script to download and prep the images for analysis:
`python prep-images.py data/images-123-4321.json`

### 3 - Generate the scatterplot

1. Generate the logits: `python -m doppler.logits data/images-123-4321.json`
2. Generate the scatterplot: `python -m doppler.mosaics data/images-123-4321.json`


Installation Tips
-----------------

For OSX, to get Torch to work you might need to `brew install libomp`.
