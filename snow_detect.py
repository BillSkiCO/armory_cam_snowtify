from itertools import islice

import cv2 as cv
import numpy as np

from .detect import SnowDetector
from .stream import ArmoryCamStream, FileStream
from .filter import blur, resize


def main(filename=None, offset_frames=0):
    cv.namedWindow('view', cv.WINDOW_NORMAL)
    cv.namedWindow('mask', cv.WINDOW_NORMAL)

    cv.resizeWindow('view', 480, 270)
    cv.resizeWindow('mask', 480, 270)

    font = cv.FONT_HERSHEY_SIMPLEX

    detector = SnowDetector()

    # Read frames from file if provided, otherwise read from live stream
    if filename is not None:
        stream = FileStream(filename, offset=offset_frames)
    else:
        stream = ArmoryCamStream()

    with stream:
        stream = resize(stream, scale=0.25)
        stream = blur(stream, kernel_size=9)

        for frame in stream:

            snow_confidence = detector.detect(frame)

            displayed = cv.drawKeypoints(frame, detector._debug_keypoints, np.array([]), (0, 0, 255),
                                         cv.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)

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
            cv.imshow('mask', detector._debug_mask)
            if cv.waitKey(30) & 0xff == 27:
                break


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
