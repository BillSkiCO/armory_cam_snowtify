import subprocess
import constant
import cv2
import numpy as np
import exceptions
import api
import signal
import threading
import sys
try:
    import Queue as queue
except ImportError:
    import queue
import time
import os

class ArmoryCamStream(object):
    width = 1920
    height = 1080
    channels = 3  # RGB

    #Debug
    frame_num = 0
    last_frame = None

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
        try:
            raw_bytes = self._proc.stdout.read(self.height * self.width * self.channels)
            np_frame = np.frombuffer(raw_bytes, dtype=np.uint8).reshape((self.height, self.width, self.channels))
        except Exception as e:
            raise exceptions.StreamError(err_obj=e)

        # Debug
        self.frame_num += 1
        if self.frame_num % 25 == 0:
            if np.array_equal(self.last_frame, np_frame):
                print("##################################")
                print("###### SAME FRAME DETECTED #######")
                print("##################################")
            print("Hit 25 frames")
            self.frame_num = 0
            self.last_frame = np_frame

        return np_frame

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
        try:
            success, frame = self._capture.read()
            if not success:
                raise exceptions.StreamError(message="Failed Iteration inside of stream.next()")
        except Exception as e:
            raise exceptions.StreamError(err_obj=e)
        return frame

    next = __next__

    def __iter__(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class TwitchOutputStream(object):
    def __init__(self, width=480, height=270, fps=24, verbose=False):
        self.twitch_stream_key = api.TWITCH_STREAM_KEY
        self.width = width
        self.height = height
        self.fps = fps
        self.ffmpeg_process = None
        self.video_pipe = None
        self.ffmpeg_binary = constant.FFMPEG_PATH
        self.verbose = verbose

        # Try to open a new ffmpeg process
        try:
            self.reset()
        except OSError:
            print("ffmpeg not installed at %s" % self.ffmpeg_binary)
            sys.exit(1)

    def reset(self):
        """
        Reset the videostream by restarting ffmpeg
        """

        if self.ffmpeg_process is not None:
            # Close the previous stream
            try:
                self.ffmpeg_process.send_signal(signal.SIGINT)
            except OSError:
                pass

        command = [
            constant.FFMPEG_PATH,
            '-loglevel', 'info',
            '-i', '/tmp/videopipe',  # The input comes from a pipe
            '-f', 'rawvideo',
            '-videocodec', 'rawvideo',
            '-r', '24',  # set a fixed frame rate
            '-c:v', 'libx264',
            # size of one frame
            '-s', str(self.width) + 'x' + str(self.height),
            '-an',  # Tells FFMPEG not to expect any audio
            '-b:v', '3000k',
            '-preset', 'fast', '-tune', 'zerolatency',
            '-pix_fmt', 'yuv440p',
            '-g', '48',  # key frame distance

            # NUMBER OF THREADS
            '-threads', '0',

            # STREAM TO TWITCH
            '-f', 'flv', '%s' % api.TWITCH_STREAM_KEY
        ]

        command = " ".join(command)

        devnullpipe = open("/dev/null", "w")  # Throw away stream

        if self.verbose:
            devnullpipe = None
        self.ffmpeg_process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stderr=devnullpipe,
            stdout=devnullpipe,
            bufsize=-1
        )

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        # sigint so avconv can clean up the stream nicely
        self.ffmpeg_process.send_signal(signal.SIGINT)
        # waiting doesn't work because of reasons I don't know
        # self.pipe.wait()

    def send_video_frame(self, frame):
        """Send frame of shape (height, width, 3)
        with values between 0 and 1.
        Raises an OSError when the stream is closed.
        :param frame: array containing the frame.
        :type frame: numpy array with shape (height, width, 3)
            containing values between 0.0 and 1.0
        """
        if self.video_pipe is None:
            if not os.path.exists('/tmp/videopipe'):
                os.mkfifo('/tmp/videopipe')
            self.video_pipe = os.open('/tmp/videopipe', os.O_WRONLY)

        assert frame.shape == (self.height, self.width, 3)

        frame = np.clip(255 * frame, 0, 255).astype('uint8')
        try:
            os.write(self.video_pipe, frame.tostring())
            print("Wrote to pipe!")
        except OSError:
            # The pipe has been closed. Reraise and handle it further
            # downstream
            raise
