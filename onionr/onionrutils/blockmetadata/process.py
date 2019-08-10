'''
    Onionr - Private P2P Communication

    Process block metadata with relevant actions
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

from etc import onionrvalues
import onionrblockapi
from .. import epoch, bytesconverter
from coredb import blockmetadb
import logger
import onionrevents
import onionrexceptions
from onionrusers import onionrusers

def process_block_metadata(blockHash: str):
    '''
        Read metadata from a block and cache it to the block database
        
        blockHash -> sha3_256 hex formatted hash of Onionr block
    '''
    curTime = epoch.get_rounded_epoch(roundS=60)
    myBlock = onionrblockapi.Block(blockHash)
    if myBlock.isEncrypted:
        myBlock.decrypt()
    if (myBlock.isEncrypted and myBlock.decrypted) or (not myBlock.isEncrypted):
        blockType = myBlock.getMetadata('type') # we would use myBlock.getType() here, but it is bugged with encrypted blocks

        signer = bytesconverter.bytes_to_str(myBlock.signer)
        valid = myBlock.verifySig()
        if myBlock.getMetadata('newFSKey') is not None:
            try:
                onionrusers.OnionrUser(signer).addForwardKey(myBlock.getMetadata('newFSKey'))
            except onionrexceptions.InvalidPubkey:
                logger.warn('%s has invalid forward secrecy key to add: %s' % (signer, myBlock.getMetadata('newFSKey')))
            
        try:
            if len(blockType) <= onionrvalues.MAX_BLOCK_TYPE_LENGTH:
                blockmetadb.update_block_info(blockHash, 'dataType', blockType)
        except TypeError:
            logger.warn("Missing block information")
            pass
        # Set block expire time if specified
        try:
            expireTime = myBlock.getHeader('expire')
            assert len(str(int(expireTime))) < 20 # test that expire time is an integer of sane length (for epoch)
        except (AssertionError, ValueError, TypeError) as e:
            expireTime = onionrvalues.DEFAULT_EXPIRE + curTime
        finally:
            blockmetadb.update_block_info(blockHash, 'expire', expireTime)
        onionrevents.event('processblocks', data = {'block': myBlock, 'type': blockType, 'signer': signer, 'validSig': valid})
