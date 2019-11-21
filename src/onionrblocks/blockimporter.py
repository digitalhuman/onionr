'''
    Onionr - Private P2P Communication

    Import block data and save it
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
import onionrexceptions, logger
from onionrutils import validatemetadata, blockmetadata
from coredb import blockmetadb
from . import onionrblacklist
import onionrstorage
import onionrcrypto as crypto
def importBlockFromData(content):
    blacklist = onionrblacklist.OnionrBlackList()
    retData = False

    try:
        content = content.encode()
    except AttributeError:
        pass

    dataHash = crypto.hashers.sha3_hash(content)

    if blacklist.inBlacklist(dataHash):
        raise onionrexceptions.BlacklistedBlock('%s is a blacklisted block' % (dataHash,))

    metas = blockmetadata.get_block_metadata_from_data(content) # returns tuple(metadata, meta), meta is also in metadata
    metadata = metas[0]
    if validatemetadata.validate_metadata(metadata, metas[2]): # check if metadata is valid
        if crypto.cryptoutils.verify_POW(content): # check if POW is enough/correct
            logger.info('Imported block passed proof, saving.', terminal=True)
            try:
                blockHash = onionrstorage.set_data(content)
            except onionrexceptions.DiskAllocationReached:
                logger.warn('Failed to save block due to full disk allocation')
            else:
                blockmetadb.add_to_block_DB(blockHash, dataSaved=True)
                blockmetadata.process_block_metadata(blockHash) # caches block metadata values to block database
                retData = True
        else:
            raise onionrexceptions.InvalidProof
    return retData