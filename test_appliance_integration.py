import os
import json
import unittest
import sys

# Ensure root directory is in sys.path
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from api.calculate import perform_calculation, DEFAULT_RATES

class TestMeralcoApplianceIntegration(unittest.TestCase):

    def setUp(self):
        self.db_path = os.path.join(PROJECT_DIR, 'appliance_db.json')
        self.assertTrue(os.path.exists(self.db_path), "appliance_db.json must exist")
        with open(self.db_path, 'r', encoding='utf-8') as f:
            self.data = json.load(f)

    def test_appliance_db_schema(self):
        """Verify that appliance_db.json contains all required categories and fields."""
        self.assertIn("categories", self.data)
        self.assertIn("appliances", self.data)
        self.assertGreater(len(self.data["categories"]), 0)
        self.assertGreater(len(self.data["appliances"]), 0)

        required_keys = {"id", "name", "category", "average_wattage", "default_hours_per_day", "default_days_per_month"}
        for app in self.data["appliances"]:
            for key in required_keys:
                self.assertIn(key, app, f"Appliance '{app.get('name')}' is missing required key '{key}'")
            self.assertIsInstance(app["average_wattage"], (int, float))
            self.assertGreater(app["average_wattage"], 0)

    def test_appliance_kwh_calculation(self):
        """Verify monthly kWh formula: (Wattage * Hours/day * Days/month) / 1000."""
        # Find 1.0 HP Inverter AC
        ac = next((a for a in self.data["appliances"] if "1.0 HP, Inverter" in a["name"]), None)
        self.assertIsNotNone(ac, "1.0 HP Inverter AC should exist in catalog")
        
        wattage = ac["average_wattage"] # 680W
        hours = ac["default_hours_per_day"] # 8 hrs
        days = ac["default_days_per_month"] # 30 days

        calculated_kwh = (wattage * hours * days) / 1000.0
        expected_kwh = (680 * 8 * 30) / 1000.0 # 163.2 kWh
        self.assertAlmostEqual(calculated_kwh, expected_kwh, places=2)

    def test_internal_calculation_engine(self):
        """Verify selecting an appliance calculates costs strictly using internal project rates."""
        kwh = 163.2
        gen_rate = 9.2504
        other_charges = 0.0

        res = perform_calculation(kwh, gen_rate, other_charges)

        self.assertTrue(res["success"])
        self.assertEqual(res["input"]["kwh"], kwh)
        self.assertEqual(res["input"]["generation_rate"], gen_rate)

        # Expected component checks using local DEFAULT_RATES
        expected_gen_cost = round(kwh * gen_rate * 100) / 100 # 1509.67
        expected_trans_cost = round(kwh * DEFAULT_RATES["transmission"] * 100) / 100 # 229.69
        expected_dist_cost = round(kwh * DEFAULT_RATES["distTier1"] * 100) / 100 # 159.99 (since kWh <= 200)

        self.assertEqual(res["itemized"]["generation_charge"], expected_gen_cost)
        self.assertEqual(res["itemized"]["transmission_charge"], expected_trans_cost)
        self.assertEqual(res["itemized"]["distribution_charge"], expected_dist_cost)

    def test_no_external_meralco_rates_imported(self):
        """Verify that no external Meralco rate constants or APIs are imported or called in perform_calculation."""
        import inspect
        source = inspect.getsource(perform_calculation)
        self.assertNotIn("meralco.com.ph", source)
        self.assertNotIn("appliancecalculator.meralco.com.ph", source)
        self.assertNotIn("fetch_external_rate", source)

    def test_pelp_api_integration(self):
        """Verify that PELP API loads categories, handles search, and formats normalized products."""
        import api.pelp as pelp
        health = pelp.get_pelp_health()
        self.assertEqual(health["status"], "ok")
        self.assertGreater(health["total_products"], 5000)
        self.assertEqual(len(health["categories_available"]), 6)

        # Test search
        res = pelp.search_pelp_appliances("sharp", limit=5)
        self.assertTrue(res["success"])
        self.assertGreater(res["total_results"], 0)
        first = res["results"][0]
        self.assertIn("power_watts", first)
        self.assertIn("brand", first)
        self.assertIn("model", first)
        self.assertIn("category", first)

if __name__ == '__main__':
    unittest.main()
