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
        self.slave_id = config.get('MasterAPI','SlaveId')
        self.__prepareRequest()

    # Gets a job, if no job returns an empty list
    def getJob(self):

        new_job = Job()
        data = {'slaveId': self.slave_id}

        params = urllib.urlencode(data)
        url = self.api_url + self.fetch_job_action + '?' + params

        request = urllib2.Request(url)

        try:
            data = json.load(urllib2.urlopen(request))
            if data['count'] > 0 :
                new_job.fileName = data['result'][0]['fileName']
                new_job.downloadURL = data['result'][0]['downloadURL']
                new_job.destinationURL = data['result'][0]['destinationURL']
                new_job.id = data['result'][0]['jobId']
                logging.info("API: job found: " + new_job.fileName)
            else:
                logging.info("API: No jobs available")

        except urllib2.HTTPError as e:
            logging.warning(e)

        return new_job

    # check in job with the master
    def checkInJob(self, job):

        params = urllib.urlencode({'slaveId': self.slave_id, 'status': job.status})
        url = self.api_url + self.fetch_job_action + '/' + job.id + '?' + params
        request = urllib2.Request(url)
        request.get_method = lambda : 'PUT' # not very pretty
        data = json.load(urllib2.urlopen(request))
        logging.info('API: Job updated with status %s' % (job.status))

    def __prepareRequest(self):

        password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
        password_mgr.add_password(None, self.api_url, self.api_username, self.api_password)

        auth = urllib2.HTTPBasicAuthHandler(password_mgr) # create an authentication handler
        opener = urllib2.build_opener(auth) # create an opener with the authentication handler
        urllib2.install_opener(opener) # install the opener...


