#!/usr/bin/env python3
# Copyright (c) 2017-2020 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.
"""An example functional test

The module-level docstring should include a high-level description of
what the test is doing. It's the first thing people see when they open
the file and should give the reader information about *what* the test
is testing and *how* it's being tested
"""
# Imports should be in PEP8 ordering (std library first, then third party
# libraries then local imports).
from collections import defaultdict

# Avoid wildcard * imports
from test_framework.blocktools import (create_block, create_coinbase)
from test_framework.messages import CInv, MSG_BLOCK
from test_framework.p2p import (
    P2PInterface,
    msg_block,
    msg_getdata,
    p2p_lock,
)
from test_framework.test_framework import BitcoinTestFramework
from test_framework.util import (
    assert_equal,
)

# P2PInterface is a class containing callbacks to be executed when a P2P
# message is received from the node-under-test. Subclass P2PInterface and
# override the on_*() methods if you need custom behaviour.
class BaseNode(P2PInterface):
    def __init__(self):
        """Initialize the P2PInterface

        Used to initialize custom properties for the Node that aren't
        included by default in the base class. Be aware that the P2PInterface
        base class already stores a counter for each P2P message type and the
        last received message of each type, which should be sufficient for the
        needs of most tests.

        Call super().__init__() first for standard initialization and then
        initialize custom properties."""
        super().__init__()
        # Stores a dictionary of all blocks received
        self.block_receive_map = defaultdict(int)

    def on_block(self, message):
        """Override the standard on_block callback

        Store the hash of a received block in the dictionary."""
        message.block.calc_sha256()
        self.block_receive_map[message.block.sha256] += 1

    def on_inv(self, message):
        """Override the standard on_inv callback"""
        pass

def custom_function():
    """Do some custom behaviour

    If this function is more generally useful for other tests, consider
    moving it to a module in test_framework."""
    # self.log.info("running custom_function")  # Oops! Can't run self.log outside the BitcoinTestFramework
    pass


class ExampleTest(BitcoinTestFramework):
    # Each functional test is a subclass of the BitcoinTestFramework class.

    # Override the set_test_params(), skip_test_if_missing_module(), add_options(), setup_chain(), setup_network()
    # and setup_nodes() methods to customize the test setup as required.

    def set_test_params(self):
        """Override test parameters for your individual test.

        This method must be overridden and num_nodes must be explicitly set."""
        # By default every test loads a pre-mined chain of 200 blocks from cache.
        # Set setup_clean_chain to True to skip this and start from the Genesis
        # block.
        self.setup_clean_chain = True
        self.num_nodes = 3
        # Use self.extra_args to change command-line arguments for the nodes
        self.extra_args = [[], ["-logips"], []]

        # self.log.info("I've finished set_test_params")  # Oops! Can't run self.log before run_test()

    # Use skip_test_if_missing_module() to skip the test if your test requires certain modules to be present.
    # This test uses generate which requires wallet to be compiled
    def skip_test_if_missing_module(self):
        self.skip_if_no_wallet()

    # Use add_options() to add specific command-line options for your test.
    # In practice this is not used very much, since the tests are mostly written
    # to be run in automated environments without command-line options.
    # def add_options()
    #     pass

    # Use setup_chain() to customize the node data directories. In practice
    # this is not used very much since the default behaviour is almost always
    # fine
    # def setup_chain():
    #     pass

    def setup_network(self):
        """Setup the test network topology

        Often you won't need to override this, since the standard network topology
        (linear: node0 <-> node1 <-> node2 <-> ...) is fine for most tests.

        If you do override this method, remember to start the nodes, assign
        them to self.nodes, connect them and then sync."""

        self.setup_nodes()

        # In this test, we're not connecting node2 to node0 or node1. Calls to
        # sync_all() should not include node2, since we're not expecting it to
        # sync.
        self.connect_nodes(0, 1)
        self.sync_all(self.nodes[0:2])

    # Use setup_nodes() to customize the node start behaviour (for example if
    # you don't want to start all nodes at the start of the test).
    # def setup_nodes():
    #     pass

    def custom_method(self):
        """Do some custom behaviour for this test

        Define it in a method here because you're going to use it repeatedly.
        If you think it's useful in general, consider moving it to the base
        BitcoinTestFramework class so other tests can use it."""

        self.log.info("Running custom_method")

    def run_test(self):
        """Main test logic"""

        # Create P2P connections will wait for a verack to make sure the connection is fully up
        peer_messaging = self.nodes[0].add_p2p_connection(BaseNode())

        # Generating a block on one of the nodes will get us out of IBD
        blocks = [int(self.nodes[0].generate(nblocks=1)[0], 16)]
        self.sync_all(self.nodes[0:2])

        # Notice above how we called an RPC by calling a method with the same
        # name on the node object. Notice also how we used a keyword argument
        # to specify a named RPC argument. Neither of those are defined on the
        # node object. Instead there's some __getattr__() magic going on under
        # the covers to dispatch unrecognised attribute calls to the RPC
        # interface.

        # Logs are nice. Do plenty of them. They can be used in place of comments for
        # breaking the test into sub-sections.
        self.log.info("Starting test!")

        self.log.info("Calling a custom function")
        custom_function()

        self.log.info("Calling a custom method")
        self.custom_method()

        self.log.info("Create some blocks")
        self.tip = int(self.nodes[0].getbestblockhash(), 16)
        self.block_time = self.nodes[0].getblock(self.nodes[0].getbestblockhash())['time'] + 1

        height = self.nodes[0].getblockcount()

        for _ in range(10):
            # Use the blocktools functionality to manually build a block.
            # Calling the generate() rpc is easier, but this allows us to exactly
            # control the blocks and transactions.
            block = create_block(self.tip, create_coinbase(height+1), self.block_time)
            block.solve()
            block_message = msg_block(block)
            # Send message is used to send a P2P message to the node over our P2PInterface
            peer_messaging.send_message(block_message)
            self.tip = block.sha256
            blocks.append(self.tip)
            self.block_time += 1
            height += 1

        self.log.info("Wait for node1 to reach current tip (height 11) using RPC")
        self.nodes[1].waitforblockheight(11)

        self.log.info("Connect node2 and node1")
        self.connect_nodes(1, 2)
        

        self.log.info("Wait for node2 to receive all the blocks from node1")
        self.sync_all()

        self.log.info("Add P2P connection to node2")
        self.nodes[0].disconnect_p2ps()

        peer_receiving = self.nodes[2].add_p2p_connection(BaseNode())

        self.log.info("Test that node2 propagates all the blocks to us")

        getdata_request = msg_getdata()
        for block in blocks:
            getdata_request.inv.append(CInv(MSG_BLOCK, block))
        peer_receiving.send_message(getdata_request)

        # wait_until() will loop until a predicate condition is met. Use it to test properties of the
        # P2PInterface objects.
        
        peer_receiving.wait_until(lambda: sorted(blocks) == sorted(list(peer_receiving.block_receive_map.keys())), timeout=5)

        self.log.info("Check that each block was received only once")

        # The network thread uses a global lock on data access to the P2PConnection objects when sending and receiving
        # messages. The test thread should acquire the global lock before accessing any P2PConnection data to avoid locking
        # and synchronization issues. Note p2p.wait_until() acquires this global lock internally when testing the predicate.

        with p2p_lock:
            for block in peer_receiving.block_receive_map.values():
                

               assert_equal(block, 1)

        self.log.info("************** End of Original Testing.  Beginning Modified Test **************")

        self.log.info("Show the height of each block prior to Node 1 generating a new block:")
        node0_height = self.nodes[0].getblockcount()
        node1_height = self.nodes[1].getblockcount()
        node2_height = self.nodes[2].getblockcount()
        
        self.log.info(f"node0 height: {node0_height}")
        self.log.info(f"node1 height: {node1_height}")
        self.log.info(f"node2 height: {node2_height}")
     
        
        # Node 1 generates a new block via the rpc command.  The RPC command is used rather than the blocktools functionality
        # so that the node itself creates a new block rather than creating a block (sui generis) and using p2p to send it
        # to Node 1.

        self.log.info("****************** Node 1 Generating New Block **********************************")
        new_block_array = self.nodes[1].generate(nblocks=1)
        new_block_hex = new_block_array[0]

        # Making the new_block an integer from the hex string to conform to the blocks list.
        new_block_int = int(new_block_hex, 16)

        self.log.info(f"new_block as hex: {new_block_hex}")
        
        self.log.info(f"new_block as int: {new_block_int}")

        # append the new block to blocks
        blocks.append(new_block_int)

        self.log.info("Wait for nodes to receive the new block from Node 1")
        self.sync_all()
        

        # It seems that Node 1 autmatically propagates the new block.  Need to understand this mechanism better.  
        # I diddn't send it out specifically, yet Node 2 seems to have recieved it sometimes even without a sync_all.
        # The sync_all seems to just wait until every node is updated.


        self.log.info("Getting the height (via rpc) after Node 1 makes new block")
        node0_height = self.nodes[0].getblockcount()
        node1_height = self.nodes[1].getblockcount()
        node2_height = self.nodes[2].getblockcount()
 
        self.log.info(f"node0 height: {node0_height}")
        self.log.info(f"node1 height: {node1_height}")
        self.log.info(f"node2 height: {node2_height}")

        self.log.info("Test that Node 1 height equals 12 and Node 2 height equals 12")
        assert_equal(12, node1_height, node2_height)


        
        # Show that the new block has propagated to Node 2.

        self.log.info("Get new block from Node 1 (via rpc).")
        new_block_1 = self.nodes[1].getblock(new_block_hex)
        #self.log.info(new_block_1)
        
        self.log.info("Get new block from Node 2 (via rpc).")
        new_block_2 = self.nodes[2].getblock(new_block_hex)
        #self.log.info(new_block_2)

        # revised assert_equal to return True if thing1 and thing2 are equal.
        assertion = assert_equal(new_block_1, new_block_2)

        #  Note:  following could show wonky if assertion fails
        self.log.info(f"Test:  Is new block from Node 1 equal to new block from Node 2? {assertion}.")
        
        
        # Now show that Node 2 sends all blocks--inlcuding the new one--to the p2p connection
        self.log.info("Test that node2 propagates all blocks --including the new one-- to us via p2p.")

        getdata_request = msg_getdata()
        for block in blocks:
            getdata_request.inv.append(CInv(MSG_BLOCK, block))
        peer_receiving.send_message(getdata_request)


        #clear out the block_receive_map before making another P2P call
        peer_receiving.block_receive_map = defaultdict(int)

        # wait_until() will loop until a predicate condition is met. Use it to test properties of the
        # P2PInterface objects.
        peer_receiving.wait_until(lambda: sorted(blocks) == sorted(list(peer_receiving.block_receive_map.keys())), timeout=5)

        
        # The network thread uses a global lock on data access to the P2PConnection objects when sending and receiving
        # messages. The test thread should acquire the global lock before accessing any P2PConnection data to avoid locking
        # and synchronization issues. Note p2p.wait_until() acquires this global lock internally when testing the predicate.
        with p2p_lock:
            #self.log.info("********** Show that Node 2 block_receive_map:  with proper number of blocks (12) each occuring once************")
            #self.log.info(peer_receiving.block_receive_map)

            self.log.info("Check that 12 blocks were received, each one only once.")

            # Test for Node 2 sent us via p2p 12 blocks
            assert_equal(12, len(list(peer_receiving.block_receive_map.keys())))
            # Test for Node 2 sending us via p2p each block once
            for block in peer_receiving.block_receive_map.values():
                assert_equal(block, 1)


        

        
        



if __name__ == '__main__':
    ExampleTest().main()
