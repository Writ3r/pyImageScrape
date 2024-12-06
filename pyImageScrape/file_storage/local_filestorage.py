
import os
import io

class LocalFileStorage:
    """
    storage for local files
    """
    def __init__(
        self,
        dataDir,
    ):
        self.dataDir = dataDir
    
    def store_file(self, bytes:bytes, path:str):
        # calc full path
        savePath = self.dataDir + "/" + path
        # ensure directories exist
        os.makedirs(os.path.dirname(savePath), exist_ok=True)
        # write file to fs
        with open(savePath, "wb") as file:
            file.write(bytes)
