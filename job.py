import ConfigParser, logging,urllib, json, subprocess
import boto,os, shutil

class Job(object):

    def __init__(self):

        config = ConfigParser.ConfigParser()
        config.read('settings.ini')

        self.id = 0
        self.media_info = {}
        self.status = 'Unknown'
        self.fileName = ''
        self.downloadPath = ''
        self.downloadHostname = ''
        self.destinationURL = ''
        self.ffmpeg = config.get('Encoder','ffmpeg')
        self.ffprobe = config.get('Encoder','ffprobe')
        self.ffprobe_params = config.get('Encoder','ffprobe_params')
        self.audio_encoder = config.get('Encoder','audio_encoder')
        self.hls_config = {
            'audio': {
                'profile': config.get('Encoder','hls_audio'),
                'bandwidth': config.get('Encoder','audio_bandwidth'),
                'name': config.get('Encoder','audio_name')
            },
            'cell' : {
                'profile': config.get('Encoder','hls_cell'),
                'bandwidth': config.get('Encoder','cell_bandwidth'),
                'name': config.get('Encoder','cell_name')
            },
            'wifi_360': {
                'profile': config.get('Encoder','hls_wifi_360'),
                'bandwidth': config.get('Encoder','wifi_360_bandwidth'),
                'name': config.get('Encoder','wifi_360_name')
            },
            'wifi_720': {
                'profile': config.get('Encoder','hls_wifi_720'),
                'bandwidth': config.get('Encoder','wifi_720_bandwidth'),
                'name': config.get('Encoder','wifi_720_name')
            },
            'wifi_1080': {
                'profile': config.get('Encoder','hls_wifi_1080'),
                'bandwidth': config.get('Encoder','wifi_1080_bandwidth'),
                'name': config.get('Encoder','wifi_1080_name')
            }
        }
        self.mp4_config = {
            '240': config.get('Encoder','mp4_240'),
            '360': config.get('Encoder','mp4_360'),
            '720': config.get('Encoder','mp4_720'),
            '1080': config.get('Encoder','mp4_1080')
        }
        self.output_dir_hls = config.get('Encoder','output_dir_hls')
        self.output_dir_mp4 = config.get('Encoder','output_dir_mp4')
        self.s3_bucket = config.get('AWS_S3','Bucket')
        self.s3_access = config.get('AWS_S3','ACCESS_KEY_ID')
        self.s3_secret = config.get('AWS_S3','SECRET_ACCESS_KEY')
        self.ios_playlist = ''
        self.web_playlist = ''
        self.mp4_file_name = ''
        # if the output directory does not exists, create one
        if not os.path.exists(self.output_dir_hls):
            os.makedirs(self.output_dir_hls)

        if not os.path.exists(self.output_dir_mp4):
            os.makedirs(self.output_dir_mp4)

    def downloadFile(self):

        opener = urllib.URLopener()
        try:
            full_path = self.downloadHostname + self.downloadPath + self.fileName
            logging.info("Job downloading %s from %s" % (self.fileName, full_path))
            opener.retrieve(full_path.encode('utf-8'), self.fileName)

        except IOError as e:
            logging.warning(e)
            raise Exception('DOWNLOAD FILE: Error: ' + e)

    def generateHLS(self):

        for key in sorted(self.hls_config):
            cmd = (self.hls_config[key]['profile'] % (
                self.ffmpeg,
                self.fileName,
                self.audio_encoder,
                self.output_dir_hls+key)
            ).split()
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, err =  p.communicate()
            logging.info('GENERATE HLS: Generating %s' % (key))
            print out, err
        # generate index m3u8
        self.writeIOSPlaylist()
        self.writeWebPlaylist();


    def generateMp4(self, api):

        self.probeMediaFile()

        height = 1080
        self.mp4_file_name, file_extension = os.path.splitext(self.fileName)

        if 'height' in self.media_info:
            height = int(self.media_info['height'])

        for key in self.mp4_config:

            if height >= int(key):

                logging.info('GENERATE MP4: Generating %s' % (key))
                cmd = (self.mp4_config[key] % (
                    self.ffmpeg,
                    self.fileName,
                    self.audio_encoder,
                    self.output_dir_mp4+self.mp4_file_name+key)
                ).split()

                print self.recordingId, self.media_info, self.fileName
                #p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                #out, err =  p.communicate()

                #if p.returncode:
                #    logging.info('GENERATE MP4: ffmpeg failed out %s err %s' %(out,err))
                #else:
                #    logging.info('GENERATE MP4: Checking In')
                    # TODO
                    #api.checkInMp4Flavor({
                    #    'recordingId': self.recordingId,
                    #    'filename': self.fileName,
                    #    'filesize': '',
                    #    'duration': '',
                    #    'bitrate': '',
                    #    'width': '',
                    #    'height': '',
                    #})
            else:
                logging.info('GENERATE MP4: Skipping %s (input movie is %s)' % (key, height))


    def writeIOSPlaylist(self):

        file_name, file_extension = os.path.splitext(self.fileName)
        self.ios_playlist = file_name + ".m3u8"

        f = open(self.ios_playlist, 'w')
        f.write('#EXTM3U\n')

        for key in sorted(self.hls_config):

            f.write('#EXT-X-STREAM-INF:PROGRAM-ID=1,NAME="%s",BANDWIDTH=%s\n'%(self.hls_config[key]['name'], self.hls_config[key]['bandwidth']))
            f.write(self.output_dir_hls+key+'_.m3u8\n')

        f.close()
        logging.info('WRITE IOS PLAYLIST: Playlist %s generated'%(self.ios_playlist))

    def writeWebPlaylist(self):

        file_name, file_extension = os.path.splitext(self.fileName)
        self.web_playlist = file_name + "_web.m3u8"

        f = open(self.web_playlist, 'w')
        f.write('#EXTM3U\n')

        for key in sorted(self.hls_config):
            # omitt audio
            if key != 'audio':
                f.write('#EXT-X-STREAM-INF:PROGRAM-ID=1,NAME="%s",BANDWIDTH=%s\n'%(self.hls_config[key]['name'], self.hls_config[key]['bandwidth']))
                f.write(self.output_dir_hls+key+'_.m3u8\n')

        f.close()
        logging.info('WRITE WEB PLAYLIST: Playlist %s generated'%(self.web_playlist))

    def transferToS3(self):

        # destination directory name (on s3)
        upload_file_names = []

        try:
            conn = boto.connect_s3(self.s3_access,self.s3_secret)
            bucket = conn.get_bucket(self.s3_bucket)

            for (self.output_dir_hls, dirname, filename) in os.walk(self.output_dir_hls):
                upload_file_names.extend(filename)
                break

            logging.info('S3 TRANSFER: Uploading files to bucket %s' % (self.s3_bucket))

            for filename in upload_file_names:

                source_path = os.path.join(self.output_dir_hls + filename)
                dest_path = os.path.join(self.destinationURL + self.output_dir_hls, filename)

                k = boto.s3.key.Key(bucket)
                k.key = dest_path
                k.set_contents_from_filename(source_path)
                k.set_acl('public-read')

            # Upload index playlist
            k = boto.s3.key.Key(bucket)
            k.key = os.path.join(self.destinationURL, self.ios_playlist)
            k.set_contents_from_filename(os.path.join(self.ios_playlist))
            k.set_acl('public-read')

            k = boto.s3.key.Key(bucket)
            k.key = os.path.join(self.destinationURL, self.web_playlist)
            k.set_contents_from_filename(os.path.join(self.web_playlist))
            k.set_acl('public-read')
            # update job status
            self.status = 'OK'

        except boto.exception.S3ResponseError as e:
            logging.error(e) # 403 Forbidden, 404 Not Found
            raise Exception('S3 TRANSFER: Error: ' + e)

    def probeMediaFile(self):

        cmd = (self.ffprobe_params % (self.ffprobe, self.fileName)).split()
        logging.info('MEDIA PROBE: Probing %s' % self.fileName)
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err =  p.communicate()
        #print out
        for line in out.split(os.linesep):
            if line.strip():
                name, value = line.partition("=")[::2]
                self.media_info[name.strip()] = value


    def cleanUp(self):

        logging.info('Job: Cleaning up')
        shutil.rmtree(self.output_dir_hls) # delete a directory with all of its contents
        os.remove(self.ios_playlist)
        os.remove(self.web_playlist)
        os.remove((self.fileName))


    def __str__(self):

        print self.id, self.status, self.fileName, self.downloadPath, self.downloadHostname, self.output_dir_hls
