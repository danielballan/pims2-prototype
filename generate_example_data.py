import tifffile
import skimage.data
import os


def main():
    here = os.path.dirname(__file__)
    directory = os.path.join(here, 'example_data')
    os.makedirs(directory, exist_ok=True)
    coffee = skimage.data.coffee()
    tifffile.imwrite(os.path.join(directory, 'coffee.tif'), coffee)
    tifffile.imwrite(os.path.join(directory, 'coffee.tiff'), coffee)
    stack = skimage.data.lfw_subset()
    tifffile.imwrite(os.path.join(directory, 'lfw_subset_as_stack.tif'), stack)
    subdirectory = os.path.join(directory, 'series')
    os.makedirs(subdirectory, exist_ok=True)
    for i, plane in enumerate(stack):
        filepath = os.path.join(subdirectory, f'lfw_subset_as_series_{i:03}.tif')
        tifffile.imwrite(filepath, plane)


if __name__ == '__main__':
    main()
