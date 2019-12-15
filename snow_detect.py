import cv2 as cv
import numpy as np
import constant as c
import time
import constant
import exceptions


from detect import SnowDetector
from stream import ArmoryCamStream, FileStream, TwitchOutputStream
from filter import blur, resize
from snowtify import Snowtification

def main(filename=None, offset_frames=0):

    #Set up view and mask output windows
    cv.namedWindow('view', cv.WINDOW_NORMAL)
    cv.resizeWindow('view', c.FrameSize.WIDTH.value, c.FrameSize.HEIGHT.value)
    font = cv.FONT_HERSHEY_SIMPLEX

    if constant.DEBUG == True:
        cv.namedWindow('mask', cv.WINDOW_NORMAL)
        cv.resizeWindow('mask', c.FrameSize.WIDTH.value, c.FrameSize.HEIGHT.value)

    # Initialize detector
    detector = SnowDetector()

    # Initialize Snowtification
    snowtify = Snowtification()

    # Read frames from file if provided, otherwise read from live stream
    if filename is not None:
        stream = FileStream(filename, offset=offset_frames)
    else:
        stream = ArmoryCamStream()
        if constant.STREAMING:
            twitch = TwitchOutputStream()

    try:
        with stream:
            stream = resize(stream, scale=.25)
            stream = blur(stream, kernel_size=3)

            # Use custom built iterator in ArmoryCamStream object to keep grabbing
            # frames from the video
            frame_hop = 0
            for frame in stream:

                if frame_hop % 3 == 0:
                    frame_hop = 0
                    snow_confidence = detector.detect(frame)

                    # If we exceed impulse decay we've detected snow. Log it.
                    if snow_confidence > constant.IMPULSE_DECAY + 1:
                        snowtify.log_snow_event()

                displayed = cv.drawKeypoints(frame, detector._debug_keypoints, np.array([]), (0, 0, 255),
                                             cv.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)
                print(type(displayed))

                cv.putText(
                    displayed,
                    str(snow_confidence),
                    (40, 30),
                    font,
                    1,
                    (0, 0, 255),
                    2,
                    cv.LINE_AA
                )

                cv.imshow('view', displayed)
                # if constant.STREAMING is True:
                if constant.STREAMING:
                    twitch.send_video_frame(displayed)
                if constant.DEBUG == True:
                    cv.imshow('mask', detector._debug_mask)
                if cv.waitKey(30) & 0xff == 27:
                    break

                frame_hop += 1



    except exceptions.StreamError as e:
        print(e.message)

if __name__ == '__main__':
     import argparse
     import os

     parser = argparse.ArgumentParser()
     parser.add_argument('--file', '-f', type=str)
     parser.add_argument('--offset-frames', type=int, default=0)
     args = parser.parse_args()

     if args.file is None:
         filename = None
     else:
         filename = os.path.abspath(args.file)

     main(filename=filename, offset_frames=args.offset_frames)
