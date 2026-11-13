"""Isolated regression checks. All host paths and power commands are stubbed."""
import os
import fcntl
from pathlib import Path
import subprocess
import tempfile
import time
import unittest


SOURCE = Path(__file__).resolve().parents[1] / 'tools/pve/laptop-battery-shutdown.sh'


class MonitorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        self.env = dict(os.environ, PATH=f'{self.bin}:{os.environ["PATH"]}')
        self.env.pop('PVE_BATTERY_UPDATE_LOCAL', None)
        self.env['PVE_BATTERY_SCRIPT_URL'] = 'https://fixture.invalid/installer.sh'
        self.events = self.root / 'events'
        self.script = self.root / 'installer.sh'
        source = SOURCE.read_text()
        for path in ('/etc/default', '/etc/systemd/system', '/usr/local/bin',
                     '/usr/local/lib', '/var/lib', '/sys/class/power_supply'):
            source = source.replace(path, str(self.root) + path)
        self.script.write_text(source)
        self.script.chmod(0o755)
        for path in ('etc/default', 'etc/systemd/system', 'usr/local/bin'):
            (self.root / path).mkdir(parents=True)
        self.supply = self.root / 'sys/class/power_supply'
        (self.supply / 'BAT0').mkdir(parents=True)
        (self.supply / 'AC').mkdir()
        self.config = self.root / 'etc/default/pve-battery-monitor'
        self.config.write_text('LOW_CAPACITY_PERCENT=25\nCHECK_INTERVAL_SECONDS=60\nDRY_RUN=1\n')
        self.state = self.root / 'var/lib/pve-battery-monitor/state'
        self.check = self.root / 'usr/local/bin/pve-battery-monitor-check'
        self.manager = self.root / 'usr/local/bin/pve-battery-monitor-manage'
        self.stub('logger', 'exit 0')
        self.stub('pveversion', 'echo pve-manager/9.0.0/test')
        self.stub('systemctl', 'exit 0')
        self.stub('shutdown', f'echo shutdown >> "{self.events}"')
        self.stub('curl', f'''case "$*" in
  *fixture.invalid*)
    while [ "$#" -gt 0 ]; do
      if [ "$1" = -o ]; then cp "{self.script}" "$2"; exit; fi
      shift
    done
    cat "{self.script}" ;;
  *) exit 0 ;;
esac''')
        self.battery(80, True)
        self.run_script('install')

    def stub(self, name, body):
        path = self.bin / name
        path.write_text('#!/usr/bin/env bash\n' + body + '\n')
        path.chmod(0o755)

    def run_script(self, action, path=None):
        return self.run_command(['bash', str(path or self.script), action])

    def run_command(self, command):
        result = subprocess.run(command, env=self.env, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    def battery(self, capacity, online=False):
        (self.supply / 'AC/online').write_text('1\n' if online else '0\n')
        energy = capacity * 100000 if isinstance(capacity, int) else 0
        (self.supply / 'BAT0/uevent').write_text(
            f'POWER_SUPPLY_CAPACITY={capacity}\nPOWER_SUPPLY_STATUS=Discharging\n'
            f'POWER_SUPPLY_ENERGY_NOW={energy}\n'
            'POWER_SUPPLY_ENERGY_FULL=10000000\nPOWER_SUPPLY_POWER_NOW=1000000\n')

    def check_run(self):
        return self.run_command(['bash', str(self.check)])

    def age_state(self, **changes):
        lines = self.state.read_text().splitlines()
        self.state.write_text('\n'.join(
            f'{key}="{changes[key]}"' if key in changes else line
            for line in lines for key in [line.split('=', 1)[0]]) + '\n')

    def test_low_battery_confirmation_and_dry_run(self):
        self.battery(20)
        self.assertIn('action=arm', self.check_run())
        self.age_state(LAST_TIMESTAMP=int(time.time()) - 1)
        self.assertIn('action=dry-run-shutdown', self.check_run())
        self.assertFalse(self.events.exists())

    def test_live_shutdown_stub(self):
        self.config.write_text(self.config.read_text().replace('DRY_RUN=1', 'DRY_RUN=0'))
        self.battery(20)
        self.check_run()
        self.age_state(LAST_TIMESTAMP=int(time.time()) - 1)
        self.assertIn('action=shutdown', self.check_run())
        self.assertEqual(self.events.read_text(), 'shutdown\n')

    def test_boot_and_stale_state_reset(self):
        self.battery(20)
        self.check_run()
        self.age_state(STATE_BOOT_ID='previous-boot')
        self.assertIn('action=arm', self.check_run())
        self.age_state(LAST_TIMESTAMP=1)
        self.assertIn('action=arm', self.check_run())

    def test_ac_recovery(self):
        self.battery(20)
        self.check_run()
        self.battery(20, True)
        self.assertIn('detail=external-power-present', self.check_run())
        self.assertIn('ARMED=0', self.state.read_text())

    def test_invalid_capacity(self):
        self.battery('invalid')
        self.assertIn('detail=missing-capacity', self.check_run())

    def test_installed_update_fetches_new_source(self):
        self.script.write_text(self.script.read_text().replace(
            'APP="PVE Laptop Battery Shutdown"', 'APP="Fixture Updated Monitor"'))
        output = self.run_script('update', self.manager)
        self.assertIn('Fixture Updated Monitor', output)
        self.assertIn('DRY_RUN=1', self.config.read_text())

    def test_recovery_and_eta(self):
        self.battery(20)
        self.check_run()
        self.age_state(LAST_TIMESTAMP=int(time.time()) - 1)
        self.battery(21)
        self.assertIn('action=clear-state', self.check_run())
        self.battery(50)
        self.assertIn('eta=02h30m', self.check_run())

    def test_concurrent_check_skips(self):
        lock_path = self.state.parent / 'lock'
        with lock_path.open('w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.assertEqual(self.check_run(), '')
        self.assertFalse(self.events.exists())

    def test_legacy_state_rearms(self):
        self.battery(20)
        self.state.write_text('ARMED=1\nLAST_CAPACITY=20\n')
        self.assertIn('action=arm', self.check_run())

    def test_invalid_config(self):
        self.config.write_text('LOW_CAPACITY_PERCENT=invalid\n')
        result = subprocess.run(['bash', str(self.check)], env=self.env,
                                text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Invalid battery monitor configuration', result.stderr)
        self.assertFalse(self.events.exists())

    def test_failed_update_preserves_installer(self):
        stored = self.root / 'usr/local/lib/pve-battery-monitor/laptop-battery-shutdown.sh'
        before = stored.read_bytes()
        self.stub('curl', 'exit 22')
        result = subprocess.run(['bash', str(self.manager), 'update'],
                                env=self.env, text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(stored.read_bytes(), before)

    def test_missing_or_invalid_ac_rejects_install(self):
        before = self.check.read_bytes()
        online = self.supply / 'AC/online'
        for value in (None, 'invalid'):
            if value is None:
                online.unlink()
            else:
                online.write_text(value)
            result = subprocess.run(['bash', str(self.script), 'install'],
                                    env=self.env, text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Set AC_DEVICE', result.stdout)
            self.assertEqual(self.check.read_bytes(), before)

    def test_fallback_menu(self):
        source = self.script.read_text()
        function = source[source.index('choose_action() {'):source.index('\nmain() {')]
        harness = ('command() { if [[ "$*" == "-v whiptail" ]]; then return 1; fi; '
                   'builtin command "$@"; }\n' + function + '\nchoose_action\n')
        result = subprocess.run(['bash', '-c', harness], input='Install\n',
                                env=self.env, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, 'Install\n')
        self.assertIn('Select an option', result.stderr)

    def test_invalid_generated_script_preserves_installed_files(self):
        before = self.check.read_bytes()
        stored = self.root / 'usr/local/lib/pve-battery-monitor/laptop-battery-shutdown.sh'
        old_installer = stored.read_bytes()
        self.script.write_text(self.script.read_text().replace(
            'set -euo pipefail', 'if then', 1))
        result = subprocess.run(['bash', str(self.script), 'install'],
                                env=self.env, text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.check.read_bytes(), before)
        self.assertEqual(stored.read_bytes(), old_installer)

    def test_atomic_replacement_failure_preserves_target(self):
        stored = self.root / 'usr/local/lib/pve-battery-monitor/laptop-battery-shutdown.sh'
        before = stored.read_bytes()
        self.stub('install', 'exit 1')
        result = subprocess.run(['bash', str(self.script), 'install'],
                                env=self.env, text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(stored.read_bytes(), before)
        self.assertEqual(list(stored.parent.glob('.pve-battery.*')), [])

    def test_downloads_have_time_limits(self):
        for script in (self.script, self.manager):
            for line in script.read_text().splitlines():
                if 'curl -fsSL' in line:
                    self.assertIn('--connect-timeout', line)
                    self.assertIn('--max-time', line)

    def test_generated_scripts_pass_shellcheck(self):
        scripts = [self.check, self.manager,
                   self.root / 'usr/local/bin/update_pve_battery_monitor',
                   self.root / 'usr/local/bin/uninstall_pve_battery_monitor']
        for script in scripts:
            self.run_command(['bash', '-n', str(script)])
            self.run_command(['shellcheck', str(script)])

    def test_curl_style_install_and_remove(self):
        self.run_command(['bash', '-c', self.script.read_text(), 'bash', 'install'])
        self.assertTrue(self.manager.exists())
        self.run_script('status', self.manager)
        self.run_script('remove', self.manager)
        self.assertFalse(self.check.exists())
        self.assertTrue(self.config.exists())


if __name__ == '__main__':
    unittest.main()
