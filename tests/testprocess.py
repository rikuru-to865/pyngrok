import time
from mock import mock

from pyngrok import ngrok, process
from pyngrok.exception import PyngrokNgrokError
from .testcase import NgrokTestCase

__author__ = "Alex Laird"
__copyright__ = "Copyright 2019, Alex Laird"
__version__ = "1.3.5"


class TestProcess(NgrokTestCase):
    def test_get_process_no_binary(self):
        # GIVEN
        self.given_ngrok_not_installed(ngrok.DEFAULT_NGROK_PATH)
        self.assertEqual(len(process._current_processes.keys()), 0)

        # WHEN
        with self.assertRaises(PyngrokNgrokError) as cm:
            process.get_process(ngrok.DEFAULT_NGROK_PATH, config_path=self.config_path)

        # THEN
        self.assertIn("ngrok binary was not found", str(cm.exception))
        self.assertEqual(len(process._current_processes.keys()), 0)

    def test_start_process_multiple_fails(self):
        # GIVEN
        self.given_ngrok_installed(ngrok.DEFAULT_NGROK_PATH)
        self.assertEqual(len(process._current_processes.keys()), 0)

        # WHEN
        ngrok_process1 = process._start_process(ngrok.DEFAULT_NGROK_PATH, config_path=self.config_path)
        with self.assertRaises(PyngrokNgrokError) as cm:
            process._start_process(ngrok.DEFAULT_NGROK_PATH, config_path=self.config_path)

        # THEN
        self.assertIn("ngrok is already running", str(cm.exception))
        self.assertIsNotNone(ngrok_process1)
        self.assertIsNone(ngrok_process1.process.poll())
        self.assertEqual(ngrok_process1, process.get_process(ngrok.DEFAULT_NGROK_PATH))
        self.assertEqual(len(process._current_processes.keys()), 1)

    def test_start_process_port_in_use(self):
        # GIVEN
        self.given_ngrok_installed(ngrok.DEFAULT_NGROK_PATH)
        self.given_config({"web_addr": "localhost:20"})
        self.assertEqual(len(process._current_processes.keys()), 0)

        # WHEN
        with self.assertRaises(PyngrokNgrokError) as cm:
            process._start_process(ngrok.DEFAULT_NGROK_PATH, config_path=self.config_path)

        # THEN
        self.assertIn("20: bind: permission denied", str(cm.exception))
        self.assertEqual(len(process._current_processes.keys()), 0)

    def test_process_external_kill(self):
        # GIVEN
        self.given_ngrok_installed(ngrok.DEFAULT_NGROK_PATH)
        ngrok_process = process._start_process(ngrok.DEFAULT_NGROK_PATH, config_path=self.config_path)
        self.assertEqual(len(process._current_processes.keys()), 1)

        # WHEN
        # Kill the process by external means, pyngrok still thinks process is active
        ngrok_process.process.kill()
        ngrok_process.process.wait()
        self.assertEqual(len(process._current_processes.keys()), 1)

        # Try to kill the process via pyngrok, no error, just update state
        process.kill_process(ngrok.DEFAULT_NGROK_PATH)
        self.assertEqual(len(process._current_processes.keys()), 0)

    def test_process_external_kill_get_process_restart(self):
        # GIVEN
        self.given_ngrok_installed(ngrok.DEFAULT_NGROK_PATH)
        ngrok_process1 = process._start_process(ngrok.DEFAULT_NGROK_PATH, config_path=self.config_path)
        self.assertEqual(len(process._current_processes.keys()), 1)

        # WHEN
        # Kill the process by external means, pyngrok still thinks process is active
        ngrok_process1.process.kill()
        ngrok_process1.process.wait()
        self.assertEqual(len(process._current_processes.keys()), 1)

        # THEN
        # Try to get process via pyngrok, it has been killed, restart and correct state
        with mock.patch("atexit.register") as mock_atexit:
            ngrok_process2 = process.get_process(ngrok.DEFAULT_NGROK_PATH, config_path=self.config_path)
            self.assertNotEqual(ngrok_process1.process.pid, ngrok_process2.process.pid)
            self.assertEqual(len(process._current_processes.keys()), 1)

            mock_atexit.assert_called_once()