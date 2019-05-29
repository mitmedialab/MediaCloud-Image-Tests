MediaCloud + Doppler Test
=========================

Running a Test
--------------

1. Start by downloading all the images for a sample file: `python process-example.py examples/caravan-news-images.json`
2. Next generate the logits: `python -m doppler.logits`
3. Then generate the images: `python -m doppler.mosaics`

Installation Tips
-----------------

For OSX, to get Torch to work you might need to `brew install libomp`.
