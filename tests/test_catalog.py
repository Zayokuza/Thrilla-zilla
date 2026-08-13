import unittest

from thrilla.catalog import ALL_DONORS, CORE_DONORS, SPECIALIST_DONORS


class CatalogTests(unittest.TestCase):
    def test_phase_one_has_ten_by_ten(self):
        self.assertEqual(100, len(CORE_DONORS))
        for category in range(1, 11):
            entries = [item for item in CORE_DONORS if item.category == category]
            self.assertEqual(10, len(entries))
            self.assertEqual(list(range(1, 11)), [item.slot for item in entries])

    def test_priority_layer_has_thirty(self):
        priority = [item for item in CORE_DONORS if item.priority]
        self.assertEqual(30, len(priority))
        self.assertTrue(all(item.slot <= 3 for item in priority))

    def test_repositories_and_paths_are_unique(self):
        repositories = [item.repository.lower() for item in ALL_DONORS]
        paths = [item.relative_path.lower() for item in ALL_DONORS]
        self.assertEqual(len(repositories), len(set(repositories)))
        self.assertEqual(len(paths), len(set(paths)))

    def test_xray_is_registered_as_first_specialist(self):
        self.assertEqual(1, len(SPECIALIST_DONORS))
        xray = SPECIALIST_DONORS[0]
        self.assertEqual("XTLS/Xray-core", xray.repository)
        self.assertEqual("11-networking-proxy/01-xray-core", xray.relative_path)


if __name__ == "__main__":
    unittest.main()

