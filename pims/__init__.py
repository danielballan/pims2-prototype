import entrypoints
import mimetypes


def open(*args, **kwargs):
    """
    Dispatch to a compatible PIMS reader.
    """
    # Dispatch using the first argument which is assumed to be a file buffer,
    # filename, or filename glob.
    reader = _dispatch(args[0])
    return reader(*args, **kwargs)


def _dispatch(file):
    # Ensure mimetypes is initialized. (This step pulls from the operating
    # system's MIME type registry.)
    mimetypes.init()
    if isinstance(file, str):
        # file is inferred to be a filename or filename glob.
        mimetype, _ = mimetypes.guess_type(file)
    else:
        # file is inferred to be a file buffer, which has a name attribute.
        # If this is a non-file-based buffer like a StringIO object it won't
        # have a name, in which case we can't infer the type this way.
        # In the future, we could employ libraries that peek at the first
        # couple bytes and infer the MIME type from the file signature, which
        # would work on any buffer.
        try:
            filename = file.name
        except AttributeError:
            raise DispatchError(
                "Expected a filename or file buffer with a 'name' attribute.")
        mimetype, _ = mimetypes.guess_type(filename)
    if mimetype is None:
        raise DispatchError(f"Could not detect MIME type of {file}")
    try:
        entrypoint = entrypoints.get_single('TBD.readers', mimetype)
    except entrypoints.NoSuchEntryPoint:
        raise DispatchError(f"No PIMS reader found for MIME type {mimetype}")
    reader = entrypoint.load()
    return reader
        

class PIMSError(Exception):
    "base class for all exceptions raised directly by PIMS"
    ...


class DispatchError(PIMSError):
    ...
