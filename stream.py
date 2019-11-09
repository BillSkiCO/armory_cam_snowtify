import subprocess
import time

import cv2 as cv
import numpy as np

STREAM_URL = 'https://tower.armorycam.com/stream/armorystream.m3u8'
FFMPEG = '/usr/bin/ffmpeg'

FFMPEG_COMMAND = [FFMPEG, '-i', STREAM_URL,
                  '-loglevel', 'quiet',  # no text output
                  '-an',  # disable audio
                  '-f', 'image2pipe',
                  '-pix_fmt', 'bgr24',
                  '-vcodec', 'rawvideo', '-',
                  ]


class ArmoryCamStream(object):
    width = 1920
    height = 1080
    channels = 3  # RGB

    def __init__(self):
        self._proc = subprocess.Popen(
            FFMPEG_COMMAND,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )

    def __next__(self):
        raw_bytes = self._proc.stdout.read(self.height * self.width * self.channels)
        return np.frombuffer(raw_bytes, dtype=np.uint8).reshape((self.height, self.width, self.channels))

    # python2 is still a thing
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
        self._capture = cv.VideoCapture(filepath)
        self._capture.set(cv.CAP_PROP_POS_FRAMES, offset)

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
