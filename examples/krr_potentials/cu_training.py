import sys
from ase.io import Trajectory
from dask.distributed import Client, LocalCluster

sys.path.append("../../")
from ml4chem import Potentials
from ml4chem.fingerprints import Gaussian
from ml4chem.models.kernelridge import KernelRidge
from ml4chem.utils import logger


def train():
    # Load the images with ASE
    images = Trajectory("cu_training.traj")

    # Arguments for fingerprinting the images
    normalized = True
    batch_size = 160

    calc = Potentials(
        fingerprints=Gaussian(
            cutoff=6.5, normalized=normalized, save_preprocessor="cu_training.scaler"
        ),
        model=KernelRidge(batch_size=batch_size),
        label="cu_training",
    )

    calc.train(training_set=images)


if __name__ == "__main__":
    logger(filename="cu_training.log")
    cluster = LocalCluster()
    client = Client(cluster, asyncronous=True)
    train()
