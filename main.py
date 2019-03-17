import tensorflow as tf

from utils.data_generator import DataGenerator
from models.gan_model import GAN
from trainers.gan_trainer import GANTrainer
from utils.config import process_config
from utils.logger import Logger
from utils.utils import get_args
from utils.dirs import create_dirs


def main():
    # capture the config path from the run arguments
    # then process the json configuration file
    try:
        args = get_args()
        config = process_config(args.config)

    except:
        print("missing or invalid arguments")
        exit(0)

    # create the experiments dirs
    create_dirs([config.summary_dir, config.checkpoint_dir])
    # create tensorflow session
    sess = tf.Session()
    # create your data generator
    data = DataGenerator(config)
    iterator = data.dataset.make_one_shot_iterator()
    image_data = iterator.get_next()
    # create an instance of the model you want
    model = GAN(config)
    # create tensorboard logger
    logger = Logger(sess, config)
    # create trainer and pass all the previous components to it
    trainer = GANTrainer(sess, model, image_data, config, logger)
    #load model if exists
    model.load(sess)
    # here you train your model
    trainer.train()


if __name__ == '__main__':
    main()
