import pkg_resources

__version__: str = pkg_resources.require("cast2gif")[0].version
__version_name__: str = f"ToB/v{__version__}/source/Cast2Gif"
