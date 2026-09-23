"""Unit tests for the home network/hardware discovery tools."""

from unittest.mock import MagicMock, patch

from tools.network_scan import scan_lan_devices, scan_bluetooth_devices, scan_mdns_devices


class TestScanLanDevices:
    """Test scan_lan_devices."""

    def test_lists_discovered_devices(self):
        with patch("tools.network_scan._get_local_ip", return_value="192.168.1.10"), \
             patch("tools.network_scan._ping"), \
             patch("tools.network_scan._read_neighbor_table",
                   return_value={"192.168.1.5": "aa:bb:cc:dd:ee:ff"}), \
             patch("tools.network_scan._resolve_hostname", return_value="printer.local"):
            result = scan_lan_devices.invoke({})

        assert "192.168.1.5" in result
        assert "aa:bb:cc:dd:ee:ff" in result
        assert "printer.local" in result

    def test_no_devices_found(self):
        with patch("tools.network_scan._get_local_ip", return_value="192.168.1.10"), \
             patch("tools.network_scan._ping"), \
             patch("tools.network_scan._read_neighbor_table", return_value={}):
            result = scan_lan_devices.invoke({})

        assert "couldn't read the ARP/neighbor table" in result

    def test_handles_local_ip_failure(self):
        with patch("tools.network_scan._get_local_ip", side_effect=Exception("no network")):
            result = scan_lan_devices.invoke({})

        assert "Could not determine the local network" in result


class TestScanBluetoothDevices:
    """Test scan_bluetooth_devices."""

    def test_lists_discovered_devices(self):
        fake_device = MagicMock(address="AA:BB:CC:DD:EE:FF", name="My Speaker")

        with patch("bleak.BleakScanner.discover", return_value=[fake_device]):
            result = scan_bluetooth_devices.invoke({})

        assert "My Speaker" in result
        assert "AA:BB:CC:DD:EE:FF" in result

    def test_no_devices_found(self):
        with patch("bleak.BleakScanner.discover", return_value=[]):
            result = scan_bluetooth_devices.invoke({})

        assert "No nearby Bluetooth devices found" in result

    def test_scan_failure_is_handled_gracefully(self):
        with patch("bleak.BleakScanner.discover", side_effect=Exception("adapter not found")):
            result = scan_bluetooth_devices.invoke({})

        assert "Bluetooth scan failed" in result
        assert "adapter not found" in result


class TestScanMdnsDevices:
    """Test scan_mdns_devices."""

    def test_no_devices_found(self):
        with patch("zeroconf.Zeroconf") as mock_zc_cls, \
             patch("zeroconf.ZeroconfServiceTypes") as mock_types_cls, \
             patch("zeroconf.ServiceBrowser"), \
             patch("tools.network_scan.time.sleep"):
            mock_types_cls.find.return_value = []
            result = scan_mdns_devices.invoke({})

        assert "No mDNS-announcing devices found" in result
        mock_zc_cls.return_value.close.assert_called_once()

    def test_scan_failure_is_handled_gracefully(self):
        with patch("zeroconf.Zeroconf") as mock_zc_cls, \
             patch("zeroconf.ZeroconfServiceTypes") as mock_types_cls:
            mock_types_cls.find.side_effect = Exception("network unreachable")
            result = scan_mdns_devices.invoke({})

        assert "mDNS scan failed" in result
        mock_zc_cls.return_value.close.assert_called_once()
