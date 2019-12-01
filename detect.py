import cv2 as cv
import numpy as np


class QParam(object):
    def __init__(self, min=0, max=255, decay=1):
        self.value = 0
        self.min = min
        self.max = max
        self.decay = decay

    def update(self, keypoints):
        # TODO: this is just a hack for right now,
        #       we need a more robust impulse response function

        # when value is large, growth is slowed
        growth = (len(keypoints) * 16) / max(self.value, 1)
        delta = growth - self.decay
        self.value = int(min(max(self.value + delta, self.min), self.max))


class SnowDetector(object):

    @staticmethod
    def _get_blob_detector_params():
        params = cv.SimpleBlobDetector_Params()

        # Change thresholds
        params.minThreshold = 5
        params.maxThreshold = 20

        # Filter by Area.
        params.filterByArea = True
        params.minArea = 9
        params.maxArea = 10

        # Filter by Circularity
        params.filterByCircularity = False
        params.minCircularity = 0.1

        # Filter by Convexity
        params.filterByConvexity = False
        params.minConvexity = 0.87

        # Filter by Inertia
        params.filterByInertia = False
        params.minInertiaRatio = 0.25

        # Filter By Color
        params.filterByColor = True
        params.blobColor = 255

        return params

    @staticmethod
    def _mask_out_areas(frame):

        # Define mask same size as frame, fill with 0s
        mask = np.zeros(frame.shape, dtype=np.uint8)

        # MARK: Define polygons of interest.
        poly_region1 = np.array([[(0, 84), (260, 130), (260, 170), (0,274)]], dtype=np.int32)
        poly_region2 = np.array([[(440, 0), (650, 0), (650,250),(510, 250)]], dtype=np.int32)

        # fill the  so it doesn't get wiped out when the mask is applied
        channel_count = frame.shape[2]
        ignore_mask_color = (255,) * channel_count
        cv.fillPoly(mask, poly_region1, ignore_mask_color)
        cv.fillPoly(mask, poly_region2, ignore_mask_color)

        # apply the mask
        masked_frame = cv.bitwise_and(frame, mask)

        return masked_frame


    def __init__(self):
        self._background_subtractor = cv.createBackgroundSubtractorMOG2()
        params = self._get_blob_detector_params()
        self._blob_detector = cv.SimpleBlobDetector_create(params)
        self._q_param = QParam()
        self._debug_mask = False
        self._debug_keypoints = None

    def detect(self, frame):

        frame = self._mask_out_areas(frame)

        fgmask = self._background_subtractor.apply(frame)
        fgmask[fgmask < 255] = 0

        self._debug_mask = fgmask

        keypoints = self._blob_detector.detect(fgmask)

        if keypoints:
            print(keypoints)

        self._debug_keypoints = keypoints
        self._q_param.update(keypoints)
        return self._q_param.value
