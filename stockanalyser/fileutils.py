import re


def to_pickle_filename(name):
    filename = re.sub("\s+", "_", name).lower()
    filename += ".pickle"
    return filename
