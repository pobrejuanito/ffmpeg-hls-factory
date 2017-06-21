# ApiManager
# Description: Gets a new job from master, checks in a job from master

import logging, ConfigParser, urllib, urllib2, json
from job import Job


class ApiManager(object):

    def __init__(self):

        config = ConfigParser.ConfigParser()
        config.read('settings.ini')
        self.api_url = config.get('MasterAPI', 'URL')
        self.api_username = config.get('MasterAPI', 'Username')
        self.api_password = config.get('MasterAPI', 'Password')
        self.fetch_job_action = config.get('MasterAPI', 'Fetchjob')
        self.slave_id = config.get('MasterAPI', 'SlaveId')
        self.world_api_url = config.get('WorldAPI', 'URL')
        self.mp4_checkin_url = config.get('WorldAPI', 'CheckInMP4URL')
        self.world_api_header = {"Authorization": "Bearer %s" % config.get('WorldAPI', 'Token')}
        self.__prepareRequest()

    # Gets a job, if no job returns an empty list
    def get_job(self):

        new_job = Job()
        data = {'slaveId': self.slave_id}

        params = urllib.urlencode(data)
        url = self.api_url + self.fetch_job_action + '?' + params

        request = urllib2.Request(url)

        try:
            data = json.load(urllib2.urlopen(request))
            if data['count'] > 0 :
                new_job.fileName = data['result'][0]['fileName']
                new_job.recordingId = data['result'][0]['recordingId']
                new_job.downloadPath = data['result'][0]['downloadPath']
                new_job.downloadHostname = data['result'][0]['downloadHostname']
                new_job.destinationURL = data['result'][0]['destinationURL']
                new_job.id = data['result'][0]['jobId']
                logging.info("API: job found: " + new_job.fileName)
            else:
                logging.info("API: No jobs available")

        except urllib2.HTTPError as e:
            logging.warning(e)

        return new_job

    def getLocalJob(self):
        # Gets a job, if no job returns an empty list
        new_job = Job()
        new_job.fileName = 'SampleVideo_1280x720_10mb.mp4'
        new_job.recordingId = 1
        new_job.downloadPath = ''
        new_job.downloadHostname = ''
        new_job.destinationURL = ''
        new_job.id = 1
        return new_job

    def checkin_job(self, job):
        # check in job with the master
        params = urllib.urlencode({'slaveId': self.slave_id, 'status': job.status})
        url = self.api_url + self.fetch_job_action + '/' + job.id + '?' + params
        request = urllib2.Request(url)
        # not very pretty
        request.get_method = lambda : 'PUT'
        data = json.load(urllib2.urlopen(request))
        logging.info('API: Job updated with status %s' % (job.status))

    def checkin_mp4_flavor(self, payload):

        url = self.world_api_url + '/' + self.mp4_checkin_url
        request = urllib2.Request(url, urllib.urlencode(payload), self.world_api_header)
        # not very pretty
        request.get_method = lambda: 'POST'

        try:
            data = json.load(urllib2.urlopen(request))
            if data['status_code'] is not 201:
                logging.info('CHECKIN MP4: error checking in flavor: %')
            else:
                logging.info('CHECKIN MP4: flavor Added')

        except urllib2.HTTPError as e:
            logging.warning("CHECKIN MP4: %s" % e)

    def __prepareRequest(self):

        password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
        password_mgr.add_password(None, self.api_url, self.api_username, self.api_password)
        # create an authentication handler
        auth = urllib2.HTTPBasicAuthHandler(password_mgr)
        # create an opener with the authentication handler
        opener = urllib2.build_opener(auth)
        # install the opener...
        urllib2.install_opener(opener)
