import os
from enum import Enum

STREAM_URL = 'http://tower.armorycam.com/stream/armorystream.m3u8'
TEST_URL = '/home/wgolembi/aa/armory_analytics/mh.mp4'
#FFMPEG_PATH = os.path.dirname(__file__) + '/ffmpeg-4.2.1/bin/ffmpeg.exe'
FFMPEG_PATH = "/usr/bin/ffmpeg"

FFMPEG_COMMAND = [FFMPEG_PATH, '-i', STREAM_URL,
                  #'-loglevel', 'quiet',  # no text output
                  '-r 24',
                  '-an',  # disable audio
                  '-f', 'image2pipe',
                  '-pix_fmt', 'bgr24',
                  '-vcodec', 'rawvideo', '-',
                  ]

FFMPEG_COMMAND = " ".join(FFMPEG_COMMAND)

class FrameSize(Enum):
    HEIGHT = 270
    WIDTH = 480
    #WIDTH = 960
    #HEIGHT = 540

IMPULSE_DECAY = 5

DEBUG=True
