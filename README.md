# PIMS 2 Design Document and Prototype

## Summary

PIMS is a library for reading image series in a lazy fashion from various image
and video formats via a consistent API. It could be reworked to leverage
libraries, language features, and changes to the packaging ecosystem that have
emerged since PIMS' first release in 2013.

## PIMS

**What is PIMS?** [PIMS](http://soft-matter.github.io/pims), short for Python
Image Sequence, provides a common API to several underlying image or video I/O
libraries. It exposes image sequences through an object that supports numpy
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
Keim (Penn State), Casper van der Wel (Nelen & Schuurmans), and Ruben Verweij
(Leiden University). New development slowed around 2015, but the project is
still tended to.

## Room for Improvement

* PIMS predated [dask](https://dask.pydata.org/). Like PIMS, dask provides an
  object with numpy-like slicing semantics that can defer I/O and computation.
  PIMS could be updated to leverage `dask.array`, which has a much larger
  community behind it.
* PIMS predated [conda-forge](https://conda-forge.org/). PIMS has minimal
  required dependencies (just numpy, six, and a pure-Python support package
  developed for PIMS)---good so far---but it bundles most of its readers in the
  main package and has many optional dependencies to support these readers. It
  might be better to distribute each reader (or groups of readers with the same
  underlying I/O library) in separate packages so that they can be separately
  released and installed.
* PIMS predated the acceptance of
  [entrypoints](https://packaging.python.org/specifications/entry-points/)
  as an official PyPA specification (as opposed to a quirk/feature of only
  setuptools specifically). PIMS supports readers defined in external packages,
  but it discovers them by searching for subclasses of its base classes
  `FramesSequences` and `FramesSequenceND`. The downsides of this approach are
  (1) external packages with readers *must* import `pims` to subclass its
  objects and (2) the user must import the external package before using
  `pims.open` for PIMS to discover it.
* PIMS predated [xarray](https://xarray.pydata.org/en/stable/). The
  `xarray.DataArray` object could provide a natural way of encoding frame
  number, timecodes, "band" (i.e. color channel) labels. (For those unfamiliar,
  it's analogous to a `pandas.Series`, but with full ND support. It also plays
  very well with dask.)
* PIMS readers return `pims.Frame` objects which subclass `numpy.ndarray` in
  order to tack a custom `metadata` on the array, rather than taking the xarray
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
  other third-party libraries in this space.

  IANA maintains an official registry of formats (e.g. ``'image/png'``) but it
  also defines a standard for adding application-specific formats outside of the
  official standard (e.g. ``'application/x-hdf'``). PIMS can use official MIME
  types where possible and use this extension mechanism for formats that are not
  registered, such as one-off vendor-specific microscopy formats.

  Within a given MIME type there can be significant variety of internal
  structure or metadata conventions. For this, a nested dispatch may be the
  right idea: PIMS dispatches based on MIME type, and the reader registered for
  that MIME type may inspect the file and do a second layer of dispatch based on
  its contents/layout. Nothing in PIMS currently requires this level of
  complexity, but it might be useful if we were to add a family of, say,
  [NeXuS](https://manual.nexusformat.org/) readers or more sophisticated TIFF
  readers.

  Although MIME types are not as well known to the scientific user--programmers
  that PIMS aims to serve as they are to web-oriented software engineers, MIME
  types do already have foothold in SciPy via IPython rich display's
  [`_repr_mimebundle_`](https://ipython.readthedocs.io/en/stable/config/integrating.html#MyObject._repr_mimebundle_)
  and the [Jupyter data
  explorer](https://github.com/jupyterlab/jupyterlab-data-explorer).
* **Use Entrypoints** Perform reader discovery using entrypoints. Packages can
  declare in their `setup.py` that they provide PIMS-compatible objects like so:

  ```py
  setup(
      ...
      entry_points = {'TBD.readers': ['image/tiff = my_package:TIFFReader']}
  )
  ```

  In this way, packages can declare that they include objects with a
  PIMS-compatible interface without actually *importing* PIMS or subclassing any
  PIMS objects. (PIMS may provide base classes as optional scaffolds for
  convenience or code reuse, but the key point is that packages are not required
  to use them.)
 
  Providing the option *not* to depend on PIMS may help gain adoption among
  packages that may add PIMS support experimentally or only incidentally.
  Established I/O packages might be open to adding PIMS-compatible readers to
  their API if it costs them only tens of lines of code and no new dependencies,
  not even optional ones.

  Also, PIMS can use [entrypoints](https://entrypoints.readthedocs.io/) to
  construct a registry of all installed readers without actually importing the
  corresponding libraries unless/until their objects are actually used.
* **Put metadata beside data** Rather than returning a lazy, array-ish object
  directly, as PIMS does now

  ```py
  lazy_array = pims.open(file)
  ```

  add one more layer of indirection, giving space for `metadata` which can be
  cheaply accessed and inspected before additional work is performed to build
  the lazy array.

  ```py
  reader = pims.open(file)
  reader.metadata
  lazy_array = reader.read()
  lazy_array.dtype
  lazy_array.shape
  ```

  The usage `pims.open(file).read()` is still satisfyingly succinct and rhymes
  nicely with the syntax for opening files in Python, `open(file).read()`.
  Reading a file with PIMS will feel like reading a file with Python, but
  instead of returning an iterable of lines, it will return a lazy array-like
  object, which can be treated as an iterable sequence of images.

* **Use Dask** Embrace dask arrays, integrating with or replacing PIMS' lazy
  array-like classes `FramesSequence` and `FramesSequenceND`. It is an open
  question whether dask arrays can fully support the same lazy slicing
  semantics; see [#1](https://github.com/danielballan/pims2-prototype/issues/1).

### Use Case

Suppose I have a library for reading and analyzing microscopy images in a
particular file format. I already have I/O code. I could wrap it in a class that
implements a PIMS-compatible reader. (As illusrated with `reader` above and in
the example below, a "PIMS compatible reader" is a very small API, so this is
likely < 100 lines of code.) I could make the reader "discoverable" to PIMS by
declaring a ``'TBD.readers'`` entrypoint in my ``setup.py``. As emphasized
above, I could do both of these things without importing pims or adding it as a
dependency.

What have I gained for my effort? If all I care about is my particular file
format, not much. I might not find the new reader class any more convenient than
my original I/O code which underlies it.

But when I or one of my collaborators needs to read two different kinds of
formats, perhaps to align microscopy images with images from another instrument
or another group, now PIMS adds value. If I can find or make PIMS-compatible
readers for all the formats involved, my code will have to change very little
moving from one format to another. And to smooth over the differences entirely,
I may decide to install pims itself to engage the automatic MIME type detection
and dispatch in ``pims.open``.

### Migrating Existing Users

The proposed change to `pims.open` would be backward-incompatible, but all other
objects in PIMS could remain in the PIMS codebase in their current form,
deprecated but usable, alongside new objects that implement the PIMS 2 API.

## Try the Prototype

1. Install an example TIFF reader.

   ```sh
   git clone https://github.com/danielballan/tifffile_reader
   cd tifffile_reader
   pip install -e .
   ```

2. Generate example data.

   ```sh
   pip install -r requirements_for_generate_example_data.txt
   python generate_example_data.py
   ```

3. Try using reader directly to read one TIFF.

   ```py
   In [1]: import tifffile_reader

   In [2]: reader = tifffile_reader.TIFFReader('example_data/coffee.tif')

   In [3]: reader
   Out[3]: TiffReader('example_data/coffee.tif')

   In [4]: reader.read()
   Out[4]: dask.array<from-value, shape=(400, 600, 3), dtype=uint8, chunksize=(400, 600, 3), chunktype=numpy.ndarray>

   In [5]: reader.read().compute()
   <numpy array output, snipped>
   ```

   And try a TIFF series and stack as well.

   ```py
   In [3]: tifffile_reader.TIFFReader('example_data/series/*.tif').read().shape
   Out[3]: (200, 25, 25)

   In [4]: tifffile_reader.TIFFReader('example_data/lfw_subset_as_stack.tif').read().shape
   Out[4]: (200, 25, 25)
   ```

5. Install PIMS.

   ```sh
   git clone https://github.com/danielballan/pims2-prototype
   cd pims2-prototype
   pip install -e .
   ```

6. Let `pims.open` detect the filetype and invoke the TIFF reader implicitly.

   ```py
   In [1]: import pims

   In [2]: pims.open('example_data/coffee.tif').read().shape
   Out[2]: (400, 600, 3)
   ```

   Another example spells the file extension differently (`tiff` vs `tif`) but
   `mimetypes` still detects the filetype successfully.

   ```py
   In [3]: pims.open('example_data/coffee.tiff').read().shape
   Out[3]: (400, 600, 3)
   ```

Things to notice:
*  We were able to use `tifffile_reader` without `pims` imported or even
   installed. If `tifffile` itself were to add a PIMS reader, it could do so
   without adding a `pims` dependency.
*  The core `pims` package provides the dispatch-on-filetype mechanism. It has
   one dependency (the tiny pure-Python package `entrypoints`) and 50 lines of
   code. The filetype detection is done via the Python standard library module
   `mimetypes`, which relies solely on the file extension. More sophisticated
   detection schemes that consider file signatures are availabe in third party
   libraries and should be considered.

## Variety of Return Types

It is often useful to label axes of the data (color band, x vs y, etc.) and it
may be useful to add *coordinates* like frame number and time code. Should
PIMS 2 standardize on `xarray.DataArray`-wrapping-`dask.array.Array` instead
of standardizing on `dask.array.Array`? Or should we explicitly support the
possibility of multiple variations on a given reader (via thin subclasses)
that implement different return types, potentially including
`xarray.DataArray`, `dask.array.Array`, and plain `numpy.ndarray`?

## Connection to Intake DataSources

[Intake](https://intake.readthedocs.io/) is a newer project that, like PIMS,
wraps disparate file formats in a consistent interface. Unlike PIMS, intake
handles many data structures, not just image series; in particular it has
many readers that return tabular data as a `pandas.DataFrame` or
`xarray.Dataset`. How should PIMS relate to intake?

There is something to be said for intake's all-encompassing generality. "You
give me a data source; I give you a PyData object or its lazy (dask-backed)
counterpart." There is also something to be said for the tight scope of "image
series", which communicates a clear use case to users, lends itself to certain
file formats, and lends type stability to the interface. That is, PIMS' `read()`
always returns a series of image frames that the user can loop over; one never
has to check whether it has returned a `pandas.DataFrame`.

Should PIMS carry on as a similar-but-distinct library to intake or should it
become a distribution of intake drivers? One possible answer is, "Yes!" It is
to automatically generate objects that satify the intake ``DataSource`` API from
the proposed ``Reader`` objects. This is demonstrated in
[danielballan/reader-intake-adapter](https://github.com/danielballan/reader-intake-adapter).
