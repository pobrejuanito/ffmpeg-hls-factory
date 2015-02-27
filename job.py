import ConfigParser, logging,urllib, json, subprocess
import boto,os, shutil

class Job(object):

    def __init__(self):

        config = ConfigParser.ConfigParser()
        config.read('settings.ini')

        self.id = 0
        self.status = 'Unknown'
        self.fileName = ''
        self.downloadURL = ''
        self.destinationURL = ''
        self.ffprobe = config.get('Encoder','ffprobe')
        self.ffmpeg = config.get('Encoder','ffmpeg')
        self.audio_encoder = config.get('Encoder','audio_encoder')
        self.profiles = {
            'audio': config.get('Encoder','hls_audio'),
            'cell' : config.get('Encoder','hls_cell'),
            'wifi' : config.get('Encoder','hls_wifi')
        }
        self.bandwidth = {
            'audio': config.get('Encoder','audio_bandwidth'),
            'cell' : config.get('Encoder','cell_bandwidth'),
            'wifi' : config.get('Encoder','wifi_bandwidth')
        }
        self.output_dir = config.get('Encoder','output_dir')
        self.s3_bucket = config.get('AWS_S3','Bucket')
        self.s3_access = config.get('AWS_S3','ACCESS_KEY_ID')
        self.s3_secret = config.get('AWS_S3','SECRET_ACCESS_KEY')
        self.index_playlist = ''

        # if the output directory does not exists, create one
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def downloadFile(self):

        opener = urllib.URLopener()
        try:
            logging.info("Job downloading %s from %s" % (self.fileName, self.downloadURL))
            opener.retrieve(self.downloadURL, self.fileName)
        except IOError as e:
            logging.warning(e)
            raise Exception('Job Error: ' + e)

    def generateHLS(self):

        for profile in sorted(self.profiles):

            cmd = (self.profiles[profile] % (
                self.ffmpeg,
                self.fileName,
                self.audio_encoder,
                self.output_dir+profile)
            ).split()
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, err =  p.communicate()
            logging.info('Job: Generating HSL for %s' % (profile))
            #print out, err
        # generate index m3u8
        self.writeMainPlaylist()


    def writeMainPlaylist(self):

        file_name, file_extension = os.path.splitext(self.fileName)
        self.index_playlist = file_name + ".m3u8"

        f = open(self.index_playlist, 'w')
        f.write('#EXTM3U\n')

        for key in sorted(self.bandwidth):

            f.write('#EXT-X-STREAM-INF:PROGRAM-ID=1,BANDWIDTH=%s\n'%(self.bandwidth[key]))
            f.write(self.output_dir+key+'_.m3u8\n')

        f.close()
        logging.info('Job: index playlist %s generated'%(self.index_playlist))

    def transferToS3(self):

        # destination directory name (on s3)
        upload_file_names = []

        try:
            conn = boto.connect_s3(self.s3_access,self.s3_secret)
            bucket = conn.get_bucket(self.s3_bucket)

            for (self.output_dir, dirname, filename) in os.walk(self.output_dir):
                upload_file_names.extend(filename)
                break

            logging.info('Job: uploading files to Amazon S3 bucket %s' % (self.s3_bucket))

            for filename in upload_file_names:

                source_path = os.path.join(self.output_dir + filename)
                dest_path = os.path.join(self.destinationURL + self.output_dir, filename)

                k = boto.s3.key.Key(bucket)
                k.key = dest_path
                k.set_contents_from_filename(source_path)
                k.set_acl('public-read')

            # Upload index playlist
            k = boto.s3.key.Key(bucket)
            k.key = os.path.join(self.destinationURL, self.index_playlist)
            k.set_contents_from_filename(os.path.join(self.index_playlist))
            k.set_acl('public-read')
            # update job status
            self.status = 'OK'

        except boto.exception.S3ResponseError as e:
            logging.error(e) # 403 Forbidden, 404 Not Found
            raise Exception('Job Error: ' + e)

    def cleanUp(self):

        shutil.rmtree(self.output_dir) # delete a directory with all of its contents
        os.remove(self.index_playlist)
        os.remove((self.fileName))
        logging.info('Job: Cleaning up')

    def __str__(self):

        print self.id, self.status, self.fileName, self.downloadURL, self.output_dir

