import cv2 as cv


def resize(stream, scale=1):
    for frame in stream:
        yield cv.resize(frame, None, fx=scale, fy=scale, interpolation=cv.INTER_AREA)


def blur(stream, kernel_size=3):
    for frame in stream:
        yield cv.GaussianBlur(frame, (kernel_size, kernel_size), 0)
