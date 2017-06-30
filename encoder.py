#!/usr/bin/env python
# 1. Fetch job metadata from master
# 2. Download video from S3
# 3. Encode video into HLS
# 4. Encode mp4 video to different flavors and check into db
# 4. Generate main m3u8 files
# 5. Upload video to S3
# 6. Report job complete
import logging, os, sys, ConfigParser
from api import ApiManager
from datetime import datetime, timedelta


def main():

    init()
    # First check if the script is already running
    pid = str(os.getpid())
    pid_file = "/tmp/encoder.pid"

    if os.path.isfile(pid_file):

        hours_ago = datetime.now() - timedelta(hours=12)
        file_time = datetime.fromtimestamp(os.path.getctime(pid_file))

        if file_time < hours_ago:
            # pid too old, delete
            logging.info("%s is stale removed" % pid_file)
            os.remove(pid_file)
        else:
            # encoder is still running
            logging.warning("%s already exists, exiting" % pid_file)
            sys.exit()

    file(pid_file, 'w').write(pid)

    # Get job from api
    api = ApiManager()
    job = api.get_job()
    #job = api.getLocalJob()

    if job.id != 0:
        logging.info("### JOB START ###")
        try:
            job.download_file()
            job.generate_hls(api)
            job.generate_mp4(api)
            job.transfer_S3()
            job.cleanup()
        except Exception as e:
            job.status = 'Job Error: ' + e.__str__()
        api.checkin_job(job)
        logging.info("### JOB END ###")

    os.unlink(pid_file)


def init():

    config = ConfigParser.ConfigParser()
    config.read('settings.ini')
    # Setup Logging
    logging.basicConfig(
        filename=config.get('Encoder','log_file'),
        format='%(asctime)s %(message)s',
        datefmt='%m/%d/%Y %I:%M:%S %p',
        level=logging.INFO
    )

if __name__ == '__main__':
    main()
