"""Onionr - Private P2P Communication.

Upload blocks in the upload queue to peers from the communicator
"""
from typing import TYPE_CHECKING
from time import sleep
from threading import Thread

from . import sessionmanager

from onionrtypes import UserID
import logger
from communicatorutils import proxypicker
import onionrexceptions
from onionrblocks import onionrblockapi as block
from onionrutils import stringvalidators, basicrequests
import onionrcrypto
from communicator import onlinepeers
if TYPE_CHECKING:
    from deadsimplekv import DeadSimpleKV
    from communicator import OnionrCommunicatorDaemon
"""
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
"""


def upload_blocks_from_communicator(comm_inst: 'OnionrCommunicatorDaemon'):
    """Accept a communicator instance + upload blocks from its upload queue."""
    """when inserting a block, we try to upload
     it to a few peers to add some deniability & increase functionality"""
    kv: "DeadSimpleKV" = comm_inst.shared_state.get_by_string("DeadSimpleKV")
    TIMER_NAME = "upload_blocks_from_communicator"

    session_manager: sessionmanager.BlockUploadSessionManager
    session_manager = comm_inst.shared_state.get(
        sessionmanager.BlockUploadSessionManager)
    tried_peers: UserID = []
    finishedUploads = []
    kv.put('blocksToUpload', onionrcrypto.cryptoutils.random_shuffle(
        kv.get('blocksToUpload')))

    def remove_from_hidden(bl):
        sleep(60)
        try:
            comm_inst.shared_state.get_by_string(
                'PublicAPI').hideBlocks.remove(bl)
        except ValueError:
            pass

    if len(kv.get('blocksToUpload')) != 0:
        for bl in kv.get('blocksToUpload'):
            if not stringvalidators.validate_hash(bl):
                logger.warn('Requested to upload invalid block', terminal=True)
                comm_inst.decrementThreadCount(TIMER_NAME)
                return
            session = session_manager.add_session(bl)
            for _ in range(min(len(kv.get('onlinePeers')), 6)):
                try:
                    peer = onlinepeers.pick_online_peer(kv)
                    if not block.Block(bl).isEncrypted:
                        if peer in kv.get('plaintextDisabledPeers'):
                            logger.info(f"Cannot upload plaintext block to peer that denies it {peer}")  # noqa
                            continue
                except onionrexceptions.OnlinePeerNeeded:
                    continue
                try:
                    session.peer_exists[peer]
                    continue
                except KeyError:
                    pass
                try:
                    if session.peer_fails[peer] > 3:
                        continue
                except KeyError:
                    pass
                if peer in tried_peers:
                    continue
                tried_peers.append(peer)
                url = f'http://{peer}/upload'
                try:
                    data = block.Block(bl).getRaw()
                    if not data:
                        logger.warn(
                            f"Couldn't data for block in upload list {bl}",
                            terminal=True)
                        raise onionrexceptions.NoDataAvailable
                except onionrexceptions.NoDataAvailable:
                    finishedUploads.append(bl)
                    break
                proxy_type = proxypicker.pick_proxy(peer)
                logger.info(
                    f"Uploading block {bl[:8]} to {peer}", terminal=True)
                resp = basicrequests.do_post_request(
                    url, data=data, proxyType=proxy_type,
                    content_type='application/octet-stream')
                if resp is not False:
                    if resp == 'success':
                        Thread(target=remove_from_hidden,
                               args=[bl], daemon=True).start()
                        session.success()
                        session.peer_exists[peer] = True
                    elif resp == 'exists':
                        session.success()
                        session.peer_exists[peer] = True
                    else:
                        session.fail()
                        session.fail_peer(peer)
                        comm_inst.getPeerProfileInstance(peer).addScore(-5)
                        logger.warn(
                           f'Failed to upload {bl[:8]}, reason: {resp}',
                           terminal=True)
                else:
                    session.fail()
        session_manager.clean_session()
    for x in finishedUploads:
        try:
            kv.get('blocksToUpload').remove(x)

            comm_inst.shared_state.get_by_string(
                'PublicAPI').hideBlocks.remove(x)

        except ValueError:
            pass
    comm_inst.decrementThreadCount(TIMER_NAME)
