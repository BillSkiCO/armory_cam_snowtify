import os
from enum import Enum

STREAM_URL = 'http://tower.armorycam.com/stream/armorystream.m3u8'
TEST_URL = 'C:/Users/wgolembi/Desktop/armory_analytics/samples/light_to_med_light.mp4'
#TEST_URL = '/home/wgolembi/aa/armory_analytics/very_light.mp4'
FFMPEG_PATH = os.path.dirname(__file__) + '/ffmpeg-4.2.1/bin/ffmpeg.exe'
#FFMPEG_PATH = "/usr/bin/ffmpeg"

FFMPEG_COMMAND = [FFMPEG_PATH, '-i', TEST_URL,
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

NOTIFY_EVENT_WINDOW_SECS = 120       # Time for event window (length of "pseudo circular buffer")
NOTIFY_THRESHOLD = .5                # % event window filled with snow_events to trigger notification
NOT_SNOWING_THRESHOLD = .9           # % event window that needs to be filled with no_snow_events to dictate no snow
NOTIF_REFRACTORY_SECS = 60 * 60 * 2  # Number of seconds of no snow to reset notification trigger
