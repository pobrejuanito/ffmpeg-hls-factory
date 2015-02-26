#!/opt/local/bin/python -tt
# 1. Fetch job metadata from master
# 2. Download video from S3
# 3. Encode video into HLS
# 4. Generate main m3u8 file
# 5. Upload video to S3
# 6. Report job complete
#
import logging, os, sys
from config import EncoderSettings
from api import ApiManager

def main():

    init()

    # check if the script is already running
    pid = str(os.getpid())
    pidfile = "/tmp/encoder.pid"

    if os.path.isfile(pidfile):
        logging.warning("%s already exists, exiting" % pidfile)
        sys.exit()
    else:
        file(pidfile, 'w').write(pid)

    logging.info("### JOB START ###")

    api = ApiManager()
    # Get Job
    job = api.getJob()
    if job.id != 0:
        try:
            job.downloadFile()
            job.probeMetadata()
            job.generateHLS()
            job.transferToS3()
            job.cleanUp()

        except Exception as e:
            job.status = 'Job Error: ' + e.__str__()

        api.checkInJob(job)

    #print job.__str__()
    logging.info("### JOB END   ###")
    os.unlink(pidfile)

def init():

    settings = EncoderSettings()
    # Setup Logging
    logging.basicConfig(
        filename=settings.log_file,
        format='%(asctime)s %(message)s',
        datefmt='%m/%d/%Y %I:%M:%S %p',
        level=logging.INFO
    )

if __name__ == '__main__':
    main()