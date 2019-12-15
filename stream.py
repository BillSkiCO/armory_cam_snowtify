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
    """
    Initialize a TwitchOutputStream object and starts the pipe.
    The stream is only started on the first frame.
    :param twitch_stream_key:
    :type twitch_stream_key:
    :param width: the width of the videostream (in pixels)
    :type width: int
    :param height: the height of the videostream (in pixels)
    :type height: int
    :param fps: the number of frames per second of the videostream
    :type fps: float
    :param enable_audio: whether there will be sound or not
    :type enable_audio: boolean
    :param ffmpeg_binary: the binary to use to create a videostream
        This is usually ffmpeg, but avconv on some (older) platforms
    :type ffmpeg_binary: String
    :param verbose: show ffmpeg output in stdout
    :type verbose: boolean
    """

    def __init__(self,
                 width=480,
                 height=270,
                 fps=24,
                 enable_audio=False,
                 verbose=False):
        self.twitch_stream_key = api.TWITCH_STREAM_KEY
        self.width = width
        self.height = height
        self.fps = fps
        self.ffmpeg_process = None
        self.video_pipe = None
        self.audio_pipe = None
        self.ffmpeg_binary = constant.FFMPEG_PATH
        self.verbose = verbose
        self.audio_enabled = enable_audio
        try:
            self.reset()
        except OSError:
            print("There seems to be no %s available" % self.ffmpeg_binary)
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
            '-loglevel', 'verbose',
            '-y',  # overwrite previous file/stream
            '-analyzeduration', '1',
            '-f', 'rawvideo',
            '-r', '24',  # set a fixed frame rate
            '-vcodec', 'libx264',
            # size of one frame
            '-s', '%dx%d' % (self.width, self.height),
            '-i', '/tmp/videopipe',  # The input comes from a pipe
            '-an',  # Tells FFMPEG not to expect any audio
            '-b:v', '3000k',
            '-preset', 'faster', '-tune', 'zerolatency',
            '-crf', '23',
            '-pix_fmt', 'yuv420p',
            '-bufsize', '-1',
            '-g', '48',  # key frame distance

            # MAP THE STREAMS
            # use only video from first input and only audio from second
            '-map', '0:v',

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
            stdout=devnullpipe)

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
        except OSError:
            # The pipe has been closed. Reraise and handle it further
            # downstream
            raise


class TwitchOutputStreamRepeater(TwitchOutputStream):
    """
    This stream makes sure a steady framerate is kept by repeating the
    last frame when needed.
    Note: this will not generate a stable, stutter-less stream!
     It does not keep a buffer and you cannot synchronize using this
     stream. Use TwitchBufferedOutputStream for this.
    """

    def __init__(self, *args, **kwargs):
        super(TwitchOutputStreamRepeater, self).__init__(*args, **kwargs)

        self.lastframe = np.ones((self.height, self.width, 3))
        self._send_last_video_frame()  # Start sending the stream

    def _send_last_video_frame(self):
        try:
            super(TwitchOutputStreamRepeater,
                  self).send_video_frame(self.lastframe)
        except OSError:
            # stream has been closed.
            # This function is still called once when that happens.
            pass
        else:
            # send the next frame at the appropriate time
            threading.Timer(1. / self.fps,
                            self._send_last_video_frame).start()

    def send_video_frame(self, frame):
        """Send frame of shape (height, width, 3)
        with values between 0 and 1.
        :param frame: array containing the frame.
        :type frame: numpy array with shape (height, width, 3)
            containing values between 0.0 and 1.0
        """
        self.lastframe = frame


class TwitchBufferedOutputStream(TwitchOutputStream):
    """
    This stream makes sure a steady framerate is kept by buffering
    frames. Make sure not to have too many frames in buffer, since it
    will increase the memory load considerably!
    Adding frames is thread safe.
    """

    def __init__(self, *args, **kwargs):
        super(TwitchBufferedOutputStream, self).__init__(*args, **kwargs)
        self.last_frame = np.ones((self.height, self.width, 3))
        self.last_frame_time = None
        self.next_video_send_time = None
        self.frame_counter = 0
        self.q_video = queue.PriorityQueue()

        # don't call the functions directly, as they block on the first
        # call
        self.t = threading.Timer(0.0, self._send_video_frame)
        self.t.daemon = True
        self.t.start()

    def _send_video_frame(self):
        start_time = time.time()
        try:
            frame = self.q_video.get_nowait()
            # frame[0] is frame count of the frame
            # frame[1] is the frame
            frame = frame[1]
        except IndexError:
            frame = self.last_frame
        except queue.Empty:
            frame = self.last_frame
        else:
            self.last_frame = frame

        try:
            super(TwitchBufferedOutputStream, self
                  ).send_video_frame(frame)
        except OSError:
            # stream has been closed.
            # This function is still called once when that happens.
            # Don't call this function again and everything should be
            # cleaned up just fine.
            return

        # send the next frame at the appropriate time
        if self.next_video_send_time is None:
            self.t = threading.Timer(1. / self.fps, self._send_video_frame)
            self.next_video_send_time = start_time + 1. / self.fps
        else:
            self.next_video_send_time += 1. / self.fps
            next_event_time = self.next_video_send_time - start_time
            if next_event_time > 0:
                self.t = threading.Timer(next_event_time,
                                         self._send_video_frame)
            else:
                # we should already have sent something!
                #
                # not allowed for recursion problems :-(
                # (maximum recursion depth)
                # self.send_me_last_frame_again()
                #
                # other solution:
                self.t = threading.Thread(
                    target=self._send_video_frame)

        self.t.daemon = True
        self.t.start()

    def send_video_frame(self, frame, frame_counter=None):
        """send frame of shape (height, width, 3)
        with values between 0 and 1
        :param frame: array containing the frame.
        :type frame: numpy array with shape (height, width, 3)
            containing values between 0.0 and 1.0
        :param frame_counter: frame position number within stream.
            Provide this when multi-threading to make sure frames don't
            switch position
        :type frame_counter: int
        """
        if frame_counter is None:
            frame_counter = self.frame_counter
            self.frame_counter += 1

        self.q_video.put((frame_counter, frame))


    def get_video_frame_buffer_state(self):
        """Find out how many video frames are left in the buffer.
        The buffer should never run dry, or audio and video will go out
        of sync. Likewise, the more filled the buffer, the higher the
        memory use and the delay between you putting your frame in the
        stream and the frame showing up on Twitch.
        :return integer estimate of the number of video frames left.
        """
        return self.q_video.qsize()
