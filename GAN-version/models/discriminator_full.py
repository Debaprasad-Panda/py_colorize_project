from .utils.calc_output_and_feature_size import calc_output_and_feature_size
from .utils.instance_normalization import InstanceNormalization
from keras.models import model_from_json, Model
from .utils.sn import ConvSN2D
from keras.optimizers import Adam
from keras import backend as K
from .utils.attention import Attention
from keras.utils import multi_gpu_model
from keras.layers import Conv2D, Lambda, add, AvgPool2D, Activation, UpSampling2D, Input, concatenate, Reshape, LeakyReLU, Reshape, Flatten, concatenate


class DiscriminatorFull():
    """Core Generator.
        
    # Arguments
        width: Width of image in pixels
        height: Height of image in pixels
        channels: Channels for the input image and the generated image
        gpus: The number of gpus you will be using.
        learning_rate: learning rate
        decay_rate: 
    """

    def __init__(self,
                 width=256,
                 height=256,
                 channels=3,
                 learning_rate=0.0002,
                 decay_rate=2e-6,
                 gpus = 0):
        
        self.width = width
        self.height = height
        self.channels = channels
        self.gpus = gpus
        self.learning_rate = learning_rate
        self.decay_rate = decay_rate


        # ----------------------
        #  Discriminator Fullres
        # ----------------------

        output_size_full_picture, output_size_full_features = calc_output_and_feature_size(self.width, self.height)

        discriminator_input = Input(shape=(self.height, self.width, self.channels,))

        x_1 = ConvSN2D(64, 4, padding='same', strides=2)(discriminator_input)
        x = LeakyReLU(alpha=0.2)(x_1)

        x_2 = ConvSN2D(128, 4, padding='same', strides=2)(x)
        x = LeakyReLU(alpha=0.2)(x_2)
        
        x_2_att = Attention(128)(x)
        
        x_3 = ConvSN2D(256, 4, padding='same', strides=2)(x_2_att)
        x = LeakyReLU(alpha=0.2)(x_3)

        x_4 = ConvSN2D(512, 4, padding='same', strides=1)(x)
        x = LeakyReLU(alpha=0.2)(x_4)

        x = ConvSN2D(1, 4, padding='same', strides=1)(x)
        x = Reshape([output_size_full_picture, 1])(x)

        discriminator_features = concatenate([Flatten()(x_1), Flatten()(x_2), Flatten()(x_3), Flatten()(x_4)], axis=1)
        discriminator_features = Reshape([output_size_full_features, 1])(discriminator_features)


        def zero_loss(y_true, y_pred):
            return K.zeros_like(y_true)

        loss_d = ['mse', zero_loss]
        
        if self.gpus < 2:
            self.model = Model(discriminator_input, [x, discriminator_features])
            self.save_model = self.model
        else:
            self.save_model = Model(discriminator_input, [x, discriminator_features])
            self.model = multi_gpu_model(self.save_model, gpus=gpus)

        loss_weights_d = [1, 0]
        optimizer = Adam(self.learning_rate, 0.5, decay=self.decay_rate)
        self.model.compile(optimizer=optimizer, loss_weights=loss_weights_d, loss=loss_d)

        