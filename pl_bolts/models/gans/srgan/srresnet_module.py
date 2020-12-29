from argparse import ArgumentParser

import pytorch_lightning as pl
import torch
import torch.nn.functional as F

from pl_bolts.callbacks import SRImageLoggerCallback
from pl_bolts.datamodules.stl10_sr_datamodule import STL10_SR_DataModule
from pl_bolts.models.gans.srgan.components import SRGANGenerator


class SRResNet(pl.LightningModule):
    """
    SRResNet implementation from the paper `Photo-Realistic Single Image Super-Resolution Using a Generative Adversarial
    Network <https://arxiv.org/pdf/1609.04802.pdf>`_. A pretrained model is used as the generator for SRGAN.

    Example::

        from pl_bolts.models.gan import SRResNet

        m = SRResNet()
        Trainer(gpus=1).fit(m)

    Example CLI::

        # STL10_SR_DataModule
        python ssresnetmodule.py --gpus 1
    """

    def __init__(self, image_channels: int = 3, feature_maps: int = 64, learning_rate: float = 1e-4, **kwargs) -> None:
        """
        Args:
            image_channels: Number of channels of the images from the dataset
            feature_maps: Number of feature maps to use
            learning_rate: Learning rate
        """
        super().__init__()
        self.save_hyperparameters()

        self.srresnet = SRGANGenerator(self.hparams.image_channels, self.hparams.feature_maps)

    def configure_optimizers(self):
        return torch.optim.Adam(self.srresnet.parameters(), lr=self.hparams.learning_rate)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Creates a high resolution image given a low resolution image

        Example::

            sr_resnet = SRResNet.load_from_checkpoint(PATH)
            hr_image = sr_resnet(lr_image)
        """
        return self.srresnet(x)

    def training_step(self, batch, batch_idx):
        hr_image, lr_image = batch
        fake = self(lr_image)
        loss = F.mse_loss(hr_image, fake)
        self.log("loss", loss, on_step=True, on_epoch=True)
        return loss

    @staticmethod
    def add_model_specific_args(parent_parser: ArgumentParser) -> ArgumentParser:
        parser = ArgumentParser(parents=[parent_parser], add_help=False)
        parser.add_argument("--image_channels", default=3, type=int)
        parser.add_argument("--feature_maps", default=64, type=int)
        parser.add_argument("--learning_rate", default=1e-4, type=float)
        return parser


def cli_main(args=None):
    pl.seed_everything(1234)

    parser = ArgumentParser()
    parser.add_argument("--log_interval", default=1000, type=int)

    parser = STL10_SR_DataModule.add_argparse_args(parser)
    parser = pl.Trainer.add_argparse_args(parser)
    parser = SRResNet.add_model_specific_args(parser)
    args = parser.parse_args(args)

    model = SRResNet(**vars(args))
    dm = STL10_SR_DataModule.from_argparse_args(args)
    trainer = pl.Trainer.from_argparse_args(args, callbacks=[SRImageLoggerCallback(log_interval=args.log_interval)])
    trainer.fit(model, dm)

    torch.save(model.srresnet, f"srresnet-epoch={args.max_epochs}-step={trainer.global_step}.pt")


if __name__ == "__main__":
    cli_main()