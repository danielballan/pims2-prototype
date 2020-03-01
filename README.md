# PIMS 2 Design Document and Prototype

## Summary

PIMS is a library for reading image series in a lazy fashion from various image
and video formats via a consistent API. It could be reworked to leverage
libraries, language features, and changes to the packaging ecosystem that have
emerged since PIMS' first release in 2013.

## PIMS

**What is PIMS?** [PIMS](http://soft-matter.github.io/pims), short for Python
Image Sequence, provides a common API to several underlying image or video I/O
libraries. It exposes images sequences through an object that supports numpy
array-like slicing with lazy evaluation.

Example:

```py
# Several formats are built in.
import pims
images = pims.open('my_directory/*.png')  # many PNGs with sequential names
images = pims.open('my_directory/*.tif')  # many TIFs with sequential names
images = pims.open('tiff_stack.tif')  # one TIF file containing many frames
images = pims.open('movie.mp4')

# All of these indexing styles are supported and lazy --- no I/O performed yet.
subset = images[::2]
subset = images[:5]
subset = images[[13, 52, 99]] 

# When a single frame is accessed, via indexing...
first_image = subset[0]

# or iteration...
for image in subset:
    ...

# then I/O occurs, with one frame loaded at a time if possible.
```

**Who uses PIMS?** According to GitHub it is used by 102 other projects, and it
has 51 forks. Dask-image uses pims, as a required dependency. Many users
are concentrated in the bio sciences or soft matter physics area.

**Who maintains PIMS?** PIMS was split out of an image analysis codebase in
2013. Its main contributors are Dan Allan (BNL), Thomas Caswell (BNL), Nathan
Keim (Cal Poly), and Casper van der Wel (Nelen & Schuurmans). New development
slowed around 2015, but the project is still tended to.

## Room for Improvement

* PIMS predated dask. It has not been updated to leverage dask.
* PIMS predated conda-forge. PIMS has minimal required dependencies (just numpy,
  six, and a pure-Python support package developed for PIMS)---good so far---but
  it bundles most of its readers in the main package and has many optional
  dependencies to support these readers. It might be better to distribute each
  reader (or groups of readers with the same underlying I/O library) in separate
  packages so that they can be separately released and installed.
* PIMS predated the acceptance of `entrypoints` as an official Python language
  feature (as opposed to a quirk/feature of only setuptools specifically). PIMS
  supports readers in external packages, but it discovers them by searching for
  subclasses of its base classes `FramesSequences` and `FramesSequenceND`. The
  downside of this approach is that (1) external packages with readers *must*
  import `pims` to subclass its objects and (2) the user must import the
  external package before using `pims.open` for PIMS to discover it.
* PIMS readers return `Frame` objects which subclass `numpy.ndarray` in order to
  tack a custom `metadata` on the array, rather than taking the xarray
  approach and putting `metadata` on an object that encapsulates the data
  through composition. The authors now appreciate the downsides of subclassing
  `ndarray` and the difficulties of propagating metadata through array
  operations.
* `pims.open` detects file format and dispatches to a compatible reader using an
  *ad hoc* scheme rather than using an existing standard.

## Proposal for PIMS 2.0

* **Use MIME** Detect file format and dispatch to a compatible reader based
  on the file's MIME type, using the Python standard library module
  [mimetypes](https://docs.python.org/3/library/mimetypes.html) and potentially
  other third-party libraries in this space. Although
  MIME types are not as well known to the scientific user--programmers that PIMS
  aims to serve as they are to web-oriented software engineers, MIME types do
  already have foothold in SciPy via IPython rich display's
  [`_repr_mimebundle_`](https://ipython.readthedocs.io/en/stable/config/integrating.html#MyObject._repr_mimebundle_)
  and the
  [Jupyter data explorer](https://github.com/jupyterlab/jupyterlab-data-explorer).
  (Some formats of interest, such as one-off vendor-specific microscopy formats,
  are not registered with the IANA MIME type standard, but that standard
  includes a well-defined system for handling unregistered types.)
* **Use Entrypoints** Perform reader discovery using entrypoints. Packages can
  declare in their `setup.py` that they provide PIMS-compatible objects like so:

  ```py
  setup(
      ...
      entry_points = {'pims.readers': ['image/tiff = my_package:TIFFReader']}
  )
  ```

  In this way, packages can declare that they include objects with a
  PIMS-compatible interface without actually *importing* PIMS or subclassing any
  PIMS objects. (Perhaps they *may* subclass something from PIMS for
  convenience, but providing the option not to do so is a selling point for
  packages that may add PIMS support experimentally or only incidentally.)

  Also, PIMS can use [entrypoints](https://entrypoints.readthedocs.io/) to
  construct a registry of all installed readers without actually *importing* the
  corresponding libraries unless/until their objects are actually used.
* **Put metadata beside data** Rather than returning a lazy, array-ish object
  directly, as PIMS does now

  ```py
  lazy_array = pims.open(file)
  ```

  add one more layer of indirection, giving space for `metadata` which can be
  cheaply accessed and inspected before additional I/O is performed to build the
  lazy array.

  ```py
  reader = pims.open(file)
  reader.metadata
  lazy_array = reader.read()
  ```

  *The usage `pims.open(file).read()` is still satisfyingly succinct and rhymes
  nicely with the opening files in Python `open(file).read()`. Reading a file
  with PIMS will feel like reading a file with Python, but instead of bytes one
  gets lazy array-like objects.*

* **Use Dask** Embrace dask arrays, leaving behind PIMS' lazy array-like
  classes `FramesSequence` and `FramesSequenceND`.

## PIMS as a Pattern

In the proposed design for 2.0, the "core" PIMS library becomes quite small
indeed, and some applications unnecessary to even install.

Suppose I have a library for reading and analyzing microscopy images. I already
have I/O code. I could wrap it in a class that implements a PIMS-compatible
reader---which is just an object with a `metadata` attribute and a `read()`
method that returns a dask array---and I could make it discoverable by declaring
a ``'pims.reader'`` entrypoint to my ``setup.py``. As emphasized above, I could
do both of these things without importing pims.

What have I gained? If all I care about is my microscopy images, not much. There
is no benefit to installing pims itself; I can just import and use my
PIMS-compatible reader class directly from my package. But when I or one of my
users needs to read two different kinds of formats, perhaps to align microscopy
images with PNG or HDF5 images from other instrument or another group, now PIMS
adds value. If there exist PIMS-compatible objects for all the formats involved,
my code will have to change very little. I may even decide to install pims
itself to engage the automatic MIME type inspection and dispatch in
``pims.open``.

## More Embellishments to Consider

* To obtain a `numpy.ndarray` instead of a `dask.array.Array`, users can do
  `pims.open(file).read().compute()`. Should readers support an optional
  argument to `read` that returns a `numpy.ndarray` directly, as in
  `pims.open(file).read(delayed=False)`? Implications:
  * This reduces the type stability of the API from strict type stability to
    duck type stability.
  * Some readers could forgo the dask dependency and raise `NotImplementedError`
    if `delayed=True`.
  * Readers could make their own choice about the best default value for
    `delayed`, depending on data shape and how well the underlying I/O library
    actually supports laziness.
* It is often convenient to label axes of the data (color band, x vs y, etc.)
  Should PIMS 2 standardize on `xarray.DataArray`-wrapping-`dask.array.Array`
  instead of standardizing on `dask.array.Array`? Or should either be allowed,
  since they duck-type alike in many ways?
