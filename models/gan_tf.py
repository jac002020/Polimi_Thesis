import tensorflow as tf

from base.base_model import BaseModel


class GAN_TF(BaseModel):
    def __init__(self, config):
        super(GAN_TF, self).__init__(config)
        self.build_model()
        self.init_saver()

    def build_model(self):
        # Placeholders
        self.is_training = tf.placeholder(tf.bool)
        self.image_input = tf.placeholder(tf.float32, shape=[None] + self.config.image_dims, name="x")
        self.noise_tensor = tf.placeholder(tf.float32, shape=[None, self.config.noise_dim], name="noise")
        self.random_vector_for_generation = tf.random_normal(
            [self.config.num_example_imgs_to_generate, self.config.noise_dim], name="sampler")
        # Random Noise addition to both image and the noise
        # This makes it harder for the discriminator to do it's job, preventing
        # it from always "winning" the GAN min/max contest
        # self.real_noise = tf.placeholder(dtype=tf.float32, shape=[None] + self.config.image_dims, name="real_noise")
        # self.fake_noise = tf.placeholder(dtype=tf.float32, shape=[None] + self.config.image_dims, name="fake_noise")

        # self.real_image = self.image_input + self.fake_noise
        # Placeholders for the true and fake labels
        self.true_labels = tf.placeholder(dtype=tf.float32, shape=[None, 1], name="true_labels")
        self.generated_labels = tf.placeholder(dtype=tf.float32, shape=[None, 1], name="gen_labels")
        # Full Model Scope
        with tf.variable_scope("DCGAN"):
            self.generated_sample = self.build_generator(self.noise_tensor)
            disc_real = self.build_discriminator(self.image_input,name="_real")
            disc_fake = self.build_discriminator(self.generated_sample,reuse=True,name="_fake")

            # Losses of the training of Generator and Discriminator
            ########################################################################
            # METRICS
            ########################################################################

        with tf.name_scope("Discriminator_Loss"):
            self.disc_loss_real = tf.reduce_mean(tf.losses.sigmoid_cross_entropy(
                multi_class_labels=self.true_labels, logits=disc_real
            ))
            self.disc_loss_fake = tf.reduce_mean(tf.losses.sigmoid_cross_entropy(
                multi_class_labels=self.generated_labels,
                logits=disc_fake,
            ))
            # Sum the both losses
            self.total_disc_loss = self.disc_loss_real + self.disc_loss_fake

        with tf.name_scope("Generator_Loss"):
            self.gen_loss = tf.reduce_mean(tf.losses.sigmoid_cross_entropy(
                tf.zeros_like(disc_fake), disc_fake))


        # Store the loss values for the Tensorboard
        ########################################################################
        # TENSORBOARD
        ########################################################################
        tf.summary.scalar("Generator_Loss", self.gen_loss)
        tf.summary.scalar("Discriminator_Real_Loss", self.disc_loss_real)
        tf.summary.scalar("Discriminator_Gen_Loss", self.disc_loss_fake)
        tf.summary.scalar("Discriminator_Total_Loss", self.total_disc_loss)
        # Images for the Tensorboard
        tf.summary.image("From_Noise", tf.reshape(self.generated_sample, [-1, 28, 28, 1]))
        tf.summary.image("Real_Image", tf.reshape(self.image_input, [-1, 28, 28, 1]))
        # Sample Operation

        ########################################################################
        # OPTIMIZATION
        ########################################################################
        # Build the Optimizers
        self.generator_optimizer = tf.train.AdamOptimizer(
            self.config.generator_l_rate,
            beta1=self.config.optimizer_adam_beta1,
            beta2=self.config.optimizer_adam_beta2
        )
        self.discriminator_optimizer = tf.train.AdamOptimizer(
            self.config.discriminator_l_rate,
            beta1=self.config.optimizer_adam_beta1,
            beta2=self.config.optimizer_adam_beta2
        )
        # Collect all the variables
        all_variables = tf.get_collection(tf.GraphKeys.TRAINABLE_VARIABLES)
        # Generator Network Variables
        self.generator_vars = [v for v in all_variables if v.name.startswith("DCGAN/Generator")]
        # Discriminator Network Variables
        self.discriminator_vars = [v for v in all_variables if v.name.startswith("DCGAN/Discriminator")]
        # Create Training Operations
        # Generator Network Operations
        self.gen_update_ops = tf.get_collection(tf.GraphKeys.UPDATE_OPS, scope="DCGAN/Generator")
        # Discriminator Network Operations
        self.disc_update_ops = tf.get_collection(tf.GraphKeys.UPDATE_OPS, scope="DCGAN/Discriminator")
        # Initialization of Optimizers
        with tf.control_dependencies(self.gen_update_ops):
            self.train_gen = self.generator_optimizer.minimize(
                self.gen_loss, global_step=self.global_step_tensor,
                var_list=self.generator_vars
            )
        with tf.control_dependencies(self.disc_update_ops):
            self.train_disc = self.discriminator_optimizer.minimize(
                self.total_disc_loss, global_step=self.global_step_tensor,
                var_list=self.discriminator_vars
            )

        for i in range(0, 10):
            with tf.name_scope("layer" + str(i)):
                pesos = tf.get_collection(tf.GraphKeys.TRAINABLE_VARIABLES)
                tf.summary.histogram("pesos" + str(i), pesos[i])
        self.summary = tf.summary.merge_all()

    def build_generator(self, noise_tensor):
        # Make the Generator model
        with tf.variable_scope("Generator",reuse=tf.AUTO_REUSE):
            # Densely connected Neural Network layer with 12544 Neurons.
            x_g = tf.layers.Dense(units=7 * 7 * 256, use_bias=False,
                                  kernel_initializer=tf.truncated_normal_initializer(stddev=0.02))(
                noise_tensor)
            # Normalize the output of the Layer
            x_g = tf.layers.batch_normalization(inputs=x_g, momentum=self.config.batch_momentum,
                                                training=self.is_training)
            # f(x) = alpha * x for x < 0, f(x) = x for x >= 0.
            x_g = tf.nn.leaky_relu(features=x_g, alpha=self.config.leakyReLU_alpha)
            # Reshaping the output
            x_g = tf.reshape(x_g, shape=[-1, 7, 7, 256])
            # Check the size of the current output just in case
            assert x_g.get_shape().as_list() == [None, 7, 7, 256]
            # First Conv2DTranspose Layer
            x_g = tf.layers.Conv2DTranspose(filters=128, kernel_size=5, strides=(1, 1), padding="same",
                                            use_bias=False,
                                            kernel_initializer=tf.truncated_normal_initializer(stddev=0.02))(x_g)
            assert x_g.get_shape().as_list() == [None, 7, 7, 128]

            x_g = tf.layers.batch_normalization(inputs=x_g, momentum=self.config.batch_momentum,
                                                training=self.is_training)
            x_g = tf.nn.leaky_relu(features=x_g, alpha=self.config.leakyReLU_alpha)
            # Second Conv2DTranspose Layer
            x_g = tf.layers.Conv2DTranspose(filters=128, kernel_size=5, strides=(2, 2), padding="same",
                                            use_bias=False,
                                            kernel_initializer=tf.truncated_normal_initializer(stddev=0.02))(x_g)
            assert x_g.get_shape().as_list() == [None, 14, 14, 128]

            x_g = tf.layers.batch_normalization(inputs=x_g, momentum=self.config.batch_momentum,
                                                training=self.is_training)
            x_g = tf.nn.leaky_relu(features=x_g, alpha=self.config.leakyReLU_alpha)
            # Third Conv2DTranspose Layer
            x_g = tf.layers.Conv2DTranspose(filters=128, kernel_size=5, strides=(2, 2), padding="same",
                                            use_bias=False,
                                            kernel_initializer=tf.truncated_normal_initializer(stddev=0.02))(x_g)
            assert x_g.get_shape().as_list() == [None, 28, 28, 128]
            x_g = tf.layers.batch_normalization(inputs=x_g, momentum=self.config.batch_momentum,
                                                training=self.is_training)
            x_g = tf.nn.leaky_relu(features=x_g, alpha=self.config.leakyReLU_alpha)
            # Final Conv2DTranspose Layer
            x_g = tf.layers.Conv2DTranspose(filters=1, kernel_size=5, strides=(1, 1), padding="same",
                                            use_bias=False,
                                            activation=tf.nn.tanh,
                                            kernel_initializer=tf.truncated_normal_initializer(stddev=0.02))(x_g)
            assert x_g.get_shape().as_list() == [None, 28, 28, 1]
            return x_g

    def build_discriminator(self,image,reuse=True,name=""):
        # if (reuse):
        #     tf.get_variable_scope().reuse_variables()
        with tf.variable_scope("Discriminator"+ name,reuse=tf.AUTO_REUSE):
            # First Convolutional Layer
            x_d = tf.layers.Conv2D(filters=128, kernel_size=5, strides=(1, 1), padding="same",
                                   kernel_initializer=tf.truncated_normal_initializer(stddev=0.02))(image)
            x_d = tf.layers.batch_normalization(inputs=x_d, momentum=self.config.batch_momentum, training=self.is_training)
            x_d = tf.nn.leaky_relu(features=x_d, alpha=self.config.leakyReLU_alpha)
            # Second Convolutional Layer
            x_d = tf.layers.Conv2D(filters=64, kernel_size=5, strides=(2, 2), padding="same",
                                   kernel_initializer=tf.truncated_normal_initializer(stddev=0.02))(x_d)
            x_d = tf.layers.batch_normalization(inputs=x_d, momentum=self.config.batch_momentum, training=self.is_training)
            x_d = tf.nn.leaky_relu(features=x_d, alpha=self.config.leakyReLU_alpha)

            # Third Convolutional Layer
            x_d = tf.layers.Conv2D(filters=32, kernel_size=5, strides=(2, 2), padding="same",
                                   kernel_initializer=tf.truncated_normal_initializer(stddev=0.02))(x_d)
            x_d = tf.layers.batch_normalization(inputs=x_d, momentum=self.config.batch_momentum, training=self.is_training)
            x_d = tf.nn.leaky_relu(features=x_d, alpha=self.config.leakyReLU_alpha)

            x_d = tf.layers.Flatten()(x_d)
            x_d = tf.layers.Dropout(rate=self.config.dropout_rate)(x_d)
            x_d = tf.layers.Dense(units=1)(x_d)
            return x_d


    def init_saver(self):
        self.saver = tf.train.Saver(max_to_keep=self.config.max_to_keep)