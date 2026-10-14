"""Reproducible monthly demand forecasting from the supplied order snapshot."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

ROOT = Path(__file__).resolve().parent

def load_panel(data_path: Path):
    """Aggregate positive order quantities; create zeros only after first observation."""
    raw = pd.read_csv(data_path, encoding='ISO-8859-1', low_memory=False)
    duplicated = int(raw.duplicated().sum())
    clean = raw.drop_duplicates().copy()
    clean['month'] = pd.to_datetime(clean['MONTH_DAY'], errors='coerce').dt.to_period('M')
    clean['quantity'] = pd.to_numeric(clean['QTY'], errors='coerce')
    clean = clean[clean['month'].notna() & clean['MATERIAL'].notna() & (clean['quantity'] > 0)].copy()
    clean['material'] = clean['MATERIAL'].astype(str)
    clean['net_value'] = pd.to_numeric(clean['NET_VALUE'], errors='coerce').fillna(0)
    clean['net_net_value'] = pd.to_numeric(clean['NET_NET_VALUE_RMB'], errors='coerce').fillna(0)
    monthly = clean.groupby(['material', 'month'], sort=True).agg(
        quantity=('quantity','sum'), net_value=('net_value','sum'), net_net_value=('net_net_value','sum'))
    last = clean['month'].max()
    frames = []
    for material, part in monthly.groupby(level='material', sort=True):
        part = part.droplevel('material')
        idx = pd.period_range(part.index.min(), last+1, freq='M')
        part = part.reindex(idx, fill_value=0)
        part.index.name = 'month'
        part['material'] = material
        part.loc[last+1, ['quantity','net_value','net_net_value']] = np.nan
        frames.append(part.reset_index())
    panel = pd.concat(frames,ignore_index=True).sort_values(['material','month']).reset_index(drop=True)
    grouped = panel.groupby('material',sort=False)
    for lag in range(1,13):
        panel[f'qty_lag_{lag}'] = grouped['quantity'].shift(lag)
    for window in (3,6,12):
        panel[f'qty_mean_{window}'] = grouped['quantity'].transform(lambda s:s.shift(1).rolling(window,min_periods=1).mean())
    panel['qty_std_3'] = grouped['quantity'].transform(lambda s:s.shift(1).rolling(3,min_periods=1).std()).fillna(0)
    for col in ('net_value','net_net_value'):
        panel[f'{col}_lag_1'] = grouped[col].shift(1)
    panel['month_sin'] = np.sin(2*np.pi*panel['month'].dt.month/12)
    panel['month_cos'] = np.cos(2*np.pi*panel['month'].dt.month/12)
    panel['history_months'] = grouped.cumcount()
    info = {'source_rows':len(raw),'exact_duplicate_rows_removed':duplicated,'usable_rows':len(clean),
            'materials':int(clean.material.nunique()),'first_month':str(clean.month.min()),'last_observed_month':str(last),
            'zero_month_policy':'No observed positive order within a covered month is treated as zero, only after first appearance.'}
    return panel, info

def feature_names(spec):
    names = [f'qty_lag_{i}' for i in range(1,spec['lags']+1)]
    if spec.get('rolling',True):
        names += ['qty_mean_3','qty_mean_6','qty_mean_12','qty_std_3']
    return names + ['net_value_lag_1','net_net_value_lag_1','month_sin','month_cos','history_months']

def predict_month(panel, month, spec):
    month = pd.Period(month,freq='M')
    features = feature_names(spec)
    train = panel[(panel.month < month) & (panel.history_months >= 1) & panel.quantity.notna()]
    target = panel[(panel.month == month) & (panel.history_months >= 1)].copy()
    model = RandomForestRegressor(random_state=42,n_jobs=1,**spec['params'])
    response=np.log1p(train.quantity) if spec.get('log_target',False) else train.quantity
    model.fit(train[features].fillna(0),response)
    prediction=model.predict(target[features].fillna(0))
    if spec.get('log_target',False):prediction=np.expm1(prediction)
    target['prediction'] = np.maximum(0,prediction)
    target['model'] = spec['name']
    return target[['material','month','quantity','prediction','model']],model

def metrics(frame):
    error = frame.prediction.to_numpy()-frame.quantity.to_numpy()
    return {'rows':len(frame),'mae':float(np.abs(error).mean()),'rmse':float(np.sqrt(np.mean(error**2))),
            'wape':float(np.abs(error).sum()/frame.quantity.sum()) if frame.quantity.sum()>0 else None,
            'actual_total':float(frame.quantity.sum()),'predicted_total':float(frame.prediction.sum())}

def run(data_path=None, output_dir=None):
    output_dir = Path(output_dir or ROOT/'results')
    output_dir.mkdir(parents=True,exist_ok=True)
    config = json.loads((ROOT/'model_config.json').read_text())
    panel,info = load_panel(Path(data_path or ROOT/'data'/'SO.csv.gz'))
    results=[]
    for month in config['audit_months']:
        predictions,_ = predict_month(panel,month,config)
        results.append(predictions)
    audit = pd.concat(results,ignore_index=True)
    audit.to_csv(output_dir/'audit_predictions.csv',index=False)
    next_month = str(pd.Period(info['last_observed_month'],freq='M')+1)
    future,model = predict_month(panel,next_month,config)
    future.drop(columns='quantity').to_csv(output_dir/'next_month_forecast.csv',index=False)
    summary = {'selected_model':config['name'],'selection_months':config['selection_months'],'audit_months':config['audit_months'],
               'audit_metrics':metrics(audit),'forecast_month':next_month,'forecast_materials':len(future),'input':info}
    (output_dir/'run_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    return summary,audit,future,model

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data',type=Path)
    parser.add_argument('--output-dir',type=Path)
    args=parser.parse_args()
    summary,*_=run(args.data,args.output_dir)
    print(json.dumps(summary,indent=2))
