from setuptools import setup


setup(
    name='my_tiff_package',
    packages=['my_tiff_package'],
    entry_points={
        'pims.readers':
            ['image/tiff = my_tiff_package:TIFFReader']},
    install_requires=['dask[array]', 'tifffile'],
    )
