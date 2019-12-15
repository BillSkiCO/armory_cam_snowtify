
class StreamError(Exception):
    def __init__(self, err_obj=None, message=None):
        if err_obj:
            self.message = "Stream Error: " + err_obj.__repr__()
        if message:
            self.message = "Stream Error: " + message
