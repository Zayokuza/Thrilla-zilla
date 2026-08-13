import unittest

from thrilla.router import Route, route_request


class RouterTests(unittest.TestCase):
    def test_general_fallback(self):
        decision = route_request("How are you today?")
        self.assertEqual(Route.GENERAL, decision.route)
        self.assertEqual((), decision.matches)

    def test_coding(self):
        decision = route_request("Debug and test this Python repository")
        self.assertEqual(Route.CODING, decision.route)
        self.assertGreater(decision.confidence, 0.7)

    def test_deep_search(self):
        self.assertEqual(Route.DEEP_SEARCH, route_request("Research the latest web sources").route)

    def test_device(self):
        self.assertEqual(Route.DEVICE, route_request("Check battery status on my S24 phone").route)

    def test_system(self):
        self.assertEqual(Route.SYSTEM, route_request("Inspect Windows CPU and RAM").route)


if __name__ == "__main__":
    unittest.main()

