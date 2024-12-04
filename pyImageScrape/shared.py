import pathlib

def get_current_folder():
    return str(pathlib.Path(__file__).parent.absolute())
