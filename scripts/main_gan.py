import tensorflow as tf

from data_loader.data_generator import DataGenerator
from scripts.gan import GAN
from scripts.gan_trainer import GANTrainer
from utils.summarizer import Summarizer
from utils.dirs import create_dirs


def main(config):
    # capture the config path from the run arguments
    # then process the json configuration file

    # create the experiments dirs
    create_dirs([config.summary_dir, config.checkpoint_dir, config.step_generation_dir])
    # create tensorflow session
    sess = tf.Session()
    # create your data generator
    data = DataGenerator(config)
    # create an instance of the model you want
    model = GAN(config)
    # create tensorboard logger
    logger = Summarizer(sess, config)
    # create trainer and pass all the previous components to it
    trainer = GANTrainer(sess, model, data, config, logger)
    # load model if exists
    model.load(sess)
    # here you train your model
    trainer.train()


if __name__ == "__main__":
    main()
