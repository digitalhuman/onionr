'''
    Onionr - P2P Microblogging Platform & Social network

    OnionrUtils offers various useful functions to Onionr. Relatively misc.
'''
'''
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
'''
# Misc functions that do not fit in the main api, but are useful
import getpass, sys, requests, os, socket, hashlib, logger, sqlite3, config, binascii, time, base64, json, glob, shutil, math, json, re
import nacl.signing, nacl.encoding
from onionrblockapi import Block
import onionrexceptions
from defusedxml import minidom
import pgpwords
if sys.version_info < (3, 6):
    try:
        import sha3
    except ModuleNotFoundError:
        logger.fatal('On Python 3 versions prior to 3.6.x, you need the sha3 module')
        sys.exit(1)

class OnionrUtils:
    '''
        Various useful functions for validating things, etc functions, connectivity
    '''
    def __init__(self, coreInstance):
        self.fingerprintFile = 'data/own-fingerprint.txt'
        self._core = coreInstance

        self.timingToken = ''

        self.avoidDupe = [] # list used to prevent duplicate requests per peer for certain actions
        self.peerProcessing = {} # dict of current peer actions: peer, actionList

        return

    def getTimeBypassToken(self):
        try:
            if os.path.exists('data/time-bypass.txt'):
                with open('data/time-bypass.txt', 'r') as bypass:
                    self.timingToken = bypass.read()
        except Exception as error:
            logger.error('Failed to fetch time bypass token.', error = error)

        return self.timingToken

    def getRoundedEpoch(self, roundS=60):
        '''
            Returns the epoch, rounded down to given seconds (Default 60)
        '''
        epoch = self.getEpoch()
        return epoch - (epoch % roundS)

    def incrementAddressSuccess(self, address):
        '''
            Increase the recorded sucesses for an address
        '''
        increment = self._core.getAddressInfo(address, 'success') + 1
        self._core.setAddressInfo(address, 'success', increment)
        return

    def decrementAddressSuccess(self, address):
        '''
            Decrease the recorded sucesses for an address
        '''
        increment = self._core.getAddressInfo(address, 'success') - 1
        self._core.setAddressInfo(address, 'success', increment)
        return

    def mergeKeys(self, newKeyList):
        '''
            Merge ed25519 key list to our database, comma seperated string
        '''
        try:
            retVal = False
            if newKeyList != False:
                for key in newKeyList.split(','):
                    key = key.split('-')
                    try:
                        if len(key[0]) > 60 or len(key[1]) > 1000:
                            logger.warn('%s or its pow value is too large.' % key[0])
                            continue
                    except IndexError:
                        logger.warn('No pow token')
                        continue
                    #powHash = self._core._crypto.blake2bHash(base64.b64decode(key[1]) + self._core._crypto.blake2bHash(key[0].encode()))
                    value = base64.b64decode(key[1])
                    hashedKey = self._core._crypto.blake2bHash(key[0])
                    powHash = self._core._crypto.blake2bHash(value + hashedKey)
                    try:
                        powHash = powHash.encode()
                    except AttributeError:
                        pass
                    if powHash.startswith(b'0000'):
                        if not key[0] in self._core.listPeers(randomOrder=False) and type(key) != None and key[0] != self._core._crypto.pubKey:
                            if self._core.addPeer(key[0], key[1]):
                                retVal = True
                            else:
                                logger.warn("Failed to add key")
                    else:
                        pass
                        #logger.debug('%s pow failed' % key[0])
            return retVal
        except Exception as error:
            logger.error('Failed to merge keys.', error=error)
            return False


    def mergeAdders(self, newAdderList):
        '''
            Merge peer adders list to our database
        '''
        try:
            retVal = False
            if newAdderList != False:
                for adder in newAdderList.split(','):
                    if not adder in self._core.listAdders(randomOrder = False) and adder.strip() != self.getMyAddress():
                        if self._core.addAddress(adder):
                            logger.info('Added %s to db.' % adder, timestamp = True)
                            retVal = True
                    else:
                        pass
                        #logger.debug('%s is either our address or already in our DB' % adder)
            return retVal
        except Exception as error:
            logger.error('Failed to merge adders.', error = error)
            return False

    def getMyAddress(self):
        try:
            with open('./data/hs/hostname', 'r') as hostname:
                return hostname.read().strip()
        except Exception as error:
            logger.error('Failed to read my address.', error = error)
            return None

    def localCommand(self, command, silent = True):
        '''
            Send a command to the local http API server, securely. Intended for local clients, DO NOT USE for remote peers.
        '''

        config.reload()
        self.getTimeBypassToken()
        # TODO: URL encode parameters, just as an extra measure. May not be needed, but should be added regardless.
        try:
            with open('data/host.txt', 'r') as host:
                hostname = host.read()
        except FileNotFoundError:
            return False
        payload = 'http://%s:%s/client/?action=%s&token=%s&timingToken=%s' % (hostname, config.get('client.port'), command, config.get('client.hmac'), self.timingToken)
        try:
            retData = requests.get(payload).text
        except Exception as error:
            if not silent:
                logger.error('Failed to make local request (command: %s):%s' % (command, error))
            retData = False

        return retData

    def getPassword(self, message='Enter password: ', confirm = True):
        '''
            Get a password without showing the users typing and confirm the input
        '''
        # Get a password safely with confirmation and return it
        while True:
            print(message)
            pass1 = getpass.getpass()
            if confirm:
                print('Confirm password: ')
                pass2 = getpass.getpass()
                if pass1 != pass2:
                    logger.error("Passwords do not match.")
                    logger.readline()
                else:
                    break
            else:
                break

        return pass1

    def getHumanReadableID(self, pub=''):
        '''gets a human readable ID from a public key'''
        if pub == '':
            pub = self._core._crypto.pubKey
        pub = base64.b16encode(base64.b32decode(pub)).decode()
        return '-'.join(pgpwords.wordify(pub))

    def getBlockMetadataFromData(self, blockData):
        '''
            accepts block contents as string, returns a tuple of metadata, meta (meta being internal metadata, which will be returned as an encrypted base64 string if it is encrypted, dict if not).

        '''
        meta = {}
        metadata = {}
        data = blockData
        try:
            blockData = blockData.encode()
        except AttributeError:
            pass

        try:
            metadata = json.loads(blockData[:blockData.find(b'\n')].decode())
        except json.decoder.JSONDecodeError:
            pass
        else:
            data = blockData[blockData.find(b'\n'):].decode()

            if not metadata['encryptType'] in ('asym', 'sym'):
                try:
                    meta = json.loads(metadata['meta'])
                except KeyError:
                    pass
            meta = metadata['meta']
        return (metadata, meta, data)

    def checkPort(self, port, host=''):
        '''
            Checks if a port is available, returns bool
        '''
        # inspired by https://www.reddit.com/r/learnpython/comments/2i4qrj/how_to_write_a_python_script_that_checks_to_see/ckzarux/
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        retVal = False
        try:
            sock.bind((host, port))
        except OSError as e:
            if e.errno is 98:
                retVal = True
        finally:
            sock.close()

        return retVal

    def checkIsIP(self, ip):
        '''
            Check if a string is a valid IPv4 address
        '''
        try:
            socket.inet_aton(ip)
        except:
            return False
        else:
            return True

    def processBlockMetadata(self, blockHash):
        '''
            Read metadata from a block and cache it to the block database
        '''
        myBlock = Block(blockHash, self._core)
        if myBlock.isEncrypted:
            myBlock.decrypt()
        blockType = myBlock.getMetadata('type') # we would use myBlock.getType() here, but it is bugged with encrypted blocks
        try:
            if len(blockType) <= 10:
                self._core.updateBlockInfo(blockHash, 'dataType', blockType)
        except TypeError:
            pass

    def escapeAnsi(self, line):
        '''
            Remove ANSI escape codes from a string with regex

            taken or adapted from: https://stackoverflow.com/a/38662876
        '''
        ansi_escape = re.compile(r'(\x9B|\x1B\[)[0-?]*[ -/]*[@-~]')
        return ansi_escape.sub('', line)

    def getBlockDBHash(self):
        '''
            Return a sha3_256 hash of the blocks DB
        '''
        try:
            with open(self._core.blockDB, 'rb') as data:
                data = data.read()
            hasher = hashlib.sha3_256()
            hasher.update(data)
            dataHash = hasher.hexdigest()

            return dataHash
        except Exception as error:
            logger.error('Failed to get block DB hash.', error=error)

    def hasBlock(self, hash):
        '''
            Check for new block in the list
        '''
        conn = sqlite3.connect(self._core.blockDB)
        c = conn.cursor()
        if not self.validateHash(hash):
            raise Exception("Invalid hash")
        for result in c.execute("SELECT COUNT() FROM hashes where hash='" + hash + "'"):
            if result[0] >= 1:
                conn.commit()
                conn.close()
                return True
            else:
                conn.commit()
                conn.close()
                return False

    def hasKey(self, key):
        '''
            Check for key in list of public keys
        '''
        return key in self._core.listPeers()

    def validateHash(self, data, length=64):
        '''
            Validate if a string is a valid hex formatted hash
        '''
        retVal = True
        if data == False or data == True:
            return False
        data = data.strip()
        if len(data) != length:
            retVal = False
        else:
            try:
                int(data, 16)
            except ValueError:
                retVal = False

        return retVal

    def validateMetadata(self, metadata):
        '''Validate metadata meets onionr spec (does not validate proof value computation), take in either dictionary or json string'''
        # TODO, make this check sane sizes
        retData = False

        # convert to dict if it is json string
        if type(metadata) is str:
            try:
                metadata = json.loads(metadata)
            except json.JSONDecodeError:
                pass

        # Validate metadata dict for invalid keys to sizes that are too large
        if type(metadata) is dict:
            for i in metadata:
                try:
                    self._core.requirements.blockMetadataLengths[i]
                except KeyError:
                    logger.warn('Block has invalid metadata key ' + i)
                    break
                else:
                    if self._core.requirements.blockMetadataLengths[i] < len(metadata[i]):
                        logger.warn('Block metadata key ' + i + ' exceeded maximum size')
                        break
                if i == 'time':
                    if not self.isIntegerString(metadata[i]):
                        logger.warn('Block metadata time stamp is not integer string')
                        break
            else:
                # if metadata loop gets no errors, it does not break, therefore metadata is valid
                retData = True
        else:
            logger.warn('In call to utils.validateMetadata, metadata must be JSON string or a dictionary object')

        return retData

    def validatePubKey(self, key):
        '''
            Validate if a string is a valid base32 encoded Ed25519 key
        '''
        retVal = False
        try:
            nacl.signing.SigningKey(seed=key, encoder=nacl.encoding.Base32Encoder)
        except nacl.exceptions.ValueError:
            pass
        except base64.binascii.Error as err:
            pass
        else:
            retVal = True
        return retVal

    def isIntegerString(self, data):
        '''Check if a string is a valid base10 integer'''
        try:
            int(data)
        except ValueError:
            return False
        else:
            return True

    def validateID(self, id):
        '''
            Validate if an address is a valid tor or i2p hidden service
        '''
        try:
            idLength = len(id)
            retVal = True
            idNoDomain = ''
            peerType = ''
            # i2p b32 addresses are 60 characters long (including .b32.i2p)
            if idLength == 60:
                peerType = 'i2p'
                if not id.endswith('.b32.i2p'):
                    retVal = False
                else:
                    idNoDomain = id.split('.b32.i2p')[0]
            # Onion v2's are 22 (including .onion), v3's are 62 with .onion
            elif idLength == 22 or idLength == 62:
                peerType = 'onion'
                if not id.endswith('.onion'):
                    retVal = False
                else:
                    idNoDomain = id.split('.onion')[0]
            else:
                retVal = False
            if retVal:
                if peerType == 'i2p':
                    try:
                        id.split('.b32.i2p')[2]
                    except:
                        pass
                    else:
                        retVal = False
                elif peerType == 'onion':
                    try:
                        id.split('.onion')[2]
                    except:
                        pass
                    else:
                        retVal = False
                if not idNoDomain.isalnum():
                    retVal = False

            return retVal
        except:
            return False

    def getPeerByHashId(self, hash):
        '''
            Return the pubkey of the user if known from the hash
        '''
        if self._core._crypto.pubKeyHashID() == hash:
            retData = self._core._crypto.pubKey
            return retData
        conn = sqlite3.connect(self._core.peerDB)
        c = conn.cursor()
        command = (hash,)
        retData = ''
        for row in c.execute('SELECT ID FROM peers where hashID=?', command):
            if row[0] != '':
                retData = row[0]
        return retData

    def isCommunicatorRunning(self, timeout = 5, interval = 0.1):
        try:
            runcheck_file = 'data/.runcheck'

            if os.path.isfile(runcheck_file):
                os.remove(runcheck_file)
                logger.debug('%s file appears to have existed before the run check.' % runcheck_file, timestamp = False)

            self._core.daemonQueueAdd('runCheck')
            starttime = time.time()

            while True:
                time.sleep(interval)
                if os.path.isfile(runcheck_file):
                    os.remove(runcheck_file)

                    return True
                elif time.time() - starttime >= timeout:
                    return False
        except:
            return False

    def token(self, size = 32):
        '''
            Generates a secure random hex encoded token
        '''
        return binascii.hexlify(os.urandom(size))

    def importNewBlocks(self, scanDir=''):
        '''
            This function is intended to scan for new blocks ON THE DISK and import them
        '''
        blockList = self._core.getBlockList()
        if scanDir == '':
            scanDir = self._core.blockDataLocation
        if not scanDir.endswith('/'):
            scanDir += '/'
        for block in glob.glob(scanDir + "*.dat"):
            if block.replace(scanDir, '').replace('.dat', '') not in blockList:
                logger.info('Found new block on dist %s' % block)
                with open(block, 'rb') as newBlock:
                    block = block.replace(scanDir, '').replace('.dat', '')
                    if self._core._crypto.sha3Hash(newBlock.read()) == block.replace('.dat', ''):
                        self._core.addToBlockDB(block.replace('.dat', ''), dataSaved=True)
                        logger.info('Imported block %s.' % block)
                    else:
                        logger.warn('Failed to verify hash for %s' % block)

    def progressBar(self, value = 0, endvalue = 100, width = None):
        '''
            Outputs a progress bar with a percentage. Write \n after use.
        '''

        if width is None or height is None:
            width, height = shutil.get_terminal_size((80, 24))

        bar_length = width - 6

        percent = float(value) / endvalue
        arrow = '─' * int(round(percent * bar_length)-1) + '>'
        spaces = ' ' * (bar_length - len(arrow))

        sys.stdout.write("\r┣{0}┫ {1}%".format(arrow + spaces, int(round(percent * 100))))
        sys.stdout.flush()

    def getEpoch(self):
        '''returns epoch'''
        return math.floor(time.time())

    def doPostRequest(self, url, data={}, port=0, proxyType='tor'):
        '''
        Do a POST request through a local tor or i2p instance
        '''
        if proxyType == 'tor':
            if port == 0:
                port = self._core.torPort
            proxies = {'http': 'socks5://127.0.0.1:' + str(port), 'https': 'socks5://127.0.0.1:' + str(port)}
        elif proxyType == 'i2p':
            proxies = {'http': 'http://127.0.0.1:4444'}
        else:
            return
        headers = {'user-agent': 'PyOnionr'}
        try:
            proxies = {'http': 'socks5://127.0.0.1:' + str(port), 'https': 'socks5://127.0.0.1:' + str(port)}
            r = requests.post(url, data=data, headers=headers, proxies=proxies, allow_redirects=False, timeout=(15, 30))
            retData = r.text
        except KeyboardInterrupt:
            raise KeyboardInterrupt
        except requests.exceptions.RequestException as e:
            logger.debug('Error: %s' % str(e))
            retData = False
        return retData

    def doGetRequest(self, url, port=0, proxyType='tor'):
        '''
        Do a get request through a local tor or i2p instance
        '''
        if proxyType == 'tor':
            if port == 0:
                raise onionrexceptions.MissingPort('Socks port required for Tor HTTP get request')
            proxies = {'http': 'socks5://127.0.0.1:' + str(port), 'https': 'socks5://127.0.0.1:' + str(port)}
        elif proxyType == 'i2p':
            proxies = {'http': 'http://127.0.0.1:4444'}
        else:
            return
        headers = {'user-agent': 'PyOnionr'}
        try:
            proxies = {'http': 'socks5://127.0.0.1:' + str(port), 'https': 'socks5://127.0.0.1:' + str(port)}
            r = requests.get(url, headers=headers, proxies=proxies, allow_redirects=False, timeout=(15, 30))
            retData = r.text
        except KeyboardInterrupt:
            raise KeyboardInterrupt
        except ValueError as e:
            logger.debug('Failed to make request', error = e)
        except requests.exceptions.RequestException as e:
            logger.debug('Error: %s' % str(e))
            retData = False
        return retData

    def getNistBeaconSalt(self, torPort=0, rounding=3600):
        '''
            Get the token for the current hour from the NIST randomness beacon
        '''
        if torPort == 0:
            try:
                sys.argv[2]
            except IndexError:
                raise onionrexceptions.MissingPort('Missing Tor socks port')
        retData = ''
        curTime = self.getRoundedEpoch(rounding)
        self.nistSaltTimestamp = curTime
        data = self.doGetRequest('https://beacon.nist.gov/rest/record/' + str(curTime), port=torPort)
        dataXML = minidom.parseString(data, forbid_dtd=True, forbid_entities=True, forbid_external=True)
        try:
            retData = dataXML.getElementsByTagName('outputValue')[0].childNodes[0].data
        except ValueError:
            logger.warn('Could not get NIST beacon value')
        else:
            self.powSalt = retData
        return retData

def size(path='.'):
    '''
        Returns the size of a folder's contents in bytes
    '''
    total = 0
    if os.path.exists(path):
        if os.path.isfile(path):
            total = os.path.getsize(path)
        else:
            for entry in os.scandir(path):
                if entry.is_file():
                    total += entry.stat().st_size
                elif entry.is_dir():
                    total += size(entry.path)
    return total

def humanSize(num, suffix='B'):
    '''
        Converts from bytes to a human readable format.
    '''
    for unit in ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']:
        if abs(num) < 1024.0:
            return "%.1f %s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f %s%s" % (num, 'Yi', suffix)
