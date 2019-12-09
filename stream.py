import subprocess
import constant
import cv2
import numpy as np

class ArmoryCamStream(object):
    width = 1920
    height = 1080
    channels = 3  # RGB

    def __init__(self):
        self._proc = subprocess.Popen(
            constant.FFMPEG_COMMAND,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            shell=True,
            bufsize=-1,
        )

    # Define custom iterator for CamStream object that will grab a new frame each
    # step
    def __next__(self):
        raw_bytes = self._proc.stdout.read(self.height * self.width * self.channels)
        return np.frombuffer(raw_bytes, dtype=np.uint8).reshape((self.height, self.width, self.channels))

    # Calling ArmoryCamStream.next() will have same functionality as
    # ArmoryCamStream.__next__()
    next = __next__

    def __iter__(self):
        return self

    def close(self):
        self._proc.terminate()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class FileStream(object):
    def __init__(self, filepath, offset=0):
        self._capture = cv2.VideoCapture(filepath)
        self._capture.set(cv2.CAP_PROP_POS_FRAMES, offset)

    def close(self):
        self._capture.release()

    def __next__(self):
        success, frame = self._capture.read()
        if not success:
            raise StopIteration

        return frame

    next = __next__

    def __iter__(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
