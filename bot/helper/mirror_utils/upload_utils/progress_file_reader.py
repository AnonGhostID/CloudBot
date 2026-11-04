from io import BufferedReader
from pathlib import Path

class ProgressFileReader(BufferedReader):
    def __init__(self, filename, read_callback=None):
        super().__init__(open(filename, "rb"))
        self.__read_callback = read_callback
        self.length = Path(filename).stat().st_size
        
    def read(self, size=-1):
        data = super().read(-1 if size is None else size)
        if data and self.__read_callback:
            self.__read_callback(self.tell())
        return data