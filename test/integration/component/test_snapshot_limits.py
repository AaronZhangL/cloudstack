# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

from nose.plugins.attrib import attr
from marvin.cloudstackTestCase import *
from marvin.cloudstackAPI import *
from marvin.integration.lib.utils import *
from marvin.integration.lib.base import *
from marvin.integration.lib.common import *
from marvin.remoteSSHClient import remoteSSHClient
import os


class Services:
    """Test Snapshots Services
    """

    def __init__(self):
        self.services = {
                        "account": {
                                    "email": "test@test.com",
                                    "firstname": "Test",
                                    "lastname": "User",
                                    "username": "test",
                                    # Random characters are appended for unique
                                    # username
                                    "password": "password",
                         },
                         "service_offering": {
                                    "name": "Tiny Instance",
                                    "displaytext": "Tiny Instance",
                                    "cpunumber": 1,
                                    "cpuspeed": 200,    # in MHz
                                    "memory": 256,      # In MBs
                        },
                        "disk_offering": {
                                    "displaytext": "Small Disk",
                                    "name": "Small Disk",
                                    "disksize": 1
                        },
                        "server_with_disk":
                                    {
                                        "displayname": "Test VM -With Disk",
                                        "username": "root",
                                        "password": "password",
                                        "ssh_port": 22,
                                        "hypervisor": 'XenServer',
                                        "privateport": 22,
                                        "publicport": 22,
                                        "protocol": 'TCP',
                                },

                        "server_without_disk":
                                    {
                                        "displayname": "Test VM-No Disk",
                                        "username": "root",
                                        "password": "password",
                                        "ssh_port": 22,
                                        "hypervisor": 'XenServer',
                                        "privateport": 22,
                                        # For NAT rule creation
                                        "publicport": 22,
                                        "protocol": 'TCP',
                                },
                        "server": {
                                    "displayname": "TestVM",
                                    "username": "root",
                                    "password": "password",
                                    "ssh_port": 22,
                                    "hypervisor": 'XenServer',
                                    "privateport": 22,
                                    "publicport": 22,
                                    "protocol": 'TCP',
                                },
                        "recurring_snapshot": {
                                    "intervaltype": 'HOURLY',
                                    # Frequency of snapshots
                                    "maxsnaps": 1,  # Should be min 2
                                    "schedule": 1,
                                    "timezone": 'US/Arizona',
                                    # Timezone Formats - http://cloud.mindtouch.us/CloudStack_Documentation/Developer's_Guide%3A_CloudStack
                                },
                        "templates": {
                                    "displaytext": 'Template',
                                    "name": 'Template',
                                    "ostype": "CentOS 5.3 (64-bit)",
                                    "templatefilter": 'self',
                                },
                        "volume": {
                                   "diskname": "APP Data Volume",
                                   "size": 1,   # in GBs
                                   "diskdevice": ['/dev/xvdb', '/dev/sdb', '/dev/hdb', '/dev/vdb' ],   # Data Disk
                        },
                        "paths": {
                                    "mount_dir": "/mnt/tmp",
                                    "sub_dir": "test",
                                    "sub_lvl_dir1": "test1",
                                    "sub_lvl_dir2": "test2",
                                    "random_data": "random.data",
                        },
                        "ostype": "CentOS 5.3 (64-bit)",
                        # Cent OS 5.3 (64 bit)
                        "sleep": 60,
                        "timeout": 10,
                    }


class TestSnapshotLimit(cloudstackTestCase):

    @classmethod
    def setUpClass(cls):
        cls.api_client = super(TestSnapshotLimit, cls).getClsTestClient().getApiClient()
        cls.services = Services().services
        # Get Zone, Domain and templates
        cls.domain = get_domain(cls.api_client, cls.services)
        cls.zone = get_zone(cls.api_client, cls.services)
        cls.services['mode'] = cls.zone.networktype
        cls._cleanup = []

        try:
            template = get_template(
                                cls.api_client,
                                cls.zone.id,
                                cls.services["ostype"]
                                )
            cls.services["server"]["zoneid"] = cls.zone.id

            cls.services["template"] = template.id

            # Create VMs, NAT Rules etc
            cls.account = Account.create(
                                cls.api_client,
                                cls.services["account"],
                                domainid=cls.domain.id
                                )
            cls._cleanup.append(cls.account)

            cls.services["account"] = cls.account.name

            if cls.zone.localstorageenabled:
                cls.services["service_offering"]["storagetype"] = "local"
            cls.service_offering = ServiceOffering.create(
                                                cls.api_client,
                                                cls.services["service_offering"]
                                                )
            cls._cleanup.append(cls.service_offering)
            cls.virtual_machine = VirtualMachine.create(
                                    cls.api_client,
                                    cls.services["server"],
                                    templateid=template.id,
                                    accountid=cls.account.name,
                                    domainid=cls.account.domainid,
                                    serviceofferingid=cls.service_offering.id
                                    )
            cls._cleanup.append(cls.virtual_machine)
        except Exception, e:
            cls.tearDownClass()
            unittest.SkipTest("setupClass fails for %s" % cls.__name__)
            raise e
        else:
            cls._cleanup.remove(cls.account)
        return

    @classmethod
    def tearDownClass(cls):
        try:
            #Cleanup resources used
            cleanup_resources(cls.api_client, reversed(cls._cleanup))
        except Exception as e:
            raise Exception("Warning: Exception during cleanup : %s" % e)
        return

    def setUp(self):
        self.apiclient = self.testClient.getApiClient()
        self.dbclient = self.testClient.getDbConnection()
        self.cleanup = []
        return

    def tearDown(self):
        try:
            #Clean up, terminate the created instance, volumes and snapshots
            cleanup_resources(self.apiclient, self.cleanup)
        except Exception as e:
            raise Exception("Warning: Exception during cleanup : %s" % e)
        return

    def is_snapshot_on_nfs(self, snapshot_id):
        """
        Checks whether a snapshot with id (not UUID) `snapshot_id` is present on the nfs storage

        @param snapshot_id: id of the snapshot (not uuid)
        @return: True if snapshot is found, False otherwise
        """
        secondaryStores = ImageStore.list(self.apiclient, zoneid=self.zone.id)
        self.assertTrue(isinstance(secondaryStores, list), "Not a valid response for listImageStores")
        self.assertNotEqual(len(secondaryStores), 0, "No image stores found in zone %s" % self.zone.id)
        secondaryStore = secondaryStores[0]
        if str(secondaryStore.providername).lower() != "nfs":
            self.skipTest("TODO: %s test works only against nfs secondary storage" % self._testMethodName)

        qresultset = self.dbclient.execute(
            "select install_path from snapshot_store_ref where snapshot_id='%s' and store_role='Image';" % snapshot_id
        )
        self.assertEqual(
            isinstance(qresultset, list),
            True,
            "Invalid db query response for snapshot %s" % snapshot_id
        )
        self.assertNotEqual(
            len(qresultset),
            0,
            "No such snapshot %s found in the cloudstack db" % snapshot_id
        )
        snapshotPath = qresultset[0][0]
        nfsurl = secondaryStore.url
        # parse_url = ['nfs:', '', '192.168.100.21', 'export', 'test']
        from urllib2 import urlparse
        parse_url = urlparse.urlsplit(nfsurl, scheme='nfs')
        host, path = parse_url.netloc, parse_url.path
        # Sleep to ensure that snapshot is reflected in sec storage
        time.sleep(self.services["sleep"])
        snapshots = []
        try:
            # Login to Secondary storage VM to check snapshot present on sec disk
            ssh_client = remoteSSHClient(
                self.config.mgtSvr[0].mgtSvrIp,
                22,
                self.config.mgtSvr[0].user,
                self.config.mgtSvr[0].passwd,
            )

            cmds = [
                "mkdir -p %s" % self.services["paths"]["mount_dir"],
                "mount -t %s %s/%s %s" % (
                    'nfs',
                    host,
                    path,
                    self.services["paths"]["mount_dir"]
                    ),
                "ls %s" % (
                    os.path.join(self.services["paths"]["mount_dir"], snapshotPath)
                    ),
            ]

            for c in cmds:
                self.debug("command: %s" % c)
                result = ssh_client.execute(c)
                self.debug("Result: %s" % result)

            snapshots.extend(result)
            # Unmount the Sec Storage
            cmds = [
                "cd",
                "umount %s" % (self.services["paths"]["mount_dir"]),
            ]
            for c in cmds:
                ssh_client.execute(c)
        except Exception as e:
            self.fail("SSH failed for management server: %s - %s" %
                      (self.config.mgtSvr[0].mgtSvrIp, e))
        return snapshots.count(snapshot_id) == 1

    @attr(speed = "slow")
    @attr(tags = ["advanced", "advancedns"])
    def test_04_snapshot_limit(self):
        """Test snapshot limit in snapshot policies
        """
        # Validate the following
        # 1. Perform hourly recurring snapshot on the root disk of VM and keep
        #    the maxsnapshots as 1
        # 2. listSnapshots should list the snapshot that was created
        #    snapshot folder in secondary storage should contain only one
        #    snapshot image(/secondary/snapshots/$accountid/$volumeid/)

        # Get the Root disk of VM
        volumes = list_volumes(
                            self.apiclient,
                            virtualmachineid=self.virtual_machine.id,
                            type='ROOT',
                            listall=True
                            )
        self.assertEqual(
                            isinstance(volumes, list),
                            True,
                            "Check list response returns a valid list"
                        )
        volume = volumes[0]

        # Create a snapshot policy
        recurring_snapshot = SnapshotPolicy.create(
                                           self.apiclient,
                                           volume.id,
                                           self.services["recurring_snapshot"]
                                        )
        self.cleanup.append(recurring_snapshot)

        snapshot_policy = list_snapshot_policy(
                                        self.apiclient,
                                        id=recurring_snapshot.id,
                                        volumeid=volume.id
                                        )
        self.assertEqual(
                            isinstance(snapshot_policy, list),
                            True,
                            "Check list response returns a valid list"
                        )

        self.assertNotEqual(
                            snapshot_policy,
                            None,
                            "Check if result exists in list item call"
                            )

        self.assertEqual(
                        snapshot_policy[0].id,
                        recurring_snapshot.id,
                        "Check recurring snapshot id in list resources call"
                        )
        self.assertEqual(
                        snapshot_policy[0].maxsnaps,
                        self.services["recurring_snapshot"]["maxsnaps"],
                        "Check interval type in list resources call"
                        )
        # Sleep for (maxsnaps+1) hours to verify
        # only maxsnaps snapshots are retained
        time.sleep(
            (self.services["recurring_snapshot"]["maxsnaps"]) * 3600
            )

        # Verify the snapshot was created or not
        snapshots = list_snapshots(
                        self.apiclient,
                        volumeid=volume.id,
                        intervaltype=\
                        self.services["recurring_snapshot"]["intervaltype"],
                        snapshottype='RECURRING',
                        listall=True
                        )

        self.assertEqual(
                            isinstance(snapshots, list),
                            True,
                            "Check list response returns a valid list"
                        )
        self.assertEqual(
                         len(snapshots),
                         self.services["recurring_snapshot"]["maxsnaps"],
                         "Check maximum number of recurring snapshots retained"
                        )
        snapshot = snapshots[0]
        # Sleep to ensure that snapshot is reflected in sec storage
        time.sleep(self.services["sleep"])

        # Fetch values from database
        qresultset = self.dbclient.execute(
                        "select id from snapshots where uuid = '%s';" \
                        % snapshot.id
                        )
        self.assertEqual(
                            isinstance(qresultset, list),
                            True,
                            "Invalid db query response for snapshot %s" % snapshot.id
                        )
        self.assertNotEqual(
                            len(qresultset),
                            0,
                            "No such snapshot %s found in the cloudstack db" % snapshot.id
                            )

        qresult = qresultset[0]
        snapshot_id = qresult[0]
        self.is_snapshot_on_nfs(snapshot_id)
        return
