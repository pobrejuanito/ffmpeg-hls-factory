import ConfigParser

class EncoderSettings(object):

    def __init__(self):

        config = ConfigParser.ConfigParser()
        config.read('settings.ini')
        self.log_file = config.get('Encoder','Log')
        self.ffmpeg = config.get('Encoder','ffmpeg')
        self.ffprobe = config.get('Encoder','ffprobe')



