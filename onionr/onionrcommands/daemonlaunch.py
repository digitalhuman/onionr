import os, time, sys, platform, sqlite3
from threading import Thread
import onionr, api, logger, communicator
import onionrevents as events
from netcontroller import NetController
def daemon(o_inst):
    '''
        Starts the Onionr communication daemon
    '''

    # remove runcheck if it exists
    if os.path.isfile('data/.runcheck'):
        logger.debug('Runcheck file found on daemon start, deleting in advance.')
        os.remove('data/.runcheck')

    Thread(target=api.API, args=(o_inst, o_inst.debug, onionr.API_VERSION)).start()
    Thread(target=api.PublicAPI, args=[o_inst.getClientApi()]).start()
    try:
        time.sleep(0)
    except KeyboardInterrupt:
        logger.debug('Got keyboard interrupt, shutting down...')
        time.sleep(1)
        o_inst.onionrUtils.localCommand('shutdown')

    apiHost = ''
    while apiHost == '':
        try:
            with open(o_inst.onionrCore.publicApiHostFile, 'r') as hostFile:
                apiHost = hostFile.read()
        except FileNotFoundError:
            pass
        time.sleep(0.5)
    onionr.Onionr.setupConfig('data/', self = o_inst)

    if o_inst._developmentMode:
        logger.warn('DEVELOPMENT MODE ENABLED (NOT RECOMMENDED)', timestamp = False)
    net = NetController(o_inst.onionrCore.config.get('client.public.port', 59497), apiServerIP=apiHost)
    logger.debug('Tor is starting...')
    if not net.startTor():
        o_inst.onionrUtils.localCommand('shutdown')
        sys.exit(1)
    if len(net.myID) > 0 and o_inst.onionrCore.config.get('general.security_level') == 0:
        logger.debug('Started .onion service: %s' % (logger.colors.underline + net.myID))
    else:
        logger.debug('.onion service disabled')
    logger.debug('Using public key: %s' % (logger.colors.underline + o_inst.onionrCore._crypto.pubKey))
    time.sleep(1)

    o_inst.onionrCore.torPort = net.socksPort
    communicatorThread = Thread(target=communicator.startCommunicator, args=(o_inst, str(net.socksPort)))
    communicatorThread.start()
    
    while o_inst.communicatorInst is None:
        time.sleep(0.1)

    # print nice header thing :)
    if o_inst.onionrCore.config.get('general.display_header', True):
        o_inst.header()

    # print out debug info
    o_inst.version(verbosity = 5, function = logger.debug)
    logger.debug('Python version %s' % platform.python_version())

    logger.debug('Started communicator.')

    events.event('daemon_start', onionr = o_inst)
    try:
        while True:
            time.sleep(3)
            # Debug to print out used FDs (regular and net)
            #proc = psutil.Process()
            #print('api-files:',proc.open_files(), len(psutil.net_connections()))
            # Break if communicator process ends, so we don't have left over processes
            if o_inst.communicatorInst.shutdown:
                break
            if o_inst.killed:
                break # Break out if sigterm for clean exit
    except KeyboardInterrupt:
        pass
    finally:
        o_inst.onionrCore.daemonQueueAdd('shutdown')
        o_inst.onionrUtils.localCommand('shutdown')
    net.killTor()
    time.sleep(3)
    o_inst.deleteRunFiles()
    return

def kill_daemon(o_inst):
    '''
        Shutdown the Onionr daemon
    '''

    logger.warn('Stopping the running daemon...', timestamp = False)
    try:
        events.event('daemon_stop', onionr = o_inst)
        net = NetController(o_inst.onionrCore.config.get('client.port', 59496))
        try:
            o_inst.onionrCore.daemonQueueAdd('shutdown')
        except sqlite3.OperationalError:
            pass

        net.killTor()
    except Exception as e:
        logger.error('Failed to shutdown daemon.', error = e, timestamp = False)
    return