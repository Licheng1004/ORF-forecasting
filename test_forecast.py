"""Temporal-isolation and result-reconciliation checks."""
import unittest
import numpy as np
import pandas as pd
import forecast

class ForecastTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.panel,_=forecast.load_panel(forecast.ROOT/'data'/'SO.csv.gz')

    def test_all_lags_are_from_earlier_months(self):
        panel=self.panel
        for lag in range(1,13):
            expected=panel.groupby('material').quantity.shift(lag)
            np.testing.assert_allclose(panel[f'qty_lag_{lag}'],expected,equal_nan=True)

    def test_future_outcomes_do_not_change_earlier_forecasts(self):
        spec={'name':'small_test_model','lags':1,'rolling':False,'params':{'n_estimators':8,'max_depth':3}}
        original,_=forecast.predict_month(self.panel,'2024-08',spec)
        changed=self.panel.copy()
        changed.loc[changed.month>=pd.Period('2024-08'),'quantity']=1e12
        other,_=forecast.predict_month(changed,'2024-08',spec)
        np.testing.assert_allclose(original.prediction,other.prediction)

    def test_saved_metrics_reconcile(self):
        predictions=pd.read_csv(forecast.ROOT/'results'/'candidate_predictions.csv')
        summary=pd.read_csv(forecast.ROOT/'results'/'candidate_comparison.csv')
        for row in summary.itertuples():
            subset=predictions[(predictions.model==row.model)&(predictions.stage==row.stage)]
            computed=forecast.metrics(subset)
            self.assertAlmostEqual(computed['mae'],row.mae,places=7)
            self.assertEqual(computed['rows'],row.rows)

if __name__=='__main__':unittest.main()
