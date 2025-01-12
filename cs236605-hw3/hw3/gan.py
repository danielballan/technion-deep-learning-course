from typing import Callable

import torch
import torch.nn as nn
import torch.nn.functional as F

from torch.optim import Optimizer
from torch.utils.data import DataLoader
from .autoencoder import EncoderCNN, DecoderCNN


class Discriminator(nn.Module):
    def __init__(self, in_size):
        """
        :param in_size: The size of on input image (without batch dimension).
        """
        super().__init__()
        self.in_size = in_size
        # TODO: Create the discriminator model layers.
        # To extract image features you can use the EncoderCNN from the VAE
        # section or implement something new.
        # You can then use either an affine layer or another conv layer to
        # flatten the features.
        # ====== YOUR CODE: ======
        self.hidden_size = 1024
        W_out = in_size[1] / 16
        H_out = in_size[2] / 16
        self.input_size = int(W_out * H_out * self.hidden_size)
        self.feature_encode = EncoderCNN(in_channels=in_size[0], out_channels=self.hidden_size)
        self.linear = nn.Linear(self.input_size, 1)
        # ========================

    def forward(self, x):
        """
        :param x: Input of shape (N,C,H,W) matching the given in_size.
        :return: Discriminator class score (aka logits, not probability) of
        shape (N,).
        """
        # TODO: Implement discriminator forward pass.
        # No need to apply sigmoid to obtain probability - we'll combine it
        # with the loss due to improved numerical stability.
        # ====== YOUR CODE: ======
        h = self.feature_encode(x)
        h = h.reshape(h.shape[0],-1)
        y = self.linear(h)
        # ========================
        return y


class Generator(nn.Module):
    def __init__(self, z_dim, featuremap_size=4, out_channels=3):
        """
        :param z_dim: Dimension of latent space.
        :featuremap_size: Spatial size of first feature map to create
        (determines output size). For example set to 4 for a 4x4 feature map.
        :out_channels: Number of channels in the generated image.
        """
        super().__init__()
        self.z_dim = z_dim

        # TODO: Create the generator model layers.
        # To combine image features you can use the DecoderCNN from the VAE
        # section or implement something new.
        # You can assume a fixed image size.
        # ====== YOUR CODE: ======
        self.featuremap_size = featuremap_size
        self.in_channels = 1024
        self.hidden_dim = self.in_channels * self.featuremap_size * self.featuremap_size
        self.ln_rec = torch.nn.Linear(self.z_dim, self.hidden_dim)
        self.features_decoder = DecoderCNN(in_channels= self.in_channels, out_channels=out_channels)
        # ========================

    def sample(self, n, with_grad=False):
        """
        Samples from the Generator.
        :param n: Number of instance-space samples to generate.
        :param with_grad: Whether the returned samples should have
        gradients or not.
        :return: A batch of samples, shape (N,C,H,W).
        """
        device = next(self.parameters()).device
        # TODO: Sample from the model.
        # Generate n latent space samples and return their reconstructions.
        # Don't use a loop.
        # ====== YOUR CODE: ======
        #Enable or disable grads based on its argument
        torch.autograd.set_grad_enabled(with_grad)

        #Generate n latent samples and return their reconstruction
        z = torch.randn([n, self.z_dim], device=device, requires_grad=with_grad)
        samples = self.forward(z)

        #Enable gradient update exist for later setting
        torch.autograd.set_grad_enabled(True)
        # ========================
        return samples

    def forward(self, z):
        """
        :param z: A batch of latent space samples of shape (N, latent_dim).
        :return: A batch of generated images of shape (N,C,H,W) which should be
        the shape which the Discriminator accepts.
        """
        # TODO: Implement the Generator forward pass.
        # Don't forget to make sure the output instances have the same scale
        # as the original (real) images.
        # ====== YOUR CODE: ======
        # 1. Convert latent to features.
        # 2. Apply features decoder.

        # ====== YOUR CODE: ======
        h_rec = self.ln_rec(z)
        h_rec = h_rec.view(h_rec.size(0), -1 , self.featuremap_size, self.featuremap_size)
        x = self.features_decoder(h_rec)
        # ========================
        return x

def discriminator_loss_fn(y_data, y_generated, data_label=0, label_noise=0.0):
    """
    Computes the combined loss of the discriminator given real and generated
    data using a binary cross-entropy metric.
    This is the loss used to update the Discriminator parameters.
    :param y_data: Discriminator class-scores of instances of data sampled
    from the dataset, shape (N,).
    :param y_generated: Discriminator class-scores of instances of data
    generated by the generator, shape (N,).
    :param data_label: 0 or 1, label of instances coming from the real dataset.
    :param label_noise: The range of the noise to add. For example, if
    data_label=0 and label_noise=0.2 then the labels of the real data will be
    uniformly sampled from the range [-0.1,+0.1].
    :return: The combined loss of both.
    """
    assert data_label == 1 or data_label == 0
    # TODO: Implement the discriminator loss.
    # See torch's BCEWithLogitsLoss for a numerically stable implementation.
    # ====== YOUR CODE: ======
    criterion = nn.BCEWithLogitsLoss(weight=None, reduce=False)
    real_labels =  label_noise * torch.rand(y_data.shape, device=y_data.device) + data_label - (label_noise / 2)
    fake_labels =  label_noise * torch.rand(y_generated.shape, device=y_data.device) + 1 - data_label - (label_noise / 2)
    loss_data =  torch.mean(criterion(y_data, real_labels))
    loss_generated = torch.mean(criterion(y_generated, fake_labels))
    # ========================
    return loss_data + loss_generated


def generator_loss_fn(y_generated, data_label=0):
    """
    Computes the loss of the generator given generated data using a
    binary cross-entropy metric.
    This is the loss used to update the Generator parameters.
    :param y_generated: Discriminator class-scores of instances of data
    generated by the generator, shape (N,).
    :param data_label: 0 or 1, label of instances coming from the real dataset.
    :return: The generator loss.
    """
    # TODO: Implement the Generator loss.
    # Think about what you need to compare the input to, in order to
    # formulate the loss in terms of Binary Cross Entropy.
    # ====== YOUR CODE: ======
    criterion = nn.BCEWithLogitsLoss(weight=None, reduce=False)
    labels = y_generated.new_full(y_generated.shape, data_label)
    loss=torch.mean(criterion(y_generated,labels))
    # ========================
    return loss


def train_batch(dsc_model: Discriminator, gen_model: Generator,
                dsc_loss_fn: Callable, gen_loss_fn: Callable,
                dsc_optimizer: Optimizer, gen_optimizer: Optimizer,
                x_data: DataLoader):
    """
    Trains a GAN for over one batch, updating both the discriminator and
    generator.
    :return: The discriminator and generator losses.
    """

    # TODO: Discriminator update
    # 1. Show the discriminator real and generated data
    # 2. Calculate discriminator loss
    # 3. Update discriminator parameters
    # ====== YOUR CODE: ======
    dsc_optimizer.zero_grad()


    real_batch = x_data
    fake_batch = gen_model.sample(x_data.shape[0], with_grad=True)

    real_prediction = dsc_model(real_batch)
    fake_prediction = dsc_model(fake_batch.detach())

    dsc_loss = dsc_loss_fn(real_prediction, fake_prediction)
    dsc_loss.backward()

    dsc_optimizer.step()
    # ========================

    # TODO: Generator update
    # 1. Show the discriminator generated data
    # 2. Calculate generator loss
    # 3. Update generator parameters
    # ====== YOUR CODE: ======
    gen_optimizer.zero_grad()

    fake_prediction = dsc_model(fake_batch)

    gen_loss = gen_loss_fn(fake_prediction)
    gen_loss.backward()
    gen_optimizer.step()
    # ========================

    return dsc_loss.item(), gen_loss.item()

