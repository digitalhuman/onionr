import urllib, requests, time
import logger
def local_command(utils_inst, command, data='', silent = True, post=False, postData = {}, maxWait=20):
    '''
        Send a command to the local http API server, securely. Intended for local clients, DO NOT USE for remote peers.
    '''
    # TODO: URL encode parameters, just as an extra measure. May not be needed, but should be added regardless.
    hostname = ''
    waited = 0
    while hostname == '':
        try:
            hostname = utils_inst.getClientAPIServer()
        except FileNotFoundError:
            time.sleep(1)
            waited += 1
            if waited == maxWait:
                return False
    if data != '':
        data = '&data=' + urllib.parse.quote_plus(data)
    payload = 'http://%s/%s%s' % (hostname, command, data)
    try:
        if post:
            retData = requests.post(payload, data=postData, headers={'token': config.get('client.webpassword'), 'Connection':'close'}, timeout=(maxWait, maxWait)).text
        else:
            retData = requests.get(payload, headers={'token': config.get('client.webpassword'), 'Connection':'close'}, timeout=(maxWait, maxWait)).text
    except Exception as error:
        if not silent:
            logger.error('Failed to make local request (command: %s):%s' % (command, error), terminal=True)
        retData = False

    return retData