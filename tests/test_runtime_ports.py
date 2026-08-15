import importlib
import socket
import unittest


class RuntimePortTests(unittest.TestCase):

    def test_inspect_port_detects_listening_tcp_service(self):
        try:
            ports = importlib.import_module(
                "thrilla.runtime.ports"
            )
        except Exception as error:
            self.fail(
                "runtime ports module must exist: {0}".format(
                    error
                )
            )

        inspection_type = getattr(
            ports,
            "PortInspection",
            None,
        )
        inspector = getattr(
            ports,
            "inspect_port",
            None,
        )

        self.assertTrue(
            callable(inspection_type),
            "PortInspection must exist",
        )
        self.assertTrue(
            callable(inspector),
            "inspect_port must exist",
        )

        server = socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM,
        )

        try:
            server.bind(
                (
                    "127.0.0.1",
                    0,
                )
            )
            server.listen(1)

            port = server.getsockname()[1]

            status = inspector(
                "127.0.0.1",
                port,
                timeout=0.2,
            )

            self.assertIsInstance(
                status,
                inspection_type,
            )
            self.assertEqual(
                "127.0.0.1",
                status.host,
            )
            self.assertEqual(
                port,
                status.port,
            )
            self.assertTrue(
                status.listening,
            )
        finally:
            server.close()

    def test_inspect_port_reports_bound_nonlistener_as_not_bindable(self):
        ports = importlib.import_module(
            "thrilla.runtime.ports"
        )

        holder = socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM,
        )

        try:
            holder.bind(
                (
                    "127.0.0.1",
                    0,
                )
            )

            port = holder.getsockname()[1]

            status = ports.inspect_port(
                "127.0.0.1",
                port,
                timeout=0.1,
            )

            self.assertFalse(
                status.listening,
            )

            self.assertFalse(
                status.bindable,
                "bound port must not be reported bindable",
            )
        finally:
            holder.close()

    def test_find_available_port_skips_occupied_candidate(self):
        ports = importlib.import_module(
            "thrilla.runtime.ports"
        )

        finder = getattr(
            ports,
            "find_available_port",
            None,
        )

        self.assertTrue(
            callable(finder),
            "find_available_port must exist",
        )

        occupied = socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM,
        )

        free_probe = socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM,
        )

        try:
            occupied.bind(
                (
                    "127.0.0.1",
                    0,
                )
            )
            occupied_port = occupied.getsockname()[1]

            free_probe.bind(
                (
                    "127.0.0.1",
                    0,
                )
            )
            free_port = free_probe.getsockname()[1]
        finally:
            free_probe.close()

        try:
            selected = finder(
                "127.0.0.1",
                [
                    occupied_port,
                    free_port,
                ],
                timeout=0.1,
            )

            self.assertEqual(
                free_port,
                selected,
            )
        finally:
            occupied.close()

    def test_inspect_port_rejects_out_of_range_port(self):
        ports = importlib.import_module(
            "thrilla.runtime.ports"
        )

        for invalid in (
            0,
            -1,
            65536,
        ):
            with self.subTest(port=invalid):
                with self.assertRaisesRegex(
                    ValueError,
                    "port must be between 1 and 65535",
                ):
                    ports.inspect_port(
                        "127.0.0.1",
                        invalid,
                    )


if __name__ == "__main__":
    unittest.main()
