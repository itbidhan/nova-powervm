# Copyright 2015 IBM Corp.
#
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#

from __future__ import absolute_import

import fixtures
import mock

from nova_powervm.virt.powervm import driver

from nova.virt import fake
from pypowervm.tests.wrappers.util import pvmhttp

MS_HTTPRESP_FILE = "managedsystem.txt"


class PyPowerVM(fixtures.Fixture):
    """Patch out PyPowerVM Session and Adapter."""

    def setUp(self):
        super(PyPowerVM, self).setUp()
        self._sess_patcher = mock.patch('pypowervm.adapter.Session')
        self._apt_patcher = mock.patch('pypowervm.adapter.Adapter')
        self.sess = self._sess_patcher.start()
        self.apt = self._apt_patcher.start()

        self.addCleanup(self._sess_patcher.stop)
        self.addCleanup(self._apt_patcher.stop)


class ImageAPI(fixtures.Fixture):
    """Mock out the Glance API."""

    def setUp(self):
        super(ImageAPI, self).setUp()
        self._img_api_patcher = mock.patch('nova.image.API')
        self.img_api = self._img_api_patcher.start()

        self.addCleanup(self.img_api)


class DiskAdapter(fixtures.Fixture):
    """Mock out the DiskAdapter."""

    def setUp(self):
        super(DiskAdapter, self).setUp()
        self._std_disk_adpt = mock.patch('nova_powervm.virt.powervm.disk.'
                                         'localdisk.LocalStorage')
        self.std_disk_adpt = self._std_disk_adpt.start()
        self.addCleanup(self._std_disk_adpt.stop)


class HostCPUStats(fixtures.Fixture):
    """Mock out the HostCPUStats."""

    def setUp(self):
        super(HostCPUStats, self).setUp()
        self._host_cpu_stats = mock.patch('nova_powervm.virt.powervm.host.'
                                          'HostCPUStats')
        self.host_cpu_stats = self._host_cpu_stats.start()
        self.addCleanup(self._host_cpu_stats.stop)


class VolumeAdapter(fixtures.Fixture):
    """Mock out the VolumeAdapter."""

    def setUp(self):
        super(VolumeAdapter, self).setUp()
        self._std_vol_adpt = mock.patch('nova_powervm.virt.powervm.volume.'
                                        'vscsi.VscsiVolumeAdapter')
        self.std_vol_adpt = self._std_vol_adpt.start()
        self.addCleanup(self._std_vol_adpt.stop)


class PowerVMComputeDriver(fixtures.Fixture):
    """Construct a fake compute driver."""

    @mock.patch('nova_powervm.virt.powervm.disk.localdisk.LocalStorage')
    @mock.patch('nova_powervm.virt.powervm.driver.PowerVMDriver._get_adapter')
    @mock.patch('nova_powervm.virt.powervm.mgmt.get_mgmt_partition')
    def _init_host(self, *args):
        ms_http = pvmhttp.load_pvm_resp(MS_HTTPRESP_FILE).get_response()
        # Pretend it just returned one host
        ms_http.feed.entries = [ms_http.feed.entries[0]]
        self.drv.adapter.read.return_value = ms_http
        self.drv.init_host('FakeHost')

    def setUp(self):
        super(PowerVMComputeDriver, self).setUp()

        self.pypvm = PyPowerVM()
        self.pypvm.setUp()
        self.addCleanup(self.pypvm.cleanUp)

        # Set up the mock CPU stats (init_host uses it)
        self.useFixture(HostCPUStats())

        self.drv = driver.PowerVMDriver(fake.FakeVirtAPI())
        self.drv.adapter = self.pypvm.apt
        self._init_host()
        self.drv.image_api = mock.Mock()

        # Set up the mock volume and disk drivers.
        vol_adpt = self.useFixture(VolumeAdapter())
        self.drv.vol_drvs['fibre_channel'] = vol_adpt.std_vol_adpt

        disk_adpt = self.useFixture(DiskAdapter())
        self.drv.disk_dvr = disk_adpt.std_disk_adpt
