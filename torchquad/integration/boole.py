from .base_integrator import BaseIntegrator
from .integration_grid import IntegrationGrid
from .utils import setup_integration_domain

import torch

import logging

logger = logging.getLogger(__name__)


class Boole(BaseIntegrator):

    """Boole's rule in torch. See https://en.wikipedia.org/wiki/Newton%E2%80%93Cotes_formulas#Closed_Newton%E2%80%93Cotes_formulas . 
    """

    def __init__(self):
        super().__init__()
        self._convergence_order = 5  # 4th grade approx

    def integrate(self, fn, dim, N=5, integration_domain=None):
        """Integrates the passed function on the passed domain using Boole's rule

        Args:
            fn (func): The function to integrate over.
            dim (int): Dimensionality of the integration domain.
            N (int, optional): Number of sample points to use for the integration. N has to be such as N^(1/dim) - 1 % 4 == 0. Defaults to 5 for dim = 1.
            integration_domain (list, optional): Integration domain. Defaults to [-1,1]^dim.

        Returns:
            float: Integral value
        """
        self._check_inputs(dim=dim, N=N, integration_domain=integration_domain)
        self._integration_domain = setup_integration_domain(dim, integration_domain)

        logger.debug(
            "Using Boole for integrating a fn with "
            + str(N)
            + " points over "
            + str(integration_domain)
        )

        self._dim = dim
        self._fn = fn

        # Create grid and assemble evaluation points
        self._grid = IntegrationGrid(N, integration_domain)

        #Check on the grid_N size
        if (self._grid._N - 1) % 4 > 0:
            raise (
                ValueError(
                    f"N was {self._grid._N}. N has to be such as N^(1/dim) - 1 % 4 == 0."
                )
            )

        logger.debug("Evaluating integrand on the grid")
        function_values = self._eval(self._grid.points)

        # Reshape the output to be [N,N,...] points instead of [dim*N] points
        function_values = function_values.reshape([self._grid._N] * dim)

        logger.debug("Computing areas")

        cur_dim_areas = function_values

        # We collapse dimension by dimension
        for cur_dim in range(dim):
            cur_dim_areas = (
                self._grid.h[cur_dim]
                / 22.5
                * (
                    7 * cur_dim_areas[..., 0:-4][..., ::4]
                    + 32 * cur_dim_areas[..., 1:-3][..., ::4]
                    + 12 * cur_dim_areas[..., 2:-2][..., ::4]
                    + 32 * cur_dim_areas[..., 3:-1][..., ::4]
                    + 7 * cur_dim_areas[..., 4:][..., ::4]
                )
            )
            cur_dim_areas = torch.sum(cur_dim_areas, dim=dim - cur_dim - 1)
        logger.info("Computed integral was " + str(cur_dim_areas))

        return cur_dim_areas