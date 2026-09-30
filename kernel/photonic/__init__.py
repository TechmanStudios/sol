"""
SOL Kernel: Photonic & WebGPU Substrate Mapping
Package: sol.kernel.photonic
"""

from sol.kernel.photonic.webgpu_compiler import (
    WebGPUComputeCompiler,
    WGSLShaderSpec,
    ShaderValidationResult
)
from sol.kernel.photonic.substrate_mapping import (
    PhotonicMZIMesh,
    PhotonicLogicGateMapping,
    NeuromorphicMemristorCrossbar,
    PhysicalSubstrateComparison
)
from sol.kernel.photonic.photonic_sheaf import (
    PhotonicSheafDilation,
    PhotonicSheafProcessor,
    PhotonicSheafReadout,
    PhotonicCavityRoundtrip,
    PhotonicCavityTrajectory
)

__all__ = [
    "WebGPUComputeCompiler",
    "WGSLShaderSpec",
    "ShaderValidationResult",
    "PhotonicMZIMesh",
    "PhotonicLogicGateMapping",
    "NeuromorphicMemristorCrossbar",
    "PhysicalSubstrateComparison",
    "PhotonicSheafDilation",
    "PhotonicSheafProcessor",
    "PhotonicSheafReadout",
    "PhotonicCavityRoundtrip",
    "PhotonicCavityTrajectory",
]
