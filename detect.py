import cv2 as cv


class QParam(object):
    def __init__(self, min=0, max=255, decay=10):
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
        params.filterByColor = True
        params.blobColor = 255
        params.minThreshold = 10
        params.maxThreshold = 200
        params.filterByArea = True
        params.minArea = 1
        params.maxArea = 80
        params.filterByCircularity = False
        # params.minCircularity = 0.1
        params.filterByConvexity = False
        # params.minConvexity = 0.87

    def __init__(self):
        self._background_subtractor = cv.createBackgroundSubtractorMOG2()
        params = self._get_blob_detector_params()
        self._blob_detector = cv.SimpleBlobDetector_create(params)
        self._q_param = QParam()
        self._debug_mask = None
        self._debug_keypoints = None

    def detect(self, frame):
        fgmask = self._background_subtractor.apply(frame)
        fgmask[fgmask < 255] = 0
        self._debug_mask = fgmask
        keypoints = self._blob_detector.detect(fgmask)
        self._debug_keypoints = keypoints
        self._q_param.update(keypoints)
        return self._q_param.value
