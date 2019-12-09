import cv2 as cv
import numpy as np
import constant


# Impulse control
# Control change in matches over time.
# Decay the number of matches by constant.IMPULSE_DECAY every frame
# and see if the number of matches can keep the average high.
# Decay argument will be the controlling variable
# Decay may change over the course of the day, might have to set based on time
class QParam(object):
    def __init__(self, min=0, max=255, decay=constant.IMPULSE_DECAY):
        self.value = 0
        self.min = min
        self.max = max
        self.decay = decay  # Decay of num keypoints matched per frame

    # Lightweight impulse response function
    def update(self, keypoints):
        growth = (len(keypoints)*8) / max(self.value, 1)  # Get growth percent of max
        delta = growth - self.decay
        self.value = int(min(max(self.value + delta, self.min), self.max))

        # Return impulse function adjusted value
        return self.value


class SnowDetector(object):

    @staticmethod
    def _get_blob_detector_params():
        params = cv.SimpleBlobDetector_Params()

        # Change thresholds
        params.minThreshold = 5
        params.maxThreshold = 200

        # Filter by Area.
        params.filterByArea = True
        params.minArea = 2
        params.maxArea = 20

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
        # poly_region1 = np.array([[(0, 84), (260, 130), (260, 170), (0,274)]], dtype=np.int32)
        # poly_region2 = np.array([[(440, 0), (650, 0), (650, 250), (510, 250)]], dtype=np.int32)

        poly_region1 = np.array([[(0, 42), (130, 65), (130, 85), (0,137)]], dtype=np.int32)
        poly_region2 = np.array([[(220, 0), (325, 0), (325, 125), (255, 125)]], dtype=np.int32)

        # fill the  so it doesn't get wiped out when the mask is applied
        channel_count = frame.shape[2]
        ignore_mask_color = (255,) * channel_count
        cv.fillPoly(mask, poly_region1, ignore_mask_color)
        cv.fillPoly(mask, poly_region2, ignore_mask_color)

        # apply the mask
        masked_frame = cv.bitwise_and(frame, mask)

        return masked_frame


    def __init__(self):
        self._background_subtractor = cv.createBackgroundSubtractorMOG2(detectShadows=False)
        params = self._get_blob_detector_params()
        self._blob_detector = cv.SimpleBlobDetector_create(params)
        self._q_param = QParam()
        self._debug_mask = None
        self._debug_keypoints = None

    def detect(self, frame):
        frame = self._mask_out_areas(frame)
        fgmask = self._background_subtractor.apply(frame)
        fgmask[fgmask < 255] = 0

        if constant.DEBUG == True:
            self._debug_mask = fgmask

        keypoints = self._blob_detector.detect(fgmask)

        if constant.DEBUG == True:
            self._debug_keypoints = keypoints
	        
        self._q_param.update(keypoints)
        return self._q_param.value
        
        
